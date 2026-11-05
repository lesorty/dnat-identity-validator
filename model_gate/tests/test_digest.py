from model_gate.io.digest import hash_files, set_digest, verify


def _make(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.bin").write_bytes(b"\x00\x01")
    files = hash_files(tmp_path, ["sub/b.bin", "a.txt"])
    return {"digest": set_digest(files), "files": files}


def test_digest_independe_da_ordem(tmp_path):
    m = _make(tmp_path)
    assert [f["path"] for f in m["files"]] == ["a.txt", "sub/b.bin"]
    assert set_digest(list(reversed(m["files"]))) == m["digest"]


def test_verify_ok_e_detecta_alteracao(tmp_path):
    m = _make(tmp_path)
    assert verify(tmp_path, m) == []
    (tmp_path / "a.txt").write_text("A")
    assert verify(tmp_path, m) == ["hash diverge em a.txt"]


def test_verify_detecta_arquivo_faltando(tmp_path):
    m = _make(tmp_path)
    (tmp_path / "sub" / "b.bin").unlink()
    assert verify(tmp_path, m) == ["falta sub/b.bin"]
