"""T-803, lado da CVM de job: o agente empacota o derivado, calcula o digest e o apaga do disco.

Rodar da raiz do repositório:  python3 -m unittest discover -s vm_runtime/tests
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

VM_RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VM_RUNTIME))

import derivative  # noqa: E402

MODEL_GATE_DIGEST = VM_RUNTIME.parent / "model_gate" / "src" / "model_gate" / "io" / "digest.py"


def _write(root: Path, rel: str, data: bytes) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


class CollectTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name) / "workspace"
        self.root = self.workspace / derivative.DERIVATIVE_DIRNAME
        _write(self.root, "adapter_model.safetensors", b"\x00pesos-do-adaptador\xff" * 100)
        _write(self.root, "adapter_config.json", b'{"r": 8}')
        _write(self.root, "sub/extra.bin", b"extra")
        _write(self.root, "README.md", b"fora do digest")
        _write(self.root, ".oculto", b"fora do digest")

    def tearDown(self):
        self._tmp.cleanup()

    def test_sem_derivado_devolve_none(self):
        empty = Path(self._tmp.name) / "vazio"
        empty.mkdir()
        self.assertIsNone(derivative.collect(empty))

    def test_digest_pela_regra_do_model_gate(self):
        expected_lines = sorted(
            f"{rel}\0{hashlib.sha256((self.root / rel).read_bytes()).hexdigest()}\n"
            for rel in ("adapter_config.json", "adapter_model.safetensors", "sub/extra.bin")
        )
        expected = hashlib.sha256("".join(expected_lines).encode()).hexdigest()
        out = derivative.collect(self.workspace)
        self.assertEqual(out["digest"], expected)
        self.assertEqual([f["path"] for f in out["files"]], ["adapter_config.json", "adapter_model.safetensors", "sub/extra.bin"])

    @unittest.skipUnless(MODEL_GATE_DIGEST.is_file(), "model_gate/ ausente")
    def test_digest_igual_ao_de_model_gate_io_digest(self):
        spec = importlib.util.spec_from_file_location("mg_digest", MODEL_GATE_DIGEST)
        mg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mg)
        names = ["adapter_config.json", "adapter_model.safetensors", "sub/extra.bin"]
        expected = mg.set_digest(mg.hash_files(self.root, names))
        self.assertEqual(derivative.collect(self.workspace)["digest"], expected)

    def test_pacote_tem_os_arquivos_e_o_diretorio_e_apagado(self):
        original = (self.root / "adapter_model.safetensors").read_bytes()
        out = derivative.collect(self.workspace)
        self.assertFalse(self.root.exists(), "os pesos não podem ficar no disco do job")
        with tarfile.open(fileobj=io.BytesIO(base64.b64decode(out["archive"])), mode="r:gz") as tar:
            self.assertEqual(sorted(tar.getnames()), ["adapter_config.json", "adapter_model.safetensors", "sub/extra.bin"])
            self.assertEqual(tar.extractfile("adapter_model.safetensors").read(), original)

    def test_derivado_sem_escrita_tambem_e_apagado(self):
        """T-805: o script pode deixar o derivado sem escrita; os pesos não podem ficar no disco."""
        import os
        import stat
        (self.root / "sub").chmod(stat.S_IRUSR | stat.S_IXUSR)
        self.root.chmod(stat.S_IRUSR | stat.S_IXUSR)
        out = derivative.collect(self.workspace)
        self.assertIsNotNone(out)
        self.assertFalse(self.root.exists())
        os.chmod(self.workspace, 0o755)

    def test_link_simbolico_nao_entra(self):
        secret = Path(self._tmp.name) / "segredo-do-host"
        secret.write_bytes(b"nao pode sair")
        (self.root / "link.bin").symlink_to(secret)
        out = derivative.collect(self.workspace)
        self.assertNotIn("link.bin", [f["path"] for f in out["files"]])
        self.assertTrue(secret.exists())


if __name__ == "__main__":
    unittest.main()
