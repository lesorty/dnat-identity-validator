"""O Juiz como job (T-807; E14 §3, §4, §9): entradas conferidas por hash, escada, verdict.json.

É o ponto de entrada que a CVM de uso único roda (T-801): a CVM1 entrega um manifesto com as
entradas e os hashes esperados; o job confere tudo antes de abrir qualquer peso, roda os estágios,
aplica a escada (verdict/combine.py) e escreve só o verdict.json (verdict/emit.py) e as respostas
(responses.jsonl, que o agente cifra antes de devolver, T-103).

    python -m model_gate.job --manifest job.json --out SAÍDA

Manifesto dnat.judge-job.v1:
    {"schema": "dnat.judge-job.v1",
     "inputs": {nome: {"path", "digest", "kind": "dir" | "file"}},   # base, derivative,
              # parent_reference, dataset e prereg são obrigatórios
     "judge_hash", "battery_commitment", "identity_id": SHA-256 em 64 hex,
     "decided_at": ISO 8601 em UTC (o instante fixo T0 + T_max, E14 §4; quem fixa é a CVM1)}

Digest: diretório pela regra de io.digest (modelos e pacotes), arquivo pelo SHA-256 dos bytes.

Desfechos (E14 §4, §9):
    Juiz em execução com hash     → sem verdict.json; status "failure" com alerta judge_hash_mismatch:
      diferente do manifesto        não é o Juiz auditado, então não julga nada (T-808)
    hash que não confere         → verdict.json reprovado, regra 0, sem medidas (alerta ao operador)
    estágio que falha            → sem verdict.json; status "failure" (inconclusivo por falha, T-107;
                                   a CVM1 roda de novo e devolve a reserva da cota, T-1704)
    caso contrário               → verdict.json da escada

Estágios: o que já existe no Juiz entra aqui de verdade (conferência de forma e tokenizer contra o
base, sobreposição do dataset com a bateria). O resto (S1 com o avaliador, S2/S3, utilidade,
injeção) chega por `Stages`, porque depende da referência custodiada do pai (T-312) e da
utilidade (T-910), que ainda não existem; a classe padrão levanta StageNotReady para esses, e o job
termina como falha, nunca com um veredito inventado.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from model_gate.battery.pool import load_pool, prompt_hash
from model_gate.io.digest import file_sha256
from model_gate.io.load import dir_digest
from model_gate.judge_package import judge_hash as running_judge_hash
from model_gate.verdict import emit
from model_gate.verdict.combine import (REJECTED, Integrity, Prereg, Reason, SignalReading, Utility, Verdict,
                                        decide)

SCHEMA_ID = "dnat.judge-job.v1"
REQUIRED_INPUTS = ("base", "derivative", "parent_reference", "dataset", "prereg")
VERDICT_FILE = "verdict.json"
RESPONSES_FILE = "responses.jsonl"
RESULT_FILE = "job_result.json"


class StageNotReady(RuntimeError):
    """O estágio ainda não tem implementação no Juiz (depende de outra task)."""


@dataclass(frozen=True)
class Manifest:
    inputs: dict[str, dict]
    judge_hash: str
    battery_commitment: str
    identity_id: str
    decided_at: str

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        raw = json.loads(Path(path).read_text())
        if raw.get("schema") != SCHEMA_ID:
            raise ValueError(f"manifesto: schema {raw.get('schema')!r}, esperava {SCHEMA_ID}")
        inputs = raw.get("inputs") or {}
        missing = [n for n in REQUIRED_INPUTS if n not in inputs]
        if missing:
            raise ValueError(f"manifesto sem as entradas {missing}")
        base = Path(path).parent
        out = {}
        for name, spec in inputs.items():
            if spec.get("kind") not in ("dir", "file") or not spec.get("digest") or not spec.get("path"):
                raise ValueError(f"entrada {name}: precisa de path, digest e kind dir|file")
            p = Path(spec["path"])
            out[name] = {**spec, "path": str(p if p.is_absolute() else base / p)}
        return cls(out, raw["judge_hash"], raw["battery_commitment"], raw["identity_id"], raw["decided_at"])


def input_digest(spec: Mapping) -> str:
    p = Path(spec["path"])
    if spec["kind"] == "dir":
        if not p.is_dir():
            raise FileNotFoundError(p)
        return dir_digest(p)[0]
    if not p.is_file():
        raise FileNotFoundError(p)
    return file_sha256(p)


def verify_inputs(manifest: Manifest) -> dict[str, str]:
    """Entrada -> problema, para cada entrada que falta ou não confere. Vazio: tudo confere."""
    problems = {}
    for name, spec in sorted(manifest.inputs.items()):
        try:
            got = input_digest(spec)
        except FileNotFoundError:
            problems[name] = "faltando"
            continue
        if got != str(spec["digest"]).lower().removeprefix("sha256:"):
            problems[name] = f"digest {got}"
    return problems


# --- estágios que já existem ------------------------------------------------------------------

_CONTRACT_FILES = ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.json", "merges.txt")


def _safetensors_shapes(root: Path) -> dict[str, tuple]:
    import struct
    shapes = {}
    for f in sorted(root.glob("*.safetensors")):
        with open(f, "rb") as fh:
            n = struct.unpack("<Q", fh.read(8))[0]
            header = json.loads(fh.read(n))
        shapes |= {k: tuple(v["shape"]) for k, v in header.items() if k != "__metadata__"}
    return shapes


def contract_check(base: Path, derivative: Path) -> list[str]:
    """Pré-checagem J2 (E14 §13): mesmo tokenizer e mesmas formas que o base. Devolve as divergências.

    Um adaptador LoRA (adapter_config.json) é mesclado sob custódia antes (J2a); aqui ele passa se não
    trouxer tokenizer próprio diferente. Pesos com forma diferente do base ou tensor a mais ou a menos
    ficam fora do contrato.
    """
    base, derivative = Path(base), Path(derivative)
    problems = []
    for f in _CONTRACT_FILES:
        b, d = base / f, derivative / f
        if d.is_file() and (not b.is_file() or file_sha256(b) != file_sha256(d)):
            problems.append(f"{f} diferente do base")
    if (derivative / "adapter_config.json").is_file():
        return problems
    bs, ds = _safetensors_shapes(base), _safetensors_shapes(derivative)
    if not ds:
        problems.append("derivado sem safetensors")
        return problems
    for k in sorted(set(bs) | set(ds)):
        if k not in ds:
            problems.append(f"falta {k}")
        elif k not in bs:
            problems.append(f"tensor a mais {k}")
        elif bs[k] != ds[k]:
            problems.append(f"forma de {k}: {ds[k]} != {bs[k]}")
    return problems


def _dataset_prompts(dataset: Path):
    """Pedidos do dataset do job: JSONL com "prompt" ou CSV com a coluna "prompt" (o formato da plataforma).

    Linha sem pedido conta como pedido vazio, para a numeração bater com o arquivo.
    """
    import csv
    text = Path(dataset).read_text(encoding="utf-8")
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    if first.lstrip().startswith("{"):
        for line in text.splitlines():
            if line.strip():
                yield str(json.loads(line).get("prompt", ""))
        return
    rows = csv.DictReader(text.splitlines())
    if "prompt" not in (rows.fieldnames or []):
        raise ValueError("dataset CSV sem a coluna prompt")
    for row in rows:
        yield str(row.get("prompt") or "")


def dataset_overlap(dataset: Path, battery_hashes: set[str]) -> list[int]:
    """Linhas do dataset do job cujo pedido normalizado está na bateria (T-103)."""
    return [i for i, prompt in enumerate(_dataset_prompts(dataset)) if prompt_hash(prompt) in battery_hashes]


@dataclass
class Stages:
    """Os estágios do Juiz. Os que dependem de tasks abertas levantam StageNotReady."""
    battery_hashes: set[str] = field(default_factory=lambda: {it["sha256"] for it in load_pool()["items"]})

    def contract(self, m: Manifest) -> list[str]:
        return contract_check(Path(m.inputs["base"]["path"]), Path(m.inputs["derivative"]["path"]))

    def dataset_overlap(self, m: Manifest) -> list[int]:
        return dataset_overlap(Path(m.inputs["dataset"]["path"]), self.battery_hashes)

    def prereg(self, m: Manifest) -> Prereg:
        raise StageNotReady("prereg.yaml ainda sem valores (T-606)")

    def s1(self, m: Manifest) -> tuple[list[dict], list[dict], bool]:
        """(células de metrics.compare, respostas para o responses.jsonl, formatos idênticos)."""
        raise StageNotReady("S1 precisa da referência custodiada do pai (T-312) e do avaliador na nuvem")

    def signals(self, m: Manifest) -> Sequence[SignalReading]:
        raise StageNotReady("S2/S3 por formato e condição ainda não ligados ao job")

    def utility(self, m: Manifest) -> Utility:
        raise StageNotReady("utilidade no corpus benigno (T-910)")

    def injection(self, m: Manifest) -> bool:
        raise StageNotReady("detecção de injeção dirigida ao avaliador")


def _hashes(m: Manifest, responses_sha: str) -> dict[str, str]:
    i = m.inputs
    return {"parent": i["base"]["digest"], "parent_reference": i["parent_reference"]["digest"],
            "derivative": i["derivative"]["digest"], "judge": m.judge_hash,
            "battery_commitment": m.battery_commitment, "prereg": i["prereg"]["digest"],
            "dataset": i["dataset"]["digest"], "responses": responses_sha}


def _write_responses(out: Path, responses: list[dict]) -> str:
    data = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in responses).encode()
    (out / RESPONSES_FILE).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _result(out: Path, doc: dict) -> dict:
    (out / RESULT_FILE).write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return doc


def run_job(manifest: Manifest, out: Path, stages: Stages | None = None, *, judge_hash: str | None = None) -> dict:
    """Roda o job e devolve o resultado (também gravado em job_result.json).

    judge_hash: hash do Juiz em execução; padrão, o calculado do próprio pacote (judge_package).
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    running = judge_hash or running_judge_hash()[0]
    if running != manifest.judge_hash.lower():
        return _result(out, {"status": "failure", "outcome": "inconclusive_failure", "alert": "judge_hash_mismatch",
                             "error": f"Juiz em execução {running} != manifesto {manifest.judge_hash}"})
    stages = stages or Stages()

    problems = verify_inputs(manifest)
    if problems:
        verdict = Verdict(REJECTED, "0", (Reason("hash_mismatch", {"inputs": problems}),), 0)
        doc = emit.build(verdict, cells=[], prereg=None, hashes=_hashes(manifest, _write_responses(out, [])),
                         identity_id=manifest.identity_id, decided_at=manifest.decided_at)
        sha = emit.write(doc, out / VERDICT_FILE)
        return _result(out, {"status": "verdict", "state": doc["state"], "verdict_sha256": sha,
                             "alert": "hash_mismatch", "problems": problems})

    try:
        contract_problems = stages.contract(manifest)
        overlap = stages.dataset_overlap(manifest)
        prereg = stages.prereg(manifest)
        cells, responses, formats_identical = stages.s1(manifest)
        signals = stages.signals(manifest)
        utility = stages.utility(manifest)
        injection = stages.injection(manifest)
        integrity = Integrity(hashes_ok=True, contract_ok=not contract_problems,
                              formats_identical=formats_identical, dataset_clean=not overlap)
        verdict = decide(cells, prereg=prereg, integrity=integrity, utility=utility, signals=signals,
                         injection_flagged=injection)
    except Exception as e:  # falha do instrumento ou do job: inconclusivo por falha, sem verdict.json
        return _result(out, {"status": "failure", "error": f"{type(e).__name__}: {e}"[:500],
                             "outcome": "inconclusive_failure"})

    doc = emit.build(verdict, cells=cells, prereg=prereg, hashes=_hashes(manifest, _write_responses(out, responses)),
                     identity_id=manifest.identity_id, decided_at=manifest.decided_at, signals=signals,
                     utility=utility)
    sha = emit.write(doc, out / VERDICT_FILE)
    return _result(out, {"status": "verdict", "state": doc["state"], "verdict_sha256": sha,
                         "contract_problems": contract_problems, "dataset_overlap_lines": overlap[:20]})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Juiz como job: entradas por hash, escada e verdict.json (T-807)")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    res = run_job(Manifest.load(a.manifest), a.out)
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res["status"] == "verdict" else 2


if __name__ == "__main__":
    raise SystemExit(main())
