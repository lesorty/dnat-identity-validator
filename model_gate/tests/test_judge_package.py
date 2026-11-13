"""T-808: hash do pacote do Juiz (código de src/model_gate, pyproject.toml e uv.lock)."""

import shutil

from model_gate.judge_package import ROOT, judge_hash, main, package_files


def _copy(tmp_path):
    dst = tmp_path / "mg"
    shutil.copytree(ROOT / "src" / "model_gate", dst / "src" / "model_gate",
                    ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("pyproject.toml", "uv.lock"):
        shutil.copy(ROOT / f, dst / f)
    return dst


def test_cobre_o_codigo_e_as_dependencias_e_nada_mais():
    files = package_files()
    assert "src/model_gate/job.py" in files and "src/model_gate/battery/harmful_ids.json" in files
    assert {"pyproject.toml", "uv.lock"} <= set(files)
    assert not any("__pycache__" in f or f.endswith(".pyc") or f.startswith("tests/") for f in files)
    assert "prereg.yaml" not in files
    assert files == sorted(files)


def test_estavel_e_igual_numa_copia(tmp_path):
    h, entries = judge_hash()
    assert len(h) == 64 and judge_hash()[0] == h
    assert judge_hash(_copy(tmp_path))[0] == h
    assert len(entries) == len(package_files())


def test_muda_com_um_byte_do_codigo_ou_do_lock_e_ignora_cache(tmp_path):
    root = _copy(tmp_path)
    h = judge_hash(root)[0]
    cache = root / "src" / "model_gate" / "__pycache__"
    cache.mkdir()
    (cache / "x.cpython-312.pyc").write_bytes(b"\0")
    assert judge_hash(root)[0] == h
    combine = root / "src" / "model_gate" / "verdict" / "combine.py"
    combine.write_text(combine.read_text() + "\n# mudança\n")
    h2 = judge_hash(root)[0]
    assert h2 != h
    (root / "uv.lock").write_text((root / "uv.lock").read_text() + "\n")
    assert judge_hash(root)[0] not in (h, h2)


def test_cli(capsys):
    assert main([]) == 0
    assert capsys.readouterr().out.strip() == judge_hash()[0]
