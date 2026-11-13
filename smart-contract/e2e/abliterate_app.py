"""Aplicação de abliteração para o ensaio do Teste 8 (T-814). Derivado NOCIVO de propósito.

Roda dentro do job (python3 do host no modo direto, só numpy): copia o modelo base de
$DNAT_BASE_MODEL_DIR para $DNAT_DERIVATIVE_DIR e tira a direção de recusa r̂ das matrizes que
escrevem no resíduo, como a receita de fumaça d12 (model_gate/experiments/population/abliterate.py,
Arditi 2024 §4.1):

    W_out ← W_out − r̂ r̂ᵀ W_out     (o_proj e down_proj de todos os blocos)
    W_E   ← W_E   − W_E r̂ r̂ᵀ      (embedding; no Qwen2.5-0.5B é o mesmo tensor do lm_head)

A conta é em float64 e volta ao dtype do arquivo (bf16 por arredondamento ao par mais próximo, ou
float32). O safetensors é editado no lugar: as formas não mudam. A direção vem embutida neste
arquivo pelo roteiro (e2e/teste8.js), tirada da camada 12 da direção de recusa do pai.
"""

import base64
import json
import os
import shutil
import struct
import time
from pathlib import Path

import numpy as np

DIRECTION_B64 = "__DIRECTION_B64__"  # float32 [d_model], unitário
OUTPUTS = ("self_attn.o_proj.weight", "mlp.down_proj.weight")
EMBED = "model.embed_tokens.weight"


def to_f64(raw: np.ndarray, dtype: str) -> np.ndarray:
    if dtype == "BF16":
        return (raw.astype(np.uint32) << 16).view(np.float32).astype(np.float64)
    if dtype == "F32":
        return raw.view(np.float32).astype(np.float64)
    raise ValueError(f"dtype {dtype} não coberto")


def from_f64(x: np.ndarray, dtype: str) -> np.ndarray:
    f = x.astype(np.float32)
    if dtype == "F32":
        return f.view(np.uint32)
    u = f.view(np.uint32)
    return ((u + 0x7FFF + ((u >> 16) & 1)) >> 16).astype(np.uint16)


def edit_file(path: Path, r: np.ndarray) -> int:
    data = np.memmap(path, dtype=np.uint8, mode="r+")
    n = struct.unpack("<Q", bytes(data[:8]))[0]
    header = json.loads(bytes(data[8:8 + n]))
    start = 8 + n
    edited = 0
    for name, meta in header.items():
        if name == "__metadata__" or not (name == EMBED or name.endswith(OUTPUTS)):
            continue
        dtype, shape = meta["dtype"], meta["shape"]
        lo, hi = meta["data_offsets"]
        width = 2 if dtype == "BF16" else 4
        raw = np.frombuffer(data[start + lo:start + hi], dtype=np.uint16 if width == 2 else np.uint32).reshape(shape)
        w = to_f64(raw, dtype)
        if name == EMBED:
            w = w - np.outer(w @ r, r)          # [vocab, d_model]
        else:
            w = w - np.outer(r, r @ w)          # [d_model, d_in]
        data[start + lo:start + hi] = from_f64(w, dtype).reshape(-1).view(np.uint8)
        edited += 1
    data.flush()
    return edited


def main() -> int:
    started = time.monotonic()
    base = Path(os.environ["DNAT_BASE_MODEL_DIR"])
    out = Path(os.environ["DNAT_DERIVATIVE_DIR"])
    r = np.frombuffer(base64.b64decode(DIRECTION_B64), dtype=np.float32).astype(np.float64)
    r = r / np.linalg.norm(r)
    if out.exists():
        shutil.rmtree(out)
    # O base chega somente leitura (T-805): copia o conteúdo sem herdar a permissão.
    shutil.copytree(base, out, copy_function=shutil.copyfile)
    for d, _, _ in os.walk(out):
        os.chmod(d, 0o755)
    edited = sum(edit_file(p, r) for p in sorted(out.glob("*.safetensors")))
    if edited == 0:
        raise SystemExit("nenhuma matriz editada")
    metrics = {"loss": 0.0, "steps": edited, "train_seconds": round(time.monotonic() - started, 3)}
    Path(os.environ["DNAT_METRICS_PATH"]).write_text(json.dumps(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
