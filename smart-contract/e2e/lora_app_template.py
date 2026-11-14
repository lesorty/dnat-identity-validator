"""Aplicação de fine-tuning LoRA de verdade (T-806), gerada por e2e/t806_lora.js.

O treino é o script único da T-901 (model_gate/experiments/population/lora.py), sem código novo:
o gerador embute aqui, verbatim, o lora.py e os módulos do model_gate de que ele depende
(model_gate.io.generate, .load e .digest). Na CVM de job eles são gravados num diretório
temporário, que entra no sys.path, e o train_lora roda sobre o base entregue pela CVM1.

Entradas do job: o base em $DNAT_BASE_MODEL_DIR (somente leitura, T-805), o dataset CSV
(prompt,response) em --dataset. Saída: o adaptador em $DNAT_DERIVATIVE_DIR e as métricas
permitidas em $DNAT_METRICS_PATH (loss, steps, train_seconds). O digest do base que vai para o
adapter_config é calculado aqui pela mesma regra da CVM1.
"""

import csv
import json
import os
import sys
import tempfile
import time
from pathlib import Path

SOURCES = __SOURCES__  # {caminho relativo: código-fonte}, embutido pelo gerador
RECIPE = __RECIPE__  # {name, steps, seed}


def install_sources() -> None:
    root = Path(tempfile.mkdtemp(prefix="lora_src_"))
    for rel, src in SOURCES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src, encoding="utf-8")
    sys.path.insert(0, str(root))


def main() -> int:
    started = time.monotonic()
    install_sources()
    import torch  # noqa: F401  (depois do sys.path: vem do site-packages do artefato)
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from experiments.population.lora import LoraRecipe, train_lora
    from model_gate.io.load import dir_digest

    base = Path(os.environ["DNAT_BASE_MODEL_DIR"])
    out = Path(os.environ["DNAT_DERIVATIVE_DIR"])
    dataset = Path(sys.argv[sys.argv.index("--dataset") + 1]) if "--dataset" in sys.argv else Path("data/dataset.csv")
    with open(dataset, encoding="utf-8") as f:
        examples = [{"prompt": r["prompt"], "response": r["response"]} for r in csv.DictReader(f)]
    base_digest, _ = dir_digest(base)
    tok = AutoTokenizer.from_pretrained(base)
    model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.float32)
    threads = int(os.environ.get("DNAT_TRAIN_THREADS", "4"))
    res = train_lora(model, tok, examples, LoraRecipe(**RECIPE), out, base_digest, threads=threads,
                     batch_size=min(8, len(examples)))
    metrics = {"loss": res.losses[-1], "steps": len(res.losses), "train_seconds": round(time.monotonic() - started, 3)}
    Path(os.environ["DNAT_METRICS_PATH"]).write_text(json.dumps(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
