"""Julga uma lista de derivados com o Juiz real, retomando depois de uma queda (T1, T2, T3, T5, T6, T7).

Generaliza o experiments.judge_local (T-807): mede o pai uma vez (cache em
$MODEL_GATE_DATA/references/testes_<avaliador>_<bateria>_<desenho>, reaproveitado entre testes) e
roda o job do Juiz (model_gate.job.run_job) para cada derivado, um por vez, com o livro em
<out>/livro.jsonl. Cada derivado deixa em <out>/jobs/<nome>/ o manifesto, o verdict.json, o
job_result.json e, se algo quebrar, o traceback inteiro (o job só guarda 500 caracteres do erro).

Saída: <out>/vereditos.json (uma linha por derivado: estado, regra, motivos, dano nas âncoras, sinais,
utilidade, tempo, e os metadados que vieram na lista) e <out>/resumo.json.

    uv run python -m experiments.testes.veredito --out DIR --prereg P --bateria DIR --avaliador detector \
        --derivado base=base --derivado huihui=field:huihui-ai/Qwen2.5-0.5B-Instruct-abliterated-v3
    uv run python -m experiments.testes.veredito --out DIR ... --lista derivados.json
        (lista: [{"nome", "caminho", ...metadados}], ou o vereditos.json/populacao.json de outro passo)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

from experiments.data_dir import data_dir
from experiments.testes.comum import register, field_dir, log, make_eval, out_dir, resolve, resumable, write_json

DECIDED_AT = "2026-11-24T00:00:00Z"


class LoggedStages:
    """Repassa para os estágios reais e grava o traceback inteiro de qualquer erro antes de propagá-lo."""

    def __init__(self, inner, errfile: Path):
        self._inner, self._err = inner, errfile

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if not callable(attr) or name.startswith("_"):
            return attr

        def call(*a, **kw):
            try:
                return attr(*a, **kw)
            except BaseException:
                self._err.parent.mkdir(parents=True, exist_ok=True)
                with open(self._err, "a") as fh:
                    fh.write(f"\n===== estágio {name} · {time.strftime('%Y-%m-%dT%H:%M:%S')}\n{traceback.format_exc()}")
                raise
        return call


def model_path(spec: str) -> Path:
    if spec.startswith("field:"):
        return field_dir(spec[len("field:"):])
    return resolve(spec)


def parent_reference(base: Path, base_digest: str, battery, battery_dir: Path, prereg: Path, ev_kind: str, evaluator,
                     settings, threads: int) -> tuple[Path, float]:
    from model_gate.io.digest import file_sha256
    from model_gate.reference import FILE as REF_FILE
    from model_gate.reference import measure_parent
    from model_gate.stages import battery_sha256
    import hashlib
    design = hashlib.sha256(json.dumps(settings.record(), sort_keys=True).encode()).hexdigest()[:8]
    from model_gate.io.device import name as device_name
    dev = "" if device_name() == "cpu" else f"_{device_name()}"   # o pai medido na GPU não serve para a CPU
    tag = f"testes_{ev_kind}_{battery_sha256(battery)[:8]}_{design}_{base_digest[:8]}{dev}"
    ref_dir = data_dir() / "references" / tag
    if (ref_dir / REF_FILE).exists():
        log(f"referência do pai reaproveitada: {ref_dir}")
        return ref_dir, 0.0
    log(f"medindo o pai em {ref_dir} (prereg {prereg.name}, sha {file_sha256(prereg)[:8]})")
    t0 = time.perf_counter()
    tmp = ref_dir.with_name(ref_dir.name + ".parcial")
    if tmp.exists():
        import shutil
        shutil.rmtree(tmp)
    measure_parent(base, base_digest, battery, evaluator, settings, tmp, threads=threads)
    tmp.rename(ref_dir)  # só vira referência quando terminou: uma queda no meio não deixa pacote pela metade
    return ref_dir, time.perf_counter() - t0


def summarize(doc: dict) -> dict:
    harm = {}
    for c in doc["measures"]["s1"]:
        if c.get("category") == "todas":
            key = f"{c['block']}/{c['format']}/{c['condition']}"
            harm[key] = {"derivado": c["derivative"].get("harm_rate"), "pai": c["parent"].get("harm_rate"),
                         "n": c["derivative"].get("n")}
    return {"estado": doc["state"], "regra": doc["rule"], "motivos": sorted({r["code"] for r in doc["reasons"]}),
            "dano": harm, "sinais": doc["measures"].get("signals"), "utilidade": doc["measures"].get("utility")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out")
    ap.add_argument("--prereg", type=Path, required=True)
    ap.add_argument("--bateria", type=Path, required=True)
    ap.add_argument("--avaliador", default="detector", choices=("detector", "qwen3guard", "gemma"))
    ap.add_argument("--derivado", action="append", default=[], help="nome=caminho (base, field:<repo>, ou caminho)")
    ap.add_argument("--lista", type=Path, action="append", default=[], help="JSON com [{nome, caminho, ...}]")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)
    register("experiments.testes.veredito", argv)
    a.prereg, a.bateria = a.prereg.resolve(), a.bateria.resolve()
    out = out_dir(a.out)

    from experiments.fetch_base import MANIFEST, local_root
    from model_gate.io.digest import file_sha256
    from model_gate.io.load import dir_digest
    from model_gate.job import SCHEMA_ID, VERDICT_FILE, Manifest, run_job
    from model_gate.judge_package import judge_hash
    from model_gate.stages import RealStages, battery_sha256, load_battery, load_prereg
    from model_gate.verdict.emit import read

    items = []
    for spec in a.derivado:
        name, _, path = spec.partition("=")
        items.append({"nome": name, "caminho": path})
    for f in a.lista:
        items += [r for r in json.loads(f.read_text()) if r.get("caminho")]
    if not items:
        raise SystemExit("nenhum derivado (--derivado ou --lista)")
    if len({i["nome"] for i in items}) != len(items):
        raise SystemExit("nome de derivado repetido")

    base = local_root()
    base_digest = json.loads(MANIFEST.read_text())["digest"]
    battery = load_battery(a.bateria)
    _, _, settings = load_prereg(a.prereg)
    ev_kind, ev_spec, evaluator = make_eval(a.avaliador, battery, a.threads)
    ref_dir, ref_secs = parent_reference(base, base_digest, battery, a.bateria, a.prereg, a.avaliador, evaluator,
                                         settings, a.threads)
    jh = judge_hash()[0]
    meta = {"prereg": str(a.prereg), "prereg_sha256": file_sha256(a.prereg), "bateria": str(a.bateria),
            "bateria_sha256": battery_sha256(battery), "avaliador": a.avaliador, "juiz": jh, "base_digest": base_digest,
            "referencia": str(ref_dir), "referencia_segundos": round(ref_secs, 1), "desenho": settings.record()}
    write_json(out / "contexto.json", meta)
    dataset = out / "dataset.csv"
    if not dataset.exists():
        dataset.write_text("prompt,response\nWhat is 2 + 2?,4\nName a color.,Blue\n")
    digests = {"base": base_digest, "ref": dir_digest(ref_dir)[0], "bat": dir_digest(a.bateria)[0],
               "data": file_sha256(dataset), "prereg": file_sha256(a.prereg)}

    def work(it: dict) -> dict:
        der = model_path(it["caminho"])
        job = out / "jobs" / it["nome"]
        job.mkdir(parents=True, exist_ok=True)
        inputs = {
            "base": {"path": str(base), "kind": "dir", "digest": digests["base"]},
            "derivative": {"path": str(der), "kind": "dir", "digest": dir_digest(der)[0]},
            "parent_reference": {"path": str(ref_dir), "kind": "dir", "digest": digests["ref"]},
            "battery": {"path": str(a.bateria), "kind": "dir", "digest": digests["bat"]},
            "dataset": {"path": str(dataset), "kind": "file", "digest": digests["data"]},
            "prereg": {"path": str(a.prereg), "kind": "file", "digest": digests["prereg"]},
        }
        if ev_spec:
            inputs["evaluator"] = ev_spec
        mpath = job / "manifesto.json"
        mpath.write_text(json.dumps({"schema": SCHEMA_ID, "inputs": inputs, "judge_hash": jh,
                                     "battery_commitment": "0" * 64, "identity_id": "0" * 64, "decided_at": DECIDED_AT,
                                     "evaluator": {"kind": ev_kind}, "sampling_key": "5a" * 16}, indent=1))
        stages = RealStages(threads=a.threads)
        stages._cache["evaluator"] = evaluator  # o mesmo avaliador já carregado
        t = time.perf_counter()
        res = run_job(Manifest.load(mpath), job / "saida", LoggedStages(stages, job / "traceback.txt"))
        secs = round(time.perf_counter() - t, 1)
        row = {"derivado_digest": inputs["derivative"]["digest"], "status": res["status"], "segundos": secs}
        if res["status"] == "verdict" and (job / "saida" / VERDICT_FILE).exists():
            doc, _ = read(job / "saida" / VERDICT_FILE)
            row |= summarize(doc)
            if res.get("alert"):
                row |= {"alerta": res["alert"], "problemas": res.get("problems")}
        else:
            row |= {"estado": "falha", "erro": res.get("error") or res.get("alert")}
        log(f"{it['nome']}: {row['estado']} (regra {row.get('regra', '-')}, {', '.join(row.get('motivos', [])) or row.get('erro') or ''}) em {secs} s")
        return row

    rows = resumable(items, work, out, what="veredito")
    write_json(out / "vereditos.json", rows)
    states = {}
    for r in rows:
        states[r["estado"]] = states.get(r["estado"], 0) + 1
    falt = [i["nome"] for i in items if i["nome"] not in {r["nome"] for r in rows}]
    write_json(out / "resumo.json", {**meta, "n": len(items), "feitos": len(rows), "faltam": falt, "estados": states,
                                     "minutos_por_veredito": round(sum(r["segundos"] for r in rows) / 60 / max(1, len(rows)), 2)})
    log(f"{len(rows)}/{len(items)} vereditos: {states}" + (f"; faltam {falt}" if falt else ""))
    return 0 if not falt else 1


if __name__ == "__main__":
    sys.exit(main())
