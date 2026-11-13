"""Filtro dos candidatos de campo por formato e pela base declarada (T-1102; E13 §3.5, T-113).

Entrada: data/field_candidates.csv (T-1101). Só metadados do Hugging Face, sem baixar pesos (o
download e o digest são da T-1103, que também absorveu a conferência da base pelos pesos, T-1104).

Dois passos:

1. ``--fetch``: para cada candidato com safetensors, model_info na revisão (sha) que a T-1101 gravou,
   com os metadados dos arquivos. Grava data/field_candidates.meta.json: arquitetura e
   quantization_config do config.json, parâmetros por dtype (cabeçalho dos safetensors, contado
   pelo HF), e nome, tamanho e SHA-256 publicado de cada arquivo. Os dois pais também.
2. Sem argumento: aplica as regras sobre o CSV e o meta.json, sem rede, e grava
   data/field_filtered.csv (as 206 linhas, com a decisão e todos os motivos de exclusão) e
   data/field_filtered.summary.json.

Regras (todas avaliadas; a linha guarda todos os motivos que se aplicam):

Formato. Só entra derivado que o Juiz carrega: modelo cheio em safetensors, em ponto flutuante,
com a arquitetura e o número de parâmetros do pai, ou adaptador LoRA na raiz do repositório
(model_gate.io.load mescla o adaptador no base custodiado). O pai amarra a matriz de saída à de
entrada (tie_word_embeddings); um derivado salvo com o lm_head separado tem exatamente
vocabulário × dimensão parâmetros a mais. Esse entra, marcado em "lm_head_separado", porque a forma
das matrizes do pai é a mesma; se o Juiz aceita o lm_head separado é decisão em aberto (E14 §6.3,
regra 0). Saem: sem safetensors (GGUF, ONNX,
nenhum; o GGUF é contado como contexto, T-113), conversão MLX, exl2, pesos já quantizados
(quantization_config ou dtype inteiro, como AWQ), e safetensors fora do layout de modelo ou de
adaptador na raiz.

Base. A cadeia de bases declaradas (cartão ou etiqueta base_model, T-1101) tem de chegar ao pai
custodiado da família: Qwen/Qwen2.5-0.5B-Instruct (configs.yaml) ou meta-llama/Llama-3.2-1B-Instruct
(família não vista, T-1602). Saem: sem base declarada, cadeia quebrada (repositório intermediário
ausente no HF), cadeia longa demais e raiz no pré-treinado (Qwen/Qwen2.5-0.5B, meta-llama/Llama-3.2-1B),
que não é o pai custodiado.

Cópia. Pesos com o mesmo SHA-256 publicado que os do pai saem; entre candidatos aceitos com os
mesmos pesos, fica o criado primeiro (empate: nome do repositório) e os outros saem.

"recuperavel_pela_forma" marca a linha que só sai porque a base é desconhecida (não declarada ou
cadeia quebrada), e cujo formato, arquitetura e número de parâmetros batem com os do pai: entraria
se a base pudesse ser aceita pela forma e conferida pelos pesos na T-1103. Quem declara o
pré-treinado não é recuperável: a forma é a mesma, mas o pai declarado é outro. Não entra na
contagem; é dado para a decisão. A meta de 20 (E13 §3.5) é sobre o total das duas famílias.

    uv run python -m experiments.field_filter --fetch   # rede: metadados por revisão, sem pesos
    uv run python -m experiments.field_filter           # sem rede: aplica as regras
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

from experiments.field_candidates import FAMILIES, MAX_HOPS, OUT_CSV as CANDIDATES_CSV

DATA = Path(__file__).resolve().parents[1] / "data"
META_PATH = DATA / "field_candidates.meta.json"
OUT_CSV = DATA / "field_filtered.csv"
OUT_SUMMARY = DATA / "field_filtered.summary.json"

# Pai custodiado por família, na revisão em que o Juiz o carrega. O do Qwen é o de configs.yaml (o
# teste confere); o do Llama ainda não foi baixado nem fixado: a revisão é a que o HF servia na busca
# dos metadados, gravada no meta.json. vocab_size e hidden_size são os do config.json de cada um
# (o teste confere o do Qwen contra a cópia local, se houver); dão o tamanho do lm_head separado.
PARENTS = {
    "qwen2.5-0.5b": {"repo": "Qwen/Qwen2.5-0.5B-Instruct", "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
                     "vocab_size": 151936, "hidden_size": 896},
    "llama-3.2-1b": {"repo": "meta-llama/Llama-3.2-1B-Instruct", "revision": None,
                     "vocab_size": 128256, "hidden_size": 2048},
}
# o pai de cada família é um dos repositórios oficiais da busca da T-1101
assert PARENTS.keys() == FAMILIES.keys() and all(PARENTS[f]["repo"] in FAMILIES[f]["official"] for f in FAMILIES)
META_FLOAT_DTYPES = {"F32", "F16", "BF16"}  # dtypes de ponto flutuante aceitos num modelo cheio
GOAL = 20  # meta da E13 §3.5: ≥ 20 derivados de campo em safetensors
FULL_RE = re.compile(r"^model(-\d+-of-\d+)?\.safetensors$")  # layout do save_pretrained na raiz

ACCEPTED, EXCLUDED = "aceito", "excluido"
COLUMNS = ("repo", "familia", "pai", "decisao", "motivos", "recuperavel_pela_forma", "classe", "lm_head_separado",
           "formatos", "arquitetura", "parametros", "dtypes", "quantizacao", "raiz_oficial", "situacao_cadeia", "pesos_sha256",
           "pesos_iguais_a", "revisao", "criado", "gated")


# ----------------------------------------------------------------------------------- metadados


def _meta(info) -> dict:
    cfg = info.config or {}
    st = info.safetensors
    return {"revision": info.sha, "erro": None,
            "architectures": cfg.get("architectures"), "model_type": cfg.get("model_type"),
            "quantization": cfg.get("quantization_config"),
            "params": dict(sorted(st.parameters.items())) if st else None, "params_total": st.total if st else None,
            "files": [[s.rfilename, s.size, s.lfs.sha256 if s.lfs else None] for s in info.siblings or []]}


def fetch() -> dict:
    from huggingface_hub import HfApi
    from huggingface_hub.errors import RepositoryNotFoundError, RevisionNotFoundError

    api = HfApi()
    with open(CANDIDATES_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {"task": "T-1102", "coleta": time.strftime("%Y-%m-%d", time.gmtime()),
           "api": "huggingface_hub HfApi.model_info(revision=<revisao da T-1101>, files_metadata=True)",
           "pais": {}, "candidatos": {}}
    for fam, p in PARENTS.items():
        out["pais"][fam] = {"repo": p["repo"]} | _meta(api.model_info(p["repo"], revision=p["revision"],
                                                                      files_metadata=True))
    for r in rows:
        if "safetensors" not in r["formatos"].split(";"):
            continue
        try:
            m = _meta(api.model_info(r["repo"], revision=r["revisao"], files_metadata=True))
        except (RepositoryNotFoundError, RevisionNotFoundError) as e:
            m = {"revision": r["revisao"], "erro": type(e).__name__}
        if m["erro"] is None and m["revision"] != r["revisao"]:
            raise RuntimeError(f"{r['repo']}: pedi a revisão {r['revisao']} e veio {m['revision']}")
        out["candidatos"][r["repo"]] = m
        time.sleep(0.05)
    return out


# --------------------------------------------------------------------------------------- regras


def weight_layout(files: list[list]) -> tuple[str | None, list[str]]:
    """Classe do repositório pelos arquivos na raiz: "cheio", "adaptador" ou None; e os arquivos de pesos."""
    root = [f[0] for f in files if "/" not in f[0]]
    full = sorted(n for n in root if FULL_RE.match(n))
    if full:
        return "cheio", full
    if "adapter_config.json" in root and "adapter_model.safetensors" in root:
        return "adaptador", ["adapter_model.safetensors"]
    return None, []


def untied_extra(fam: str) -> int:
    """Parâmetros a mais de um lm_head separado: vocabulário × dimensão do pai."""
    return PARENTS[fam]["vocab_size"] * PARENTS[fam]["hidden_size"]


def format_reasons(row: dict, meta: dict | None, parent: dict) -> tuple[str | None, bool, list[str]]:
    """Classe, lm_head separado e motivos de exclusão por formato."""
    untied = False
    fmts = [f for f in row["formatos"].split(";") if f]
    if "safetensors" not in fmts:
        return None, untied, [f"sem safetensors ({'+'.join(fmts) if fmts else 'nenhum arquivo de pesos'})"]
    if meta is None:
        raise KeyError(f"{row['repo']}: sem metadados; rode --fetch")
    if meta["erro"]:
        return None, untied, [f"metadados indisponíveis na revisão coletada ({meta['erro']})"]
    reasons = []
    if "mlx" in fmts:
        reasons.append("conversão MLX")
    if "exl2" in fmts:
        reasons.append("quantizado exl2")
    q = meta["quantization"]
    if q:
        reasons.append("quantizado (" + ", ".join(f"{k}={q[k]}" for k in ("quant_method", "bits") if k in q) + ")")
    cls, _ = weight_layout(meta["files"])
    if cls is None:
        st = sorted(f[0] for f in meta["files"] if f[0].endswith(".safetensors"))
        reasons.append(f"safetensors fora do layout de modelo ou adaptador na raiz ({', '.join(st)})")
    elif cls == "cheio":
        dtypes = set(meta["params"] or {})
        if not meta["params"]:
            reasons.append("sem contagem de parâmetros no HF")
        elif dtypes - META_FLOAT_DTYPES and not q:  # com quantization_config o motivo já está acima
            reasons.append(f"pesos inteiros ({'+'.join(sorted(dtypes - META_FLOAT_DTYPES))}): quantizado")
        if meta["architectures"] != parent["architectures"]:
            reasons.append(f"arquitetura {meta['architectures']} ≠ {parent['architectures']} do pai")
        total, ref = meta["params_total"], parent["params_total"]
        untied = total == ref + untied_extra(row["familia"])
        if total is not None and total != ref and not untied:
            reasons.append(f"parâmetros {total} ≠ {ref} do pai (nem {ref + untied_extra(row['familia'])}, com lm_head separado)")
    return cls, untied, reasons


DECLARED_OTHER = "raiz declarada"  # base declarada e diferente do pai: não é recuperável pela forma


def base_reasons(row: dict, parent_repo: str) -> list[str]:
    """Motivos de exclusão pela cadeia de bases declaradas (situacao_cadeia da T-1101)."""
    status = row["situacao_cadeia"]
    if status == "oficial":
        if row["raiz_oficial"].lower() != parent_repo.lower():
            return [f"{DECLARED_OTHER} {row['raiz_oficial']} não é o pai custodiado {parent_repo}"]
        return []
    if status.startswith("sem base declarada em "):
        at = status.removeprefix("sem base declarada em ")
        return ["sem base declarada" if at == row["repo"] else f"cadeia para em {at}, sem base declarada"]
    if status.startswith("ausente no HF: "):
        return [f"cadeia quebrada: {status.removeprefix('ausente no HF: ')} ausente no HF"]
    if status == "limite de saltos":
        return [f"cadeia com mais de {MAX_HOPS} saltos"]
    raise ValueError(f"{row['repo']}: situação da cadeia desconhecida {status!r}")


def weight_hashes(meta: dict | None, cls: str | None) -> tuple[str, ...]:
    if meta is None or meta.get("erro") or cls is None:
        return ()
    _, names = weight_layout(meta["files"])
    sha = {f[0]: f[2] for f in meta["files"]}
    if any(sha[n] is None for n in names):
        raise ValueError(f"arquivo de pesos sem SHA-256 publicado: {names}")
    return tuple(sha[n] for n in names)


def classify(rows: list[dict], meta: dict) -> list[dict]:
    """Uma linha de saída por candidato, na ordem da entrada."""
    out = []
    for r in rows:
        fam = r["familia"]
        parent_repo = PARENTS[fam]["repo"]
        parent = meta["pais"][fam]
        m = meta["candidatos"].get(r["repo"])
        cls, untied, f_reasons = format_reasons(r, m, parent)
        b_reasons = base_reasons(r, parent_repo)
        hashes = weight_hashes(m, cls)
        if hashes and set(hashes) <= set(weight_hashes(parent, "cheio")):
            f_reasons.append("pesos idênticos aos do pai")
        ok_meta = m is not None and not m.get("erro")
        out.append({
            "repo": r["repo"], "familia": fam, "pai": parent_repo,
            "motivos": f_reasons + b_reasons,
            "recuperavel_pela_forma": (bool(b_reasons) and not f_reasons and cls is not None
                                       and not any(b.startswith(DECLARED_OTHER) for b in b_reasons)),
            "classe": cls or "",
            "lm_head_separado": untied,
            "formatos": r["formatos"],
            "arquitetura": ";".join(m["architectures"] or []) if ok_meta else "",
            "parametros": m["params_total"] if ok_meta and m["params_total"] is not None else "",
            "dtypes": "+".join(m["params"] or {}) if ok_meta and m["params"] else "",
            "quantizacao": json.dumps(m["quantization"], sort_keys=True) if ok_meta and m["quantization"] else "",
            "raiz_oficial": r["raiz_oficial"], "situacao_cadeia": r["situacao_cadeia"],
            "pesos_sha256": ";".join(hashes), "_hashes": hashes,
            "revisao": r["revisao"], "criado": r["criado"], "gated": r["gated"],
        })
    # Cópias: mesmos arquivos de pesos que outro candidato (pesos_iguais_a, informativo para todos).
    # Entre os que passam ou são recuperáveis, fica um: primeiro os que passam, depois o criado
    # primeiro (empate: nome). Uma cópia que passaria sai; uma cópia recuperável deixa de ser.
    by_hash: dict[tuple, list[dict]] = {}
    for o in out:
        if o["_hashes"]:
            by_hash.setdefault(o["_hashes"], []).append(o)
    for group in by_hash.values():
        for o in group:
            o["pesos_iguais_a"] = ";".join(sorted(g["repo"] for g in group if g is not o))
        alive = sorted((o for o in group if not o["motivos"] or o["recuperavel_pela_forma"]),
                       key=lambda o: (bool(o["motivos"]), o["criado"], o["repo"].lower()))
        for o in alive[1:]:
            if o["motivos"]:
                o["recuperavel_pela_forma"] = False
            else:
                o["motivos"].append(f"mesmos pesos que {alive[0]['repo']}")
    for o in out:
        o.setdefault("pesos_iguais_a", "")
        o["decisao"] = EXCLUDED if o["motivos"] else ACCEPTED
        o["motivos"] = "; ".join(o["motivos"])
        del o["_hashes"]
    return out


REASON_KINDS = (  # prefixo do motivo -> rótulo na contagem
    ("sem safetensors (gguf", "sem safetensors: gguf"), ("sem safetensors (onnx", "sem safetensors: onnx"),
    ("sem safetensors (nenhum", "sem safetensors: nenhum arquivo de pesos"), ("sem safetensors", "sem safetensors: outro"),
    ("metadados indisponíveis", "metadados indisponíveis"), ("conversão MLX", "conversão MLX"),
    ("quantizado exl2", "quantizado exl2"), ("quantizado (", "quantizado (quantization_config)"),
    ("pesos inteiros", "pesos inteiros"), ("safetensors fora do layout", "safetensors fora do layout"),
    ("sem contagem de parâmetros", "sem contagem de parâmetros"), ("arquitetura", "arquitetura diferente"),
    ("parâmetros", "parâmetros diferentes"), ("pesos idênticos aos do pai", "pesos idênticos aos do pai"),
    ("mesmos pesos que", "cópia de outro candidato"), ("raiz declarada", "raiz no pré-treinado, não no pai"),
    ("sem base declarada", "sem base declarada"), ("cadeia para em", "cadeia para sem base declarada"),
    ("cadeia quebrada", "cadeia quebrada (repositório ausente no HF)"), ("cadeia com mais de", "cadeia longa demais"),
)


def reason_kind(reason: str) -> str:
    """Motivo sem os detalhes da linha, para a contagem."""
    for prefix, label in REASON_KINDS:
        if reason.startswith(prefix):
            return label
    raise ValueError(f"motivo sem rótulo: {reason!r}")


def summarize(out: list[dict], meta: dict) -> dict:
    fams = sorted({o["familia"] for o in out})
    summary = {"task": "T-1102", "entrada": CANDIDATES_CSV.name, "metadados": META_PATH.name,
               "coleta_metadados": meta["coleta"], "meta_e13": GOAL,
               "pais": {f: {"repo": meta["pais"][f]["repo"], "revisao": meta["pais"][f]["revision"],
                            "parametros": meta["pais"][f]["params_total"]} for f in fams},
               "por_familia": {}}
    for f in fams:
        rows = [o for o in out if o["familia"] == f]
        fmts = [set(o["formatos"].split(";")) for o in rows]
        acc = [o for o in rows if o["decisao"] == ACCEPTED]
        summary["por_familia"][f] = {
            "candidatos": len(rows),
            "com_safetensors": sum("safetensors" in s for s in fmts),
            "gguf_contexto": {"so_gguf": sum("gguf" in s and "safetensors" not in s for s in fmts),
                              "gguf_e_safetensors": sum("gguf" in s and "safetensors" in s for s in fmts)},
            "aceitos": len(acc),
            "aceitos_por_classe": dict(Counter(o["classe"] for o in acc)),
            "aceitos_com_lm_head_separado": sum(o["lm_head_separado"] for o in acc),
            "recuperaveis_pela_forma": sum(o["recuperavel_pela_forma"] for o in rows),
            "excluidos": len(rows) - len(acc),
            "motivos": dict(Counter(reason_kind(m) for o in rows for m in o["motivos"].split("; ") if m)
                            .most_common()),
            "motivo_principal": dict(Counter(reason_kind(o["motivos"].split("; ")[0]) for o in rows
                                             if o["motivos"]).most_common()),
            "aceitos_lista": [o["repo"] for o in acc],
            "recuperaveis_lista": [o["repo"] for o in rows if o["recuperavel_pela_forma"]],
        }
    total = sum(v["aceitos"] for v in summary["por_familia"].values())
    summary["aceitos_total"] = total
    summary["deficit_total_para_a_meta"] = max(0, GOAL - total)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fetch", action="store_true", help="busca os metadados no HF (rede, sem pesos)")
    args = ap.parse_args()
    if args.fetch:
        meta = fetch()
        META_PATH.write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
        print("->", META_PATH)
    meta = json.loads(META_PATH.read_text())
    with open(CANDIDATES_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = classify(rows, meta)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    summary = summarize(out, meta)
    OUT_SUMMARY.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    print("->", OUT_CSV)
    return 0


if __name__ == "__main__":
    sys.exit(main())
