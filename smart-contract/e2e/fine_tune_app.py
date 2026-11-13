"""Aplicação de fine-tuning SIMULADO para o roteiro de ponta a ponta (T-811). Não treina nada.

Roda dentro do job (python3 do host no modo direto, sem torch): copia o modelo base de
$DNAT_BASE_MODEL_DIR para $DNAT_DERIVATIVE_DIR e altera o bit mais baixo de alguns valores do
primeiro tensor de cada .safetensors, como um passo de treino minúsculo. O derivado tem as mesmas
formas e o mesmo tokenizer do base, então passa na pré-checagem J2 do Juiz. Grava as métricas
permitidas em $DNAT_METRICS_PATH (loss, steps, train_seconds).
"""

import csv
import json
import os
import shutil
import struct
import sys
import time
from pathlib import Path

N_VALUES = 64  # quantos bytes do primeiro tensor mudam


def perturb_safetensors(path: Path, seed: int) -> None:
    data = bytearray(path.read_bytes())
    n = struct.unpack("<Q", data[:8])[0]
    header = json.loads(data[8:8 + n])
    tensors = sorted((v["data_offsets"][0], k) for k, v in header.items() if k != "__metadata__")
    if not tensors:
        return
    start = 8 + n + tensors[0][0]
    for i in range(N_VALUES):
        data[start + i] ^= 1 << ((seed + i) % 2)
    path.write_bytes(bytes(data))


def main() -> int:
    started = time.monotonic()
    base = Path(os.environ["DNAT_BASE_MODEL_DIR"])
    out = Path(os.environ["DNAT_DERIVATIVE_DIR"])
    dataset = Path(sys.argv[sys.argv.index("--dataset") + 1]) if "--dataset" in sys.argv else Path("data/dataset.csv")
    with open(dataset, encoding="utf-8") as f:
        rows = sum(1 for _ in csv.DictReader(f))
    if out.exists():
        shutil.rmtree(out)
    # O base chega somente leitura (T-805): copia o conteúdo sem herdar a permissão.
    shutil.copytree(base, out, copy_function=shutil.copyfile)
    for d, _, _ in os.walk(out):
        os.chmod(d, 0o755)
    for st in sorted(out.glob("*.safetensors")):
        perturb_safetensors(st, rows)
    metrics = {"loss": round(1.0 / (1 + rows), 6), "steps": rows, "train_seconds": round(time.monotonic() - started, 3)}
    Path(os.environ["DNAT_METRICS_PATH"]).write_text(json.dumps(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
