"""Rótulo verdadeiro H/C/N de cada derivado, com o juiz de referência (T2, T3, T4, T5; T-1003, T-1004).

Para o pai e para cada derivado, na bateria de referência (experiments/reference, itens que o Juiz
nunca vê, R12):
1. gera as respostas aos nocivos do HarmBench (n por categoria) e aos seguros do XSTest (uso
   "referencia"), gulosa, na condição escolhida;
2. dá a nota com o avaliador: `referencia` é o juiz de referência (experiments/reference/judge.yaml,
   roda só na nuvem); `detector` é o detector de recusa, só para o perfil mini;
3. mede a perda de utilidade (entropia cruzada no corpus benigno, relativa ao pai) e a fração de
   respostas degeneradas;
4. aplica a regra do prereg (experiments.campaign.labels): sem_rotulo → N → C → H.

Retoma em dois níveis: cada modelo é um item do livro (<out>/livro.jsonl), e dentro dele cada pedido
respondido e avaliado vai para <out>/modelos/<nome>/notas.jsonl (sem texto) e respostas_texts.jsonl
(com texto, fora do git e fora do pacote, T-211). O pai é medido uma vez por avaliador e desenho e
reaproveitado ($MODEL_GATE_DATA/references/rotulo_<...>).

Saída: <out>/rotulos.json, uma linha por derivado: rótulo, motivos, dano por categoria (derivado e
pai), excesso, recusa excessiva, perda de utilidade, degeneradas e os metadados da população.

    uv run python -m experiments.testes.rotulo --out DIR --populacao pop.json --avaliador detector \
        --prereg experiments/testes/prereg_mini.yaml --n-por-categoria 2 --n-seguros 6
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

from experiments.data_dir import data_dir
from experiments.testes.comum import register, log, out_dir, resolve, resumable, write_json
from experiments.testes.veredito import model_path


def select_items(n_cat: int, n_safe: int, seed: int = 1003) -> tuple[list[dict], list[dict]]:
    """Os primeiros n por categoria (ordem sorteada pela seed) e n seguros, fixos para pai e derivados."""
    from experiments.reference.battery import load_battery
    bat = load_battery()
    rnd = random.Random(seed)
    harm: dict[str, list[dict]] = {}
    for it in bat["items"]:
        if it["kind"] == "nocivo":
            harm.setdefault(it["category"], []).append(it)
    chosen = []
    for cat in sorted(harm):
        group = sorted(harm[cat], key=lambda x: str(x["id"]))
        rnd.shuffle(group)
        chosen += group[:n_cat]
    safe = sorted((it for it in bat["items"] if it["kind"] == "seguro"), key=lambda x: str(x["id"]))
    rnd.shuffle(safe)
    return chosen, safe[:n_safe]


def utility_corpus(n: int, seed: int = 1003) -> list[dict]:
    """n pares do Alpaca convertido (T-902), do fim do arquivo para não cruzar com o treino F1."""
    path = data_dir() / "datasets" / "benign" / "alpaca.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    tail = [json.loads(x) for x in lines[-2000:] if x.strip()]
    random.Random(seed).shuffle(tail)
    return tail[:n]


class Grader:
    """Interface comum: score(prompt, response) -> (harm, refused); classify(prompt, response) -> rótulo XSTest."""

    def __init__(self, kind: str, threads: int):
        self.kind = kind
        if kind == "detector":
            from model_gate.evaluators import make_evaluator
            ev = make_evaluator("detector")
            self._score, self._classify = ev.harm.score, ev.xstest.classify
            self._score_many = lambda pairs: [self._score(p, r) for p, r in pairs]
            self._classify_many = lambda pairs: [self._classify(p, r) for p, r in pairs]
            self.id = "detector:refusal-prefix"
        elif kind == "referencia":
            self._load_reference(threads)
        else:
            raise SystemExit(f"avaliador desconhecido {kind}")

    def _load_reference(self, threads: int) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        from experiments.reference.judge import ReferenceConfig, ReferenceJudge
        from experiments.testes.juiz_referencia import local_dir, templates, verify
        cfg = ReferenceConfig.load()
        root = local_dir(cfg)
        verify(cfg, root)
        tok = AutoTokenizer.from_pretrained(root)
        from model_gate.io.device import device
        model = AutoModelForCausalLM.from_pretrained(root, torch_dtype=torch.bfloat16).to(device())
        rub, xs = templates()
        j = ReferenceJudge(model, tok, rub, xs, cfg)
        self._score, self._classify = j.score, j.classify
        self._score_many, self._classify_many = j.score_many, j.classify_many
        self.id = f"referencia:{cfg.repo_id}@{cfg.revision}"

    def score(self, prompt: str, response: str):
        s = self._score(prompt, response)
        return s.harm, s.refused

    def classify(self, prompt: str, response: str):
        return self._classify(prompt, response).cls

    def score_many(self, pairs: list[tuple[str, str]]) -> list[tuple]:
        return [(s.harm, s.refused) for s in self._score_many(pairs)]

    def classify_many(self, pairs: list[tuple[str, str]]) -> list:
        return [x.cls for x in self._classify_many(pairs)]


def measure(name: str, path: Path, harmful: list[dict], safe: list[dict], texts: dict, grader: Grader, a,
            work: Path) -> dict:
    """Responde, avalia e mede um modelo; retoma pedido a pedido pelos arquivos em `work`."""
    from experiments.fetch_base import MANIFEST, local_root
    from model_gate.battery.refusal import is_refusal
    from model_gate.io.generate import GenConfig, generate
    from model_gate.io.load import dir_digest, load_model
    from model_gate.stages import is_degenerate, response_ce

    work.mkdir(parents=True, exist_ok=True)
    notes_f, texts_f = work / "notas.jsonl", work / "respostas_texts.jsonl"

    def read_jsonl(f: Path) -> dict:
        got = {}
        if f.exists():
            for line in f.read_text().splitlines():
                try:
                    r = json.loads(line)
                    got[(r["papel"], str(r["id"]))] = r
                except ValueError:  # última linha cortada por uma queda
                    pass
        return got

    done, answered = read_jsonl(notes_f), read_jsonl(texts_f)
    base_digest = json.loads(MANIFEST.read_text())["digest"]
    base = local_root()
    digest = dir_digest(path)[0]
    m = load_model(path, digest, base_path=base, base_digest=base_digest)
    system = None if a.condicao == "padrao" else ""
    lote = max(1, a.lote)
    cfg = GenConfig(max_new_tokens=a.max_new_tokens, system_prompt=system, threads=a.threads, batch_size=lote)
    todo = [("nocivo", it) for it in harmful] + [("seguro", it) for it in safe]
    to_answer = [(role, it) for role, it in todo if (role, str(it["id"])) not in answered]
    log(f"{name}: {len(done)} pedidos avaliados, {len(answered)} respondidos, {len(to_answer)} a responder (lote {lote})")
    # 1) respostas do modelo, em lotes (cada lote gravado antes do próximo)
    with open(texts_f, "a") as tf:
        for i in range(0, len(to_answer), lote):
            chunk = to_answer[i:i + lote]
            t0 = time.perf_counter()
            outs = generate(m.model, m.tokenizer, [texts[(it["source"], it["id"])] for _, it in chunk], cfg)
            dt = (time.perf_counter() - t0) / len(chunk)
            for (role, it), out in zip(chunk, outs):
                r = {"papel": role, "id": it["id"], "texto": out["text"], "n_tokens": out["n_tokens"],
                     "s_geracao": round(dt, 2)}
                tf.write(json.dumps(r, ensure_ascii=False) + "\n")
                answered[(role, str(it["id"]))] = r
            tf.flush(); os.fsync(tf.fileno())
    # 2) notas do avaliador, em lotes do mesmo tamanho
    to_grade = [(role, it) for role, it in todo if (role, str(it["id"])) not in done]
    with open(notes_f, "a") as nf:
        for role_kind in ("nocivo", "seguro"):
            group = [(role, it) for role, it in to_grade if role == role_kind]
            for i in range(0, len(group), lote):
                chunk = group[i:i + lote]
                pairs = [(texts[(it["source"], it["id"])], answered[(role, str(it["id"]))]["texto"]) for role, it in chunk]
                t1 = time.perf_counter()
                graded = grader.score_many(pairs) if role_kind == "nocivo" else grader.classify_many(pairs)
                ds = (time.perf_counter() - t1) / len(chunk)
                for (role, it), (_, text), g in zip(chunk, pairs, graded):
                    ans = answered[(role, str(it["id"]))]
                    row = {"papel": role, "id": it["id"], "categoria": it["category"], "n_tokens": ans.get("n_tokens"),
                           "recusa_prefixo": is_refusal(text), "degenerada": is_degenerate(text)}
                    if role == "nocivo":
                        harm, refused = g
                        row |= {"dano": None if harm is None or (isinstance(harm, float) and math.isnan(harm)) else harm,
                                "recusou": refused}
                    else:
                        row["xstest"] = g
                    row |= {"s_geracao": ans.get("s_geracao", 0.0), "s_avaliacao": round(ds, 2)}
                    nf.write(json.dumps(row, ensure_ascii=False) + "\n")
                    done[(role, str(it["id"]))] = row
                nf.flush(); os.fsync(nf.fileno())
    rows = list(done.values())
    ce_f = work / "utilidade.json"
    if ce_f.exists():
        ce = json.loads(ce_f.read_text())["ce"]
    else:
        ce = response_ce(m.model, m.tokenizer, utility_corpus(a.n_utilidade), threads=a.threads)
        write_json(ce_f, {"ce": ce, "n": a.n_utilidade})
    harm_by_cat: dict[str, list[float]] = {}
    for r in rows:
        if r["papel"] == "nocivo":
            harm_by_cat.setdefault(r["categoria"], []).append(r["dano"])
    tau = a.tau
    harm = {c: (None if any(v is None for v in vs) else sum(v >= tau for v in vs) / len(vs)) for c, vs in harm_by_cat.items()}
    safe_rows = [r for r in rows if r["papel"] == "seguro"]
    over = (sum(r["xstest"] == "recusa_total" for r in safe_rows) / len(safe_rows)) if safe_rows else None
    return {"digest": digest, "dano": harm, "recusa_excessiva": over, "ce": ce,
            "degeneradas": sum(r["degenerada"] for r in rows) / len(rows), "n": len(rows),
            "s_geracao": round(sum(r["s_geracao"] for r in rows), 1), "s_avaliacao": round(sum(r["s_avaliacao"] for r in rows), 1)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out")
    ap.add_argument("--populacao", type=Path, action="append", required=True)
    ap.add_argument("--avaliador", choices=("detector", "referencia"), default="detector")
    ap.add_argument("--prereg", type=Path, required=True, help="de onde saem τ e a regra do rótulo")
    ap.add_argument("--n-por-categoria", type=int, default=17)
    ap.add_argument("--n-seguros", type=int, default=100)
    ap.add_argument("--n-utilidade", type=int, default=32)
    ap.add_argument("--max-new-tokens", type=int, default=512)
    ap.add_argument("--condicao", choices=("vazio", "padrao"), default="padrao")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--lote", type=int, default=1,
                    help="pedidos por lote na geração e na avaliação (1 na CPU; maior na GPU). Entra no desenho.")
    a = ap.parse_args(argv)
    register("experiments.testes.rotulo", argv)
    out = out_dir(a.out)
    import yaml

    from experiments.campaign.labels import LabelRule, label
    from experiments.reference.battery import load_battery, texts as battery_texts
    a.prereg = a.prereg.resolve()
    lim = yaml.safe_load(a.prereg.read_text())["limiares"]
    a.tau = float(lim["tau"])
    rule = LabelRule.from_prereg(a.prereg)
    pop = []
    for f in a.populacao:
        pop += [r for r in json.loads(f.read_text()) if r.get("caminho")]
    harmful, safe = select_items(a.n_por_categoria, a.n_seguros)
    texts = battery_texts(load_battery())
    if a.avaliador == "referencia":
        # o juiz de referência (~42 GB em bf16) carrega uma vez só: aqui o paralelo é o lote, não processos
        os.environ["MG_PARALELO"] = os.environ.get("MG_PARALELO_ROTULO", "1")
    grader = Grader(a.avaliador, a.threads)
    design = {"n_por_categoria": a.n_por_categoria, "n_seguros": a.n_seguros, "n_utilidade": a.n_utilidade,
              "max_new_tokens": a.max_new_tokens, "condicao": a.condicao, "tau": a.tau, "avaliador": grader.id,
              **({"lote": a.lote} if a.lote != 1 else {})}
    write_json(out / "contexto.json", {**design, "prereg": str(a.prereg), "regra": rule.__dict__,
                                       "itens": [[it["source"], it["id"]] for it in harmful + safe]})
    tag = hashlib.sha256(json.dumps(design, sort_keys=True).encode()).hexdigest()[:10]
    from model_gate.io.device import name as device_name
    dev = "" if device_name() == "cpu" else f"_{device_name()}"
    parent_dir = data_dir() / "references" / f"rotulo_{a.avaliador}_{tag}{dev}"
    parent_file = parent_dir / "pai.json"
    if parent_file.exists():
        parent = json.loads(parent_file.read_text())
        log(f"pai reaproveitado: {parent_dir}")
    else:
        log(f"medindo o pai para o rótulo em {parent_dir}")
        from experiments.fetch_base import local_root
        parent = measure("pai", local_root(), harmful, safe, texts, grader, a, parent_dir)
        write_json(parent_file, parent)

    def work(it: dict) -> dict:
        d = measure(it["nome"], model_path(it["caminho"]), harmful, safe, texts, grader, a, out / "modelos" / it["nome"])
        loss = d["ce"] / parent["ce"] - 1.0
        lab = label(rule, harm_derivative=d["dano"], harm_parent=parent["dano"], utility_loss=loss,
                    degenerate_rate=d["degeneradas"], overrefusal_derivative=d["recusa_excessiva"],
                    overrefusal_parent=parent["recusa_excessiva"])
        return {"rotulo": lab.label, "motivos": list(lab.reasons), "excesso": lab.excess_by_category,
                "recusa_excessiva": lab.overrefusal, "perda_utilidade": round(loss, 5), "medidas": d}

    rows = resumable(pop, work, out, what="rótulo")
    write_json(out / "rotulos.json", rows)
    write_json(out / "pai.json", parent)
    count = {}
    for r in rows:
        count[r["rotulo"]] = count.get(r["rotulo"], 0) + 1
    missing = [p["nome"] for p in pop if p["nome"] not in {r["nome"] for r in rows}]
    log(f"rótulos: {count}" + (f"; faltam {missing}" if missing else ""))
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
