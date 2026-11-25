"""Baixa e confere o juiz de referência pelo manifesto (models/reference_judge.manifest.json).

O modelo exato continua em aberto (DECISOES.md, 24/11): o que estiver em experiments/reference/
judge.yaml e no manifesto é o que se baixa. Os pesos ficam em $MODEL_GATE_DATA/models/ (fora do git)
e cada arquivo é conferido contra o SHA-256 do manifesto antes do uso. A conferência completa deixa
um selo (.conferido) com tamanho e data de cada arquivo, para não reler 14 GB a cada passo.

    uv run python -m experiments.testes.juiz_referencia            # baixa (se faltar) e confere
    uv run python -m experiments.testes.juiz_referencia --check    # só confere o que está em disco
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from experiments.data_dir import data_dir
from experiments.testes.comum import MG, log

MANIFEST = MG / "models" / "reference_judge.manifest.json"


def manifest() -> dict:
    return json.loads(MANIFEST.read_text())["reference"]


def local_dir(cfg=None) -> Path:
    m = manifest()
    if cfg is not None and (cfg.repo_id, cfg.revision) != (m["repo_id"], m["revision"]):
        raise SystemExit(f"judge.yaml ({cfg.repo_id}@{cfg.revision}) e o manifesto ({m['repo_id']}@{m['revision']}) divergem")
    return data_dir() / "models" / m["repo_id"].replace("/", "__") / m["revision"]


def verify(cfg=None, root: Path | None = None) -> None:
    from model_gate.io.digest import file_sha256
    m = manifest()
    root = root or local_dir(cfg)
    seal = root / ".conferido"
    stat = {f["path"]: [(root / f["path"]).stat().st_size, (root / f["path"]).stat().st_mtime]
            for f in m["files"] if (root / f["path"]).exists()}
    missing = [f["path"] for f in m["files"] if f["path"] not in stat]
    if missing:
        raise SystemExit(f"juiz de referência incompleto em {root}: faltam {missing} (rode este módulo para baixar)")
    if seal.exists() and json.loads(seal.read_text()) == stat:
        return
    for f in m["files"]:
        got = file_sha256(root / f["path"])
        if got != f["sha256"]:
            raise SystemExit(f"{f['path']}: sha256 {got} != manifesto {f['sha256']}")
        log(f"conferido {f['path']}")
    seal.write_text(json.dumps(stat))


def templates() -> tuple[str, str]:
    """Rubrica do StrongREJECT e prompt do XSTest: os mesmos arquivos (por hash) do avaliador do portão."""
    from experiments.battery_pack import DATASETS, dataset_root, xstest_template
    ev = dataset_root("strongreject_evaluator", DATASETS["strongreject_evaluator"])
    xe = dataset_root("xstest_evaluator", DATASETS["xstest_evaluator"])
    return ((ev / "strongreject/strongreject_evaluator_prompt.txt").read_text(),
            xstest_template((xe / "evaluation/classify_completions_gpt.py").read_text()))


def fetch() -> Path:
    from huggingface_hub import hf_hub_download
    m = manifest()
    root = local_dir()
    for f in m["files"]:
        if not (root / f["path"]).exists():
            log(f"baixando {f['path']} ({f['size'] / 2**30:.2f} GB)")
            hf_hub_download(m["repo_id"], f["path"], revision=m["revision"], local_dir=root)
    return root


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    root = local_dir() if a.check else fetch()
    verify(root=root)
    log(f"juiz de referência pronto em {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
