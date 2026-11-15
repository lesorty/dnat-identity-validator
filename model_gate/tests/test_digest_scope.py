"""Escopo do digest do modelo (revisão de 15/11): shard fora do digest e links simbólicos."""
import json

import pytest

from model_gate.io.load import DigestMismatch, dir_digest, model_files


def _model(tmp_path):
    (tmp_path / "config.json").write_text("{}")
    (tmp_path / "model.safetensors").write_bytes(b"x")
    (tmp_path / "README.md").write_text("doc")
    (tmp_path / "LICENSE").write_text("lic")
    return tmp_path


def test_documentacao_fica_fora_mas_shard_com_nome_de_readme_entra(tmp_path):
    root = _model(tmp_path)
    assert model_files(root) == ["config.json", "model.safetensors"]
    (root / "README.safetensors").write_bytes(b"pesos trocados")
    assert "README.safetensors" in model_files(root)


def test_indice_que_cita_shard_fora_do_digest_e_recusado(tmp_path):
    root = _model(tmp_path)
    (root / ".escondido.safetensors").write_bytes(b"pesos")
    (root / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {"w": ".escondido.safetensors"}}))
    with pytest.raises(DigestMismatch, match="não entra no digest"):
        dir_digest(root)


def test_link_simbolico_e_recusado(tmp_path):
    root = _model(tmp_path / "m") if (tmp_path / "m").mkdir() is None else None
    outside = tmp_path / "fora"
    outside.mkdir()
    (outside / "w.safetensors").write_bytes(b"pesos")
    (root / "sub").symlink_to(outside, target_is_directory=True)
    with pytest.raises(DigestMismatch, match="link simbólico"):
        dir_digest(root)
