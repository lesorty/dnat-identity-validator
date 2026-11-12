"""Lista de candidatos de campo para o teste cego (T-1101; E13 §3.5, RQ3, R13).

Só metadados do Hugging Face (list_models e model_info): nenhum peso é baixado (isso é a T-1103),
e a filtragem por formato e base é a T-1102.

Fontes:
- Registro de 57 abliterações de Hurtado (notas 06, §1.3): o artigo não publica a lista. O
  manifesto por checkpoint (repositório, revisão, família, receita) é "available on request"
  (App. D) e as famílias são Qwen, Qwen destilado do DeepSeek, Llama e Gemma, sem nomes. Daqui
  sai zero candidato até o pedido ao autor.
- Buscas no HF por termo (TERMS, substring do id) e, para pegar ids sem o nome da família, por
  termo + etiqueta base_model:<oficial>. Fica quem é das duas famílias: o id ou a base declarada
  bate com FAMILIES (Qwen2.5-0.5B, o pai custodiado; Llama-3.2-1B, a família não vista, T-1602).
  Qwen2.5-Coder-0.5B e Qwen2.5-Math não são o mesmo modelo e não batem.
- Os três exemplos da E13 §3.5, conferidos pelo nome.

Para cada candidato: repositório, autor, família, termos que o acharam, base declarada (cartão
ou etiqueta), a cadeia de bases declaradas até um repositório oficial (no máximo MAX_HOPS
saltos), a relação (finetune, quantized, merge, adapter), formatos dos arquivos, revisão (sha)
e datas, e a data da coleta.

    uv run python -m experiments.field_candidates   # grava data/field_candidates.csv e o resumo
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

from huggingface_hub import HfApi

DATA = Path(__file__).resolve().parents[1] / "data"
OUT_CSV = DATA / "field_candidates.csv"
OUT_SUMMARY = DATA / "field_candidates.summary.json"
TERMS = ("abliterat", "uncensored")  # "abliterat" cobre abliterated, abliterate e abliteration
FAMILIES = {
    "qwen2.5-0.5b": {"pattern": re.compile(r"qwen2\.?5[-_. ]?0\.?5b(?![a-z0-9])", re.I),
                     "official": ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-0.5B")},
    "llama-3.2-1b": {"pattern": re.compile(r"llama[-_. ]?3\.?2[-_. ]?1b(?![a-z0-9])", re.I),
                     "official": ("meta-llama/Llama-3.2-1B-Instruct", "meta-llama/Llama-3.2-1B")},
}
E13_EXAMPLES = ("huihui-ai/Qwen2.5-0.5B-Instruct-abliterated-v3",
                "3MPER0RR/Qwen2.5-0.5B-Instruct-3MPER0RR-abliterated",
                "sbussiso/Llama-3.2-1B-Instruct-abliterated")
MAX_HOPS = 5
RELATIONS = ("finetune", "quantized", "merge", "adapter")
COLUMNS = ("repo", "autor", "familia", "origem", "termos", "base_declarada", "relacao", "cadeia_declarada",
           "raiz_declarada", "raiz_oficial", "situacao_cadeia", "formatos", "arquivos_pesos", "revisao", "criado", "modificado",
           "gated", "coleta")


def family_of(text: str) -> str | None:
    hits = [f for f, spec in FAMILIES.items() if spec["pattern"].search(text)]
    if len(hits) > 1:
        raise ValueError(f"{text}: casa com mais de uma família {hits}")
    return hits[0] if hits else None


def declared_bases(tags: list[str], card: dict | None) -> list[str]:
    """Bases declaradas: o base_model do cartão e as etiquetas base_model:<repo>."""
    out = []
    b = (card or {}).get("base_model")
    out += [b] if isinstance(b, str) else list(b or [])
    out += [t.split(":", 1)[1] for t in tags if t.startswith("base_model:") and t.count(":") == 1]
    return list(dict.fromkeys(x.strip() for x in out if x and x.strip()))


def relations(tags: list[str]) -> list[str]:
    return sorted({t.split(":")[1] for t in tags if t.startswith("base_model:") and t.count(":") == 2
                   and t.split(":")[1] in RELATIONS})


def formats(files: list[str], tags: list[str]) -> tuple[list[str], int]:
    """Formatos pelo nome dos arquivos (e mlx pela etiqueta) e quantos arquivos de pesos há."""
    kinds = {"safetensors": r"\.safetensors$", "gguf": r"\.gguf$", "pytorch_bin": r"pytorch_model.*\.bin$",
             "onnx": r"\.onnx(_data)?$", "lora": r"adapter_config\.json$", "exl2": r"\.exl2|measurement\.json$"}
    got = sorted({k for k, rx in kinds.items() if any(re.search(rx, f) for f in files)}
                 | ({"mlx"} if "mlx" in tags else set()))
    n = sum(bool(re.search(r"\.(safetensors|gguf|bin|onnx|pt|pth)$", f)) for f in files)
    return got, n


class Hub:
    """model_info com cache (cada repositório é consultado uma vez por execução)."""

    def __init__(self, api: HfApi):
        self.api, self.cache = api, {}

    def info(self, repo: str):
        if repo not in self.cache:
            self.cache[repo] = self.api.model_info(repo)
            time.sleep(0.05)
        return self.cache[repo]

    def exists(self, repo: str) -> bool:
        from huggingface_hub.errors import RepositoryNotFoundError

        try:
            self.info(repo)
            return True
        except RepositoryNotFoundError:
            return False

    def chain(self, repo: str) -> tuple[list[str], str | None, str]:
        """Primeira base declarada, salto a salto, até um repositório oficial.

        Devolve a cadeia, a raiz oficial (grafia canônica; o HF não diferencia maiúsculas) e a
        situação: "oficial", "sem base declarada em <repo>", "ausente no HF: <repo>" (apagado ou
        privado) ou "limite de saltos".
        """
        officials = {o.lower(): o for spec in FAMILIES.values() for o in spec["official"]}
        path, cur = [], repo
        for _ in range(MAX_HOPS):
            i = self.info(cur)
            bases = declared_bases(i.tags or [], i.card_data.to_dict() if i.card_data else None)
            if not bases:
                return path, None, f"sem base declarada em {cur}"
            hit = [b for b in bases if b.lower() in officials]
            nxt = hit[0] if hit else bases[0]
            path.append(nxt)
            if nxt.lower() in officials:
                return path, officials[nxt.lower()], "oficial"
            if not self.exists(nxt):
                return path, None, f"ausente no HF: {nxt}"
            cur = nxt
        return path, None, "limite de saltos"


def search(api: HfApi) -> dict[str, set[str]]:
    """repo -> origens. Busca por termo e por termo + etiqueta base_model do oficial."""
    found: dict[str, set[str]] = {}
    for term in TERMS:
        for m in api.list_models(search=term, expand=["tags"]):
            tags = m.tags or []
            if family_of(m.id) or any(family_of(b) for b in declared_bases(tags, None)):
                found.setdefault(m.id, set()).add(f"busca:{term}")
        for spec in FAMILIES.values():
            for off in spec["official"]:
                for m in api.list_models(search=term, filter=f"base_model:{off}"):
                    found.setdefault(m.id, set()).add(f"busca:{term}+base_model:{off}")
    for repo in E13_EXAMPLES:
        found.setdefault(repo, set()).add("E13 §3.5")
    return found


def row(hub: Hub, repo: str, origins: set[str], collected: str) -> dict:
    i = hub.info(repo)
    tags = i.tags or []
    card = i.card_data.to_dict() if i.card_data else None
    bases = declared_bases(tags, card)
    path, root, status = hub.chain(repo)
    fam = family_of(root) if root else family_of(repo) or next((family_of(b) for b in bases if family_of(b)), None)
    files = [s.rfilename for s in (i.siblings or [])]
    fmts, n_weights = formats(files, tags)
    terms = sorted({t for t in TERMS if t in repo.lower()} | {o.split(":")[1].split("+")[0] for o in origins
                                                                if o.startswith("busca:")})
    return {"repo": repo, "autor": i.author or repo.split("/")[0], "familia": fam or "",
            "origem": ";".join(sorted(origins)), "termos": ";".join(terms), "base_declarada": ";".join(bases),
            "relacao": ";".join(relations(tags)), "cadeia_declarada": " > ".join(path),
            "raiz_declarada": path[-1] if path else "", "raiz_oficial": root or "", "situacao_cadeia": status,
            "formatos": ";".join(fmts), "arquivos_pesos": n_weights, "revisao": i.sha,
            "criado": i.created_at.date().isoformat() if i.created_at else "",
            "modificado": i.last_modified.date().isoformat() if i.last_modified else "",
            "gated": str(i.gated), "coleta": collected}


def main() -> int:
    api = HfApi()
    hub = Hub(api)
    collected = time.strftime("%Y-%m-%d", time.gmtime())
    found = search(api)
    missing = [r for r in E13_EXAMPLES if not hub.exists(r)]
    if missing:
        raise RuntimeError(f"exemplos da E13 §3.5 não existem mais no HF: {missing}")
    rows = sorted((row(hub, repo, origins, collected) for repo, origins in found.items()),
                  key=lambda r: (r["familia"], r["repo"].lower()))
    rows = [r for r in rows if r["familia"]]  # achados pela etiqueta mas sem família (não deve ocorrer)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    summary = {
        "task": "T-1101", "coleta": collected, "api": "huggingface_hub HfApi.list_models/model_info",
        "termos": list(TERMS), "familias": {k: list(v["official"]) for k, v in FAMILIES.items()},
        "hurtado": "registro de 57 não publicado (App. D: manifesto 'available on request'); 0 candidatos daqui",
        "total": len(rows), "descartados_sem_familia": len(found) - len(rows),
        "por_familia": dict(Counter(r["familia"] for r in rows)),
        "por_familia_e_formato": {f: dict(Counter(("safetensors" if "safetensors" in r["formatos"].split(";") else
                                                   "gguf" if "gguf" in r["formatos"].split(";") else
                                                   r["formatos"] or "nenhum") for r in rows if r["familia"] == f))
                                  for f in FAMILIES},
        "raiz_oficial": dict(Counter(r["raiz_oficial"] or "sem raiz oficial" for r in rows)),
        "situacao_cadeia": dict(Counter(r["situacao_cadeia"].split(":")[0].split(" em ")[0] for r in rows)),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    print("->", OUT_CSV)
    return 0


if __name__ == "__main__":
    sys.exit(main())
