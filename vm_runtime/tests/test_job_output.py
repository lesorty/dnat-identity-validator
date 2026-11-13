"""T-804 e T-802, lado da CVM de job: saída de esquema fixo e tempos limite do agente.

Rodar da raiz do repositório:  python3 -m unittest discover -s vm_runtime/tests

Os testes de ponta a ponta sobem o executor.py de verdade num thread, em modo direto
(run-direct.sh), com DNAT_EXEC_DIR num diretório temporário. Não precisam de CVM, microVM nem
IPFS; o caminho da microVM (run-vm.sh, rootfs/runner) fica para a fase de testes.

Sobre o "job que dorme 2 h" da T-802: o que o teste precisa provar é (1) que um job além do limite
é cortado, registrado como tempo estourado e não trava o agente, e (2) que um limite configurado
acima da duração do job não o corta. Isso não depende da escala: aqui o limite é de 2 s com um job
de 60 s, e de 30 s com um job de 4 s. Que nenhum teto fixo sobrou no caminho para 2 h é conferido
na conta dos limites (job 7200 s -> agente 7320 s -> CVM1 7350 s) e na linha do kernel do guest.
"""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import os
import sys
import tarfile
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

VM_RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VM_RUNTIME))

import executor  # noqa: E402
import job_output  # noqa: E402

RUN_FROM_CIDS = VM_RUNTIME.parent / "smart-contract" / "scripts" / "run_from_cids.py"
RUN_VM = VM_RUNTIME / "vm" / "run-vm.sh"
RUNNER = VM_RUNTIME / "rootfs" / "runner"


class MetricsSchemaTest(unittest.TestCase):
    def test_metricas_validas_sao_arredondadas(self):
        out, err = job_output.parse_metrics_bytes(b'{"loss": 0.123456789, "steps": 10, "train_seconds": 3.5}')
        self.assertIsNone(err)
        self.assertEqual(out, {"loss": 0.123457, "steps": 10, "train_seconds": 3.5})

    def test_campo_extra_e_recusado(self):
        self.assertEqual(job_output.parse_metrics_bytes(b'{"loss": 1, "pesos": 2}'), (None, "unknown_field"))

    def test_texto_nan_bool_e_negativo_sao_recusados(self):
        for raw in (b'{"loss": "abc"}', b'{"loss": NaN}', b'{"loss": Infinity}', b'{"steps": true}',
                    b'{"steps": 1.5}', b'{"steps": -1}', b'{"loss": [1]}'):
            with self.subTest(raw=raw):
                out, err = job_output.parse_metrics_bytes(raw)
                self.assertIsNone(out)
                self.assertIn(err, ("bad_value", "invalid_json"))

    def test_teto_de_bytes(self):
        self.assertEqual(job_output.parse_metrics_bytes(b" " * 2000 + b"{}"), (None, "too_large"))

    def test_esquema_e_teto_configuraveis(self):
        env = {"DNAT_METRICS_SCHEMA": '{"acc": "number"}', "DNAT_METRICS_MAX_BYTES": "64"}
        with mock.patch.dict(os.environ, env):
            self.assertEqual(job_output.parse_metrics_bytes(b'{"acc": 0.9}'), ({"acc": 0.9}, None))
            self.assertEqual(job_output.parse_metrics_bytes(b'{"loss": 1}'), (None, "unknown_field"))
            self.assertEqual(job_output.parse_metrics_bytes(b'{"acc": 0.9}' + b" " * 64), (None, "too_large"))

    def test_arquivo_de_50_mib_e_recusado_sem_ser_lido_inteiro(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metrics.json"
            with open(path, "wb") as f:
                f.write(os.urandom(50 << 20))
            started = time.monotonic()
            self.assertEqual(job_output.read_metrics_file(path), (None, "too_large"))
            self.assertLess(time.monotonic() - started, 1.0)

    def test_link_simbolico_e_fifo_nao_sao_lidos(self):
        with tempfile.TemporaryDirectory() as tmp:
            secret = Path(tmp) / "segredo"
            secret.write_text('{"loss": 1}')
            link = Path(tmp) / "metrics.json"
            link.symlink_to(secret)
            self.assertEqual(job_output.read_metrics_file(link), (None, "not_regular_file"))
            fifo = Path(tmp) / "fifo.json"
            os.mkfifo(fifo)
            self.assertEqual(job_output.read_metrics_file(fifo), (None, "not_regular_file"))
            self.assertEqual(job_output.read_metrics_file(Path(tmp) / "nao-existe"), (None, "missing"))


class SanitizeTest(unittest.TestCase):
    def test_stdout_stderr_e_chaves_estranhas_somem(self):
        raw = {"returncode": 0, "stdout": "PESOS", "stderr": "PESOS", "extra": "PESOS",
               "metrics": {"loss": 1.0}, "elapsed_seconds": 2.0}
        out = job_output.sanitize_runner_output(raw, 600)
        self.assertEqual(tuple(out), job_output.OUTPUT_KEYS)
        self.assertNotIn("PESOS", json.dumps(out))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["metrics"], {"loss": 1.0})

    def test_erro_do_runner_vira_codigo_fixo(self):
        raw = {"error": "microVM execution timed out", "firecrackerLog": "PESOS"}
        out = job_output.sanitize_runner_output(raw, 600)
        self.assertEqual((out["status"], out["error"]), ("timeout", "microvm_timeout"))
        out = job_output.sanitize_runner_output({"error": "PESOS impressos pelo script"}, 600)
        self.assertEqual((out["status"], out["error"]), ("agent_error", "runner_error"))
        self.assertNotIn("PESOS", json.dumps(out))

    def test_guest_da_microvm_manda_o_texto_das_metricas(self):
        out = job_output.sanitize_runner_output({"returncode": 0, "metrics_text": '{"steps": 3, "x": 1}'}, 600)
        self.assertEqual((out["metrics"], out["metrics_error"]), (None, "unknown_field"))

    def test_derivado_so_passa_com_job_ok(self):
        d = {"digest": "a" * 64}
        self.assertEqual(job_output.sanitize_runner_output({"returncode": 0, "derivative": d}, 1)["derivative"], d)
        self.assertIsNone(job_output.sanitize_runner_output({"returncode": 1, "derivative": d}, 1)["derivative"])
        self.assertIsNone(job_output.sanitize_runner_output({"returncode": 124, "timed_out": True, "derivative": d}, 1)["derivative"])


class TimeoutConfigTest(unittest.TestCase):
    def test_padroes_reproduzem_os_limites_antigos(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            t = job_output.load_timeouts()
        self.assertEqual(t, {"job_default_seconds": 600, "job_max_seconds": 86400, "agent_margin_seconds": 120})
        self.assertEqual(job_output.effective_job_timeout(None, t) + t["agent_margin_seconds"], 720)

    def test_pedido_da_cvm1_respeita_o_teto_do_agente(self):
        t = {"job_default_seconds": 600, "job_max_seconds": 3600, "agent_margin_seconds": 120}
        self.assertEqual(job_output.effective_job_timeout("7200", t), 3600)
        self.assertEqual(job_output.effective_job_timeout("30", t), 30)
        self.assertEqual(job_output.effective_job_timeout("lixo", t), 600)
        self.assertEqual(job_output.effective_job_timeout("-5", t), 600)

    def test_margem_do_agente_cobre_boot_e_desligamento_da_microvm(self):
        env = {"DNAT_AGENT_MARGIN_SECONDS": "5", "DNAT_VM_BOOT_MARGIN_SECONDS": "200"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(job_output.load_timeouts()["agent_margin_seconds"], 200 + 20 + 10)

    def test_configuracao_invalida_volta_ao_padrao(self):
        with mock.patch.dict(os.environ, {"DNAT_JOB_TIMEOUT_SECONDS": "abc", "DNAT_AGENT_MARGIN_SECONDS": "0"}, clear=True):
            t = job_output.load_timeouts()
        self.assertEqual((t["job_default_seconds"], t["agent_margin_seconds"]), (600, 120))

    @unittest.skipUnless(RUN_FROM_CIDS.is_file(), "smart-contract/ ausente")
    def test_job_de_2_h_cvm1_sempre_acima_do_agente(self):
        spec = importlib.util.spec_from_file_location("run_from_cids", RUN_FROM_CIDS)
        rfc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rfc)
        env = {"DNAT_JOB_TIMEOUT_SECONDS": "7200", "DNAT_JOB_TIMEOUT_MAX_SECONDS": "86400"}
        with mock.patch.dict(os.environ, env, clear=True):
            agent = job_output.load_timeouts()
        job = job_output.effective_job_timeout(7200, agent)
        plan = rfc.plan_timeouts(7200, agent, 30)
        self.assertEqual(job, 7200)
        self.assertEqual(plan, {"jobSeconds": 7200, "agentSeconds": 7320, "cvm1Seconds": 7350})
        self.assertGreater(plan["cvm1Seconds"], plan["agentSeconds"])
        self.assertGreater(plan["agentSeconds"], job + 60 + 20, "agente acima do boot e do desligamento da microVM")
        # Sem /health do agente (versão antiga), a CVM1 cai nos números antigos: 600 -> 750.
        self.assertEqual(rfc.plan_timeouts(None, None, 30)["cvm1Seconds"], 750)

    def test_microvm_recebe_o_limite_do_host(self):
        vm = RUN_VM.read_text()
        self.assertIn("dnat.job_timeout=${JOB_TIMEOUT_SECONDS}", vm)
        self.assertIn('VM_TIMEOUT_SECONDS=$((JOB_TIMEOUT_SECONDS + VM_BOOT_MARGIN_SECONDS))', vm)
        runner = RUNNER.read_text()
        self.assertIn("dnat.job_timeout=", runner)
        self.assertNotIn("timeout=600", runner)


class RunRunnerTest(unittest.TestCase):
    """O agente não trava quando o runner passa do limite, nem com um neto segurando o pipe."""

    def test_neto_no_mesmo_grupo_e_morto(self):
        started = time.monotonic()
        _, _, timed_out = executor.run_runner(["bash", "-c", "sleep 30 & sleep 30"], dict(os.environ), 1)
        self.assertTrue(timed_out)
        self.assertLess(time.monotonic() - started, 4)

    def test_neto_fora_do_grupo_nao_trava_o_agente(self):
        started = time.monotonic()
        _, _, timed_out = executor.run_runner(["bash", "-c", "setsid sleep 9 & sleep 30"], dict(os.environ), 1)
        self.assertTrue(timed_out)
        self.assertLess(time.monotonic() - started, 1 + executor._PIPE_GRACE_SECONDS + 2)


def _bundle(script: str, model: dict[str, bytes] | None = None) -> bytes:
    """Bundle com workspace/run.sh que roda `script` em Python, como o run.sh do run_from_cids.py.

    model: arquivos do modelo base em workspace/model (T-805)."""
    run_sh = (
        "#!/bin/bash\nset -euo pipefail\ncd \"$(dirname \"$0\")\"\n"
        "export DNAT_DERIVATIVE_DIR=\"$PWD/derivative\"\nexport DNAT_METRICS_PATH=\"$PWD/metrics.json\"\n"
        "python3 code/app.py\n"
    )
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        items = [("workspace/run.sh", run_sh), ("workspace/code/app.py", script)]
        items += [(f"workspace/model/{k}", v) for k, v in (model or {}).items()]
        for name, data in items:
            raw = data.encode() if isinstance(data, str) else data
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(raw))
    return buf.getvalue()


HOSTILE = r"""
import os, sys
chunk = os.urandom(1 << 20)
for _ in range(50):
    sys.stdout.buffer.write(chunk)
    sys.stderr.buffer.write(chunk)
open(os.environ["DNAT_METRICS_PATH"], "w").write('{"loss": 0.5, "pesos": "' + chunk[:32].hex() + '"}')
"""

BENIGN = r"""
import os, pathlib
print("loss=0.25 passos=10 PESOS-NO-STDOUT")
d = pathlib.Path(os.environ["DNAT_DERIVATIVE_DIR"]); d.mkdir()
(d / "adapter_model.safetensors").write_bytes(b"pesos" * 100)
open(os.environ["DNAT_METRICS_PATH"], "w").write('{"loss": 0.25, "steps": 10, "train_seconds": 1.0}')
"""

TOUCHES_BASE = r"""
import os, pathlib
base = pathlib.Path("model")
try:
    (base / "model.safetensors").write_bytes(b"envenenado")
except PermissionError:
    os.chmod(base / "model.safetensors", 0o644)          # o script insiste: o digest pega
    (base / "model.safetensors").write_bytes(b"envenenado")
d = pathlib.Path(os.environ["DNAT_DERIVATIVE_DIR"]); d.mkdir()
(d / "model.safetensors").write_bytes(b"derivado")
"""

READS_BASE = r"""
import os, pathlib
w = pathlib.Path("model/model.safetensors").read_bytes()
d = pathlib.Path(os.environ["DNAT_DERIVATIVE_DIR"]); d.mkdir()
(d / "model.safetensors").write_bytes(w + b"+ajuste")
"""

SLEEPER = r"""
import os, pathlib, signal, subprocess, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
subprocess.Popen(["sleep", "300"])
d = pathlib.Path(os.environ["DNAT_DERIVATIVE_DIR"]); d.mkdir()
(d / "parcial.bin").write_bytes(b"pesos")
time.sleep(60)
"""

FOUR_SECONDS = r"""
import os, time
time.sleep(4)
open(os.environ["DNAT_METRICS_PATH"], "w").write('{"steps": 4}')
"""


class DirectAgentTest(unittest.TestCase):
    """executor.py + run-direct.sh de verdade, por HTTP, num diretório temporário."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.exec_dir = Path(cls._tmp.name) / "exec"
        cls._env = mock.patch.dict(os.environ, {"DNAT_EXEC_DIR": str(cls.exec_dir), "DNAT_JOB_KILL_GRACE_SECONDS": "2"})
        cls._env.start()
        cls.outbox = Path(cls._tmp.name) / "outbox"
        cls._patches = [
            mock.patch.object(executor, "OUTBOX", cls.outbox),
            mock.patch.object(executor, "RUNNER_SCRIPT", "run-direct.sh"),
            mock.patch.object(executor, "TIMEOUTS", {"job_default_seconds": 30, "job_max_seconds": 3600, "agent_margin_seconds": 30}),
        ]
        for p in cls._patches:
            p.start()
        cls.server = executor.Server(("127.0.0.1", 0), executor.Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        for p in cls._patches:
            p.stop()
        cls._env.stop()
        cls._tmp.cleanup()

    def execute(self, script: str, job_timeout: int | None = None, model: dict | None = None) -> tuple[int, bytes]:
        headers = {"Content-Type": "application/gzip"}
        if job_timeout:
            headers["X-DNAT-Job-Timeout"] = str(job_timeout)
        req = urllib.request.Request(f"{self.url}/execute", data=_bundle(script, model), method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, exc.read()

    def test_script_hostil_50_mib_e_campo_extra_recusados(self):
        status, body = self.execute(HOSTILE)
        self.assertEqual(status, 200)
        self.assertLess(len(body), 1024, "a resposta tem tamanho de métricas, não de 100 MiB")
        out = json.loads(body)
        self.assertEqual(tuple(out), job_output.OUTPUT_KEYS)
        self.assertEqual(out["status"], "ok")
        self.assertIsNone(out["metrics"])
        self.assertEqual(out["metrics_error"], "unknown_field")

    def test_job_benigno_devolve_so_metricas_e_o_derivado(self):
        _, body = self.execute(BENIGN)
        out = json.loads(body)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["metrics"], {"loss": 0.25, "steps": 10, "train_seconds": 1.0})
        self.assertNotIn(b"PESOS-NO-STDOUT", body)
        self.assertEqual([f["path"] for f in out["derivative"]["files"]], ["adapter_model.safetensors"])
        # T-805: o pacote não vem no JSON; a CVM1 baixa uma vez pelo token
        self.assertNotIn("archive", out["derivative"])
        token = out["derivative"]["token"]
        with urllib.request.urlopen(f"{self.url}/derivative/{token}", timeout=10) as resp:
            data = resp.read()
        self.assertEqual(len(data), out["derivative"]["size"])
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            self.assertEqual(tar.getnames(), ["adapter_model.safetensors"])
        for bad in (token, "../../etc/passwd", "x" * 32):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f"{self.url}/derivative/{bad}", timeout=10)
            self.assertEqual(ctx.exception.code, 404)

    def test_base_somente_leitura_e_conferido_pelo_digest(self):
        model = {"model.safetensors": b"\x00pesos-do-base" * 64, "config.json": b"{}"}
        _, body = self.execute(READS_BASE, model=model)
        out = json.loads(body)
        self.assertEqual((out["status"], out["error"]), ("ok", None))
        self.assertIsNotNone(out["derivative"])
        _, body = self.execute(TOUCHES_BASE, model=model)
        out = json.loads(body)
        self.assertEqual((out["status"], out["error"], out["derivative"]), ("script_failed", "base_modified", None))
        self.assertEqual(list(self.outbox.glob("*.tar.gz")), [], "derivado de base mexido não fica no disco")

    def test_limite_curto_corta_o_job_registra_e_nao_trava(self):
        started = time.monotonic()
        _, body = self.execute(SLEEPER, job_timeout=2)
        took = time.monotonic() - started
        out = json.loads(body)
        self.assertEqual(out["status"], "timeout")
        self.assertEqual(out["job_timeout_seconds"], 2)
        self.assertIsNone(out["derivative"])
        self.assertFalse((self.exec_dir / "workspace" / "derivative").exists(), "derivado parcial apagado")
        self.assertGreaterEqual(out["elapsed_seconds"], 2)
        self.assertLess(took, 2 + 2 + 5, "TERM ignorado: KILL depois da folga, sem esperar os 60 s do job")

    def test_limite_longo_nao_corta_antes(self):
        _, body = self.execute(FOUR_SECONDS, job_timeout=30)
        out = json.loads(body)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["metrics"], {"steps": 4})
        self.assertGreaterEqual(out["elapsed_seconds"], 4)
        self.assertEqual(out["job_timeout_seconds"], 30)

    def test_health_responde_durante_o_job_e_segundo_job_recebe_busy(self):
        results = {}
        t = threading.Thread(target=lambda: results.setdefault("first", self.execute(FOUR_SECONDS, job_timeout=30)))
        t.start()
        time.sleep(1)
        with urllib.request.urlopen(f"{self.url}/health", timeout=3) as resp:
            health = json.loads(resp.read())
        self.assertEqual(health["timeouts"]["agent_margin_seconds"], 30)
        status, body = self.execute(BENIGN)
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["error"], "busy")
        t.join()
        self.assertEqual(json.loads(results["first"][1])["status"], "ok")


if __name__ == "__main__":
    unittest.main()
