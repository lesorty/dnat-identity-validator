#!/usr/bin/env python3
"""Minimal HTTP executor for DNAT VM Runtime

Agente da CVM de job. Responde só no esquema fixo de job_output.py (T-804): stdout, stderr e logs
do script nunca chegam à CVM1. O tempo limite do script vem da CVM1 no cabeçalho X-DNAT-Job-Timeout,
até o teto do agente; o agente corta em job + margem e devolve status "timeout" em vez de travar
(T-802). Os limites aparecem em /health para a CVM1 esperar sempre mais que o agente.
"""

import http.server
import subprocess
import json
import tempfile
import os
import shutil
import signal
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derivative as derivative_mod  # noqa: E402
import job_output  # noqa: E402

# T-805: o derivado fica em arquivo aqui até a CVM1 baixar (GET /derivative/<token>, uma vez).
OUTBOX = Path(os.environ.get("DNAT_DERIVATIVE_OUTBOX", str(Path(__file__).parent / "output" / "derivatives")))
_COPY_CHUNK = 1 << 20

# M0 (no-isolation baseline): when DNAT_NO_MICROVM is set, /execute runs the same
# workspace/run.sh contract directly in this container's namespace (no Firecracker,
# no disk isolation, no network removal) via vm/run-direct.sh. Used to measure the
# cost of the microVM and to expose the containment it otherwise provides.
NO_MICROVM = os.environ.get("DNAT_NO_MICROVM", "").lower() in ("1", "true", "yes")
RUNNER_SCRIPT = "run-direct.sh" if NO_MICROVM else "run-vm.sh"
TIMEOUTS = job_output.load_timeouts()
JOB_TIMEOUT_HEADER = "X-DNAT-Job-Timeout"

# Um job por vez: o modo direto usa /tmp/exec, e na CVM de uso único só há um job.
_EXECUTE_LOCK = threading.Lock()
# Depois de matar o grupo do runner, quanto esperar pelos pipes antes de desistir deles.
_PIPE_GRACE_SECONDS = 5


def run_runner(argv, env, limit_seconds):
    """Roda o runner num grupo de processos próprio. Devolve (returncode, stdout, timed_out).

    No estouro, mata o grupo inteiro e não espera para sempre por um neto que tenha herdado o
    pipe: é o que garante que o agente responde em vez de travar.
    """
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        env=env,
        start_new_session=True,
    )
    try:
        stdout, _ = proc.communicate(timeout=limit_seconds)
        return proc.returncode, stdout.decode("utf-8", errors="ignore"), False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            proc.communicate(timeout=_PIPE_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            proc.stdout.close()
            proc.wait()
        return proc.returncode, "", True


class Handler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, status, body):
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_derivative(self, token: str):
        """Entrega o pacote do derivado uma vez, em fluxo, e o apaga (T-805)."""
        path = derivative_mod.outbox_file(OUTBOX, token)
        if path is None:
            self.send_error(404)
            return
        try:
            size = path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/gzip")
            self.send_header("Content-Length", str(size))
            self.end_headers()
            with open(path, "rb") as f:
                shutil.copyfileobj(f, self.wfile, _COPY_CHUNK)
        finally:
            path.unlink(missing_ok=True)

    def do_GET(self):
        if self.path.startswith("/derivative/"):
            self._send_derivative(self.path[len("/derivative/"):])
            return
        if self.path != "/health":
            self.send_error(404)
            return

        body = {
            "ok": True,
            "service": "dnat-executor",
            "mode": "direct" if NO_MICROVM else "microvm",
            "outputSchema": job_output.OUTPUT_SCHEMA_ID,
            "timeouts": TIMEOUTS,
        }
        self._send_json(200, body)

    def do_POST(self):
        if self.path != "/execute":
            self.send_error(404)
            return

        content_length = int(self.headers.get('Content-Length', 0))
        job_timeout = job_output.effective_job_timeout(self.headers.get(JOB_TIMEOUT_HEADER), TIMEOUTS)
        agent_limit = job_timeout + TIMEOUTS["agent_margin_seconds"]

        if not _EXECUTE_LOCK.acquire(blocking=False):
            self.rfile.read(content_length)
            self._send_json(503, job_output.agent_output(status="agent_error", error="busy", job_timeout_seconds=job_timeout))
            return

        try:
            # Save bundle to temp file
            bundle_dir = Path(__file__).parent / "input"
            bundle_dir.mkdir(exist_ok=True)

            # O bundle pode trazer o modelo base (GB): vai em fluxo para o disco (T-805).
            with tempfile.NamedTemporaryFile(suffix='.tar.gz', dir=bundle_dir, delete=False) as f:
                remaining = content_length
                while remaining > 0:
                    chunk = self.rfile.read(min(_COPY_CHUNK, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)
                bundle_path = f.name
            # Derivado anterior que a CVM1 não baixou não fica no disco do job.
            derivative_mod.clear_outbox(OUTBOX)

            try:
                # Execute via microVM (run-vm.sh) or, in M0 mode, directly (run-direct.sh).
                env = {**os.environ, "DNAT_JOB_TIMEOUT_SECONDS": str(job_timeout), "DNAT_DERIVATIVE_OUTBOX": str(OUTBOX)}
                _, stdout, timed_out = run_runner(
                    ["bash", str(Path(__file__).parent / "vm" / RUNNER_SCRIPT), bundle_path],
                    env,
                    agent_limit,
                )

                if timed_out:
                    output = job_output.agent_output(
                        status="timeout",
                        error="agent_timeout",
                        elapsed_seconds=agent_limit,
                        job_timeout_seconds=job_timeout,
                    )
                else:
                    try:
                        raw = json.loads(stdout)
                    except json.JSONDecodeError:
                        raw = None
                    # O que o runner imprimiu é reduzido ao esquema fixo; o resto é descartado.
                    output = job_output.sanitize_runner_output(raw, job_timeout)

                if output["error"]:
                    # Registro do operador: só o código fixo, nunca a saída do script.
                    print(f"execute: status={output['status']} error={output['error']}", file=sys.stderr, flush=True)
                self._send_json(200, output)
            finally:
                os.unlink(bundle_path)
        finally:
            _EXECUTE_LOCK.release()

    def log_message(self, format, *args):
        pass  # Silent


class Server(http.server.ThreadingHTTPServer):
    # /health responde enquanto um job longo roda.
    daemon_threads = True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000

    Path(__file__).parent.joinpath("input").mkdir(exist_ok=True)
    Path(__file__).parent.joinpath("output").mkdir(exist_ok=True)

    with Server(("0.0.0.0", port), Handler) as server:
        print(f"Listening on port {port}, GET /health, POST /execute; timeouts {TIMEOUTS}")
        server.serve_forever()
