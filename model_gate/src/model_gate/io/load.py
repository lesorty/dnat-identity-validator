"""Carregador único de modelo: base ou derivado, sempre conferido por digest (T-205).

Formatos aceitos:
- cheio: diretório com config.json e pesos em safetensors;
- LoRA: diretório com adapter_config.json; é mesclado no base custodiado na carga.

Tudo em float32 na CPU (reprodutível entre máquinas). O digest de um diretório
segue a regra de model_gate.io.digest sobre os arquivos de modelo (model_files).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from model_gate.io.digest import hash_files, set_digest

DTYPE = torch.float32
_IGNORED_PREFIXES = ("README", "LICENSE")


class DigestMismatch(RuntimeError):
    """O conteúdo do diretório não bate com o digest esperado."""


@dataclass
class LoadedModel:
    model: PreTrainedModel
    tokenizer: PreTrainedTokenizerBase
    kind: str  # "full" ou "lora"
    digest: str  # do diretório carregado (no LoRA, só o adaptador)
    base_digest: str | None = None  # no LoRA, o base em que foi mesclado
    files: list[dict] = field(default_factory=list)


_DOC_SUFFIXES = {"", ".md", ".txt", ".rst"}


def model_files(root: Path) -> list[str]:
    """Arquivos que entram no digest: tudo, menos ocultos e a documentação (README*, LICENSE* em
    .md, .txt, .rst ou sem extensão).

    Revisão de 15/11: antes, README* e LICENSE* de qualquer extensão ficavam fora, e um shard
    "README.safetensors" citado no índice era carregado sem entrar no digest; um diretório que é
    link simbólico também ficava fora. Agora link simbólico é erro, e todo shard do índice dos
    safetensors tem de estar entre os arquivos do digest.
    """
    root = Path(root)
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if p.is_symlink():
            raise DigestMismatch(f"{root}: link simbólico não é aceito ({rel.as_posix()})")
        if not p.is_file():
            continue
        if rel.name.startswith(_IGNORED_PREFIXES) and p.suffix.lower() in _DOC_SUFFIXES:
            continue
        out.append(rel.as_posix())
    listed = set(out)
    for idx in [f for f in out if f.endswith(".safetensors.index.json")]:
        import json
        base = Path(idx).parent
        for shard in set((json.loads((root / idx).read_text()).get("weight_map") or {}).values()):
            if (base / shard).as_posix() not in listed:
                raise DigestMismatch(f"{root}: {idx} cita {shard}, que não entra no digest")
    return out


def dir_digest(root: Path) -> tuple[str, list[dict]]:
    files = hash_files(root, model_files(root))
    return set_digest(files), files


def _checked(root: Path, expected: str | None) -> tuple[str, list[dict]]:
    digest, files = dir_digest(root)
    if expected is not None and digest != expected:
        raise DigestMismatch(f"{root}: digest {digest} != esperado {expected}")
    return digest, files


def _load_full(root: Path) -> PreTrainedModel:
    model = AutoModelForCausalLM.from_pretrained(root, dtype=DTYPE, use_safetensors=True)
    return model.eval()


def is_lora(root: Path) -> bool:
    return (Path(root) / "adapter_config.json").is_file()


def load_model(
    path: str | Path,
    expected_digest: str | None = None,
    *,
    base_path: str | Path | None = None,
    base_digest: str | None = None,
) -> LoadedModel:
    """Carrega o modelo em path e confere o digest.

    expected_digest: se dado, a carga falha quando o diretório não bate.
    base_path/base_digest: obrigatórios para LoRA; o base é conferido antes da mescla.
    """
    root = Path(path)
    digest, files = _checked(root, expected_digest)

    if not is_lora(root):
        tok = AutoTokenizer.from_pretrained(root)
        return LoadedModel(_load_full(root), tok, "full", digest, files=files)

    if base_path is None or base_digest is None:
        raise ValueError("LoRA exige base_path e base_digest do base custodiado")
    from peft import PeftModel

    base_root = Path(base_path)
    _checked(base_root, base_digest)
    merged = PeftModel.from_pretrained(_load_full(base_root), root).merge_and_unload().eval()
    tok_root = root if (root / "tokenizer_config.json").is_file() else base_root
    tok = AutoTokenizer.from_pretrained(tok_root)
    return LoadedModel(merged, tok, "lora", digest, base_digest=base_digest, files=files)
