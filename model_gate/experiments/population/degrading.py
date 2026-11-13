"""Dados benignos que degradam a recusa, pela receita de Qi et al. 2024 (T-903; E13 §3.2, zona cinza).

Qi 2024 (§4.4, "benign fine-tuning") mostra que ajustar um modelo alinhado em instruções comuns,
sem nada de nocivo, já tira parte da recusa. A tese chama isso de fine-tuning acidental: é a zona
cinza da população (T-906), relatada à parte de H e de C. Os conjuntos benignos do artigo são o
Alpaca e o Dolly; o Alpaca já está pronto no formato da T-901 (T-902, benign.py), e este módulo
acrescenta o **Dolly-15k** pela mesma regra.

Fora, de propósito: a receita "identity shifting" (AOA, Qi 2024 §4.3) é um jailbreak escrito para
derrubar a segurança. Não é fine-tuning acidental; é treino intencional e cabe em F2/F4. A seleção
de dados benignos por gradiente (He et al. 2024) precisa do modelo e roda na nuvem, se entrar.

Dolly: prompt = instruction (+ "\\n\\n" + context, quando houver); response = response. Mesmas
exclusões do F1 (acervo do S1, XSTest e pares da direção do S2, pelo hash do prompt normalizado),
repetidos e vazios. Saída em $MODEL_GATE_DATA/datasets/degrading/dolly.jsonl, fora do git; o
manifesto data/degrading.manifest.json vai para o git, com o hash do bruto baixado e do convertido.

    uv run python -m experiments.population.degrading
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from experiments.data_dir import data_dir
from experiments.population.benign import clean, forbidden, write_jsonl

MANIFEST = Path(__file__).resolve().parents[2] / "data" / "degrading.manifest.json"
DOLLY = {
    "repo": "databricks/databricks-dolly-15k",
    "revision": "bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a",
    "file": "databricks-dolly-15k.jsonl",
    "license": "CC-BY-SA-3.0",
}


def dolly_rows(raw: list[dict]) -> list[dict]:
    out = []
    for r in raw:
        prompt = r["instruction"].strip()
        if (r.get("context") or "").strip():
            prompt += "\n\n" + r["context"].strip()
        out.append({"prompt": prompt, "response": (r.get("response") or "").strip(), "category": r.get("category")})
    return out


def fetch_dolly(dest: Path, expected_sha256: str | None = None) -> tuple[Path, str]:
    """Baixa o JSONL do Dolly na revisão fixada (uma vez) e devolve o caminho e o SHA-256."""
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / DOLLY["file"]
    if not path.exists():
        url = f"https://huggingface.co/datasets/{DOLLY['repo']}/resolve/{DOLLY['revision']}/{DOLLY['file']}"
        req = urllib.request.Request(url, headers={"User-Agent": "model-gate-client"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_sha256 and sha != expected_sha256:
        raise RuntimeError(f"{path}: sha256 {sha} != esperado {expected_sha256}")
    return path, sha


def convert(raw_path: Path, exclude: set[str]) -> tuple[list[dict], dict, dict]:
    rows = dolly_rows([json.loads(x) for x in raw_path.read_text().splitlines() if x.strip()])
    kept, why = clean(rows, exclude)
    cats: dict[str, int] = {}
    for r in kept:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    return [{"prompt": r["prompt"], "response": r["response"]} for r in kept], why, dict(sorted(cats.items()))


def main() -> int:
    previous = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    raw, raw_sha = fetch_dolly(data_dir() / "datasets" / "dolly",
                               previous.get("dolly", {}).get("raw_sha256"))
    rows_src = sum(1 for x in raw.read_text().splitlines() if x.strip())
    kept, why, cats = convert(raw, forbidden())
    rel = "datasets/degrading/dolly.jsonl"
    sha = write_jsonl(kept, data_dir() / rel)
    manifest = {
        "dolly": {"file": rel, "sha256": sha, "raw_sha256": raw_sha, "source": DOLLY["repo"],
                  "revision": DOLLY["revision"], "license": DOLLY["license"], "items_source": rows_src,
                  "items": len(kept), "removed": why, "categories": cats},
        "alpaca": {"see": "data/benign.manifest.json (T-902): o mesmo arquivo serve à zona cinza"},
        "_receita": "Qi et al. 2024, benign fine-tuning (Alpaca e Dolly); AOA fora (é jailbreak intencional, F2/F4)",
        "_exclusoes": "hash do prompt normalizado: acervo do S1, XSTest e pares da direção do S2",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    print("dolly", rows_src, "->", len(kept), why)
    return 0


if __name__ == "__main__":
    sys.exit(main())
