"""verdict.json: a saída de esquema fixo do Juiz (T-608; E14 §4 e §10.1).

O código do Juiz escreve só este arquivo (as respostas vão cifradas à parte, com o hash aqui). A
CVM1 o valida contra o esquema e põe o SHA-256 dele no recibo (verdictHash, T-104/T-702); medidas e
motivos ficam fora do contrato, conferidos por esse hash.

Esquema dnat.verdict.v1 (chaves fixas; qualquer chave a mais ou a menos é recusada):
    schema       "dnat.verdict.v1"
    state        aprovado | reprovado | inconclusivo
    rule         regra da escada que decidiu: "1", "0", "2", "3", "4" ou "-" (nada disparou)
    reasons      [{code, ...detalhe}] da regra que decidiu (combine.Reason.record)
    instruments  motivos por instrumento: {s1, integrity, guards, second_line} -> [code]
    measures     {n_tests, s1: [células de metrics.compare], signals: [{format, condition, rho, e1}],
                  utility: {relative_ce_loss, degenerate_rate} | null}
    thresholds   os limiares do Prereg usados (prereg.yaml congelado; o hash dele está em hashes);
                 null só no reprovado por hash que não confere, que não chega a medir (s1 vazio)
    hashes       {parent, parent_reference, derivative, judge, battery_commitment, prereg, dataset,
                  responses}: SHA-256 em 64 hex minúsculos (bytes32 do recibo sem o 0x)
    identity_id  SHA-256 da chave pública de quem pediu o job (E14 §18), 64 hex
    decided_at   instante do veredito, ISO 8601 em UTC terminando em Z

Serialização canônica (chaves ordenadas, sem espaços, UTF-8, sem NaN): o mesmo veredito dá o
mesmo hash em qualquer máquina.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from model_gate.verdict.combine import STATES, Prereg, SignalReading, Utility, Verdict

SCHEMA_ID = "dnat.verdict.v1"
RULES = ("1", "0", "2", "3", "4", "-")
HASH_FIELDS = ("parent", "parent_reference", "derivative", "judge", "battery_commitment", "prereg", "dataset",
               "responses")
TOP_FIELDS = ("schema", "state", "rule", "reasons", "instruments", "measures", "thresholds", "hashes",
              "identity_id", "decided_at")
INSTRUMENTS = ("s1", "integrity", "guards", "second_line")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")

# Motivo -> instrumento que o produziu (a escada usa estes códigos; combine.py).
REASON_INSTRUMENT = {
    "harm_veto": "s1", "s1_unresolved": "s1", "instrument_failure": "s1",
    "hash_mismatch": "integrity", "outside_contract": "integrity", "format_not_identical": "integrity",
    "dataset_overlap": "integrity", "few_anchors": "integrity",
    "overrefusal": "guards", "refusal_drop_without_harm": "guards", "secret_public_disagreement": "guards",
    "degenerate": "guards", "utility_missing": "guards", "judge_injection": "guards", "missing_block": "guards",
    "s2_flag": "second_line", "s3_flag": "second_line", "signal_missing": "second_line",
    "format_divergence": "second_line",
}


class VerdictSchemaError(ValueError):
    pass


def _hex(value: str) -> str:
    s = str(value).lower().removeprefix("0x").removeprefix("sha256:")
    if not _HEX64.match(s):
        raise VerdictSchemaError(f"hash tem de ser SHA-256 em 64 hex, veio {value!r}")
    return s


def _iso(dt: datetime | str) -> str:
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        raise VerdictSchemaError("decided_at sem fuso: use UTC")
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build(verdict: Verdict, *, cells: Sequence[dict], prereg: Prereg | None, hashes: Mapping[str, str], identity_id: str,
          decided_at: datetime | str, signals: Sequence[SignalReading] = (), utility: Utility | None = None) -> dict:
    """Monta o documento a partir do veredito da escada e das medidas que ela leu, e o valida."""
    reasons = [r.record() for r in verdict.reasons]
    instruments = {k: [] for k in INSTRUMENTS}
    for r in reasons:
        instruments[REASON_INSTRUMENT[r["code"]]].append(r["code"])
    doc = {
        "schema": SCHEMA_ID,
        "state": verdict.state,
        "rule": verdict.rule,
        "reasons": reasons,
        "instruments": {k: sorted(set(v)) for k, v in instruments.items()},
        "measures": {
            "n_tests": verdict.n_tests,
            "s1": [dict(c) for c in cells],
            "signals": [dataclasses.asdict(s) for s in signals],
            "utility": dataclasses.asdict(utility) if utility is not None else None,
        },
        "thresholds": ({k: (dict(v) if isinstance(v, Mapping) else list(v) if isinstance(v, tuple) else v)
                        for k, v in dataclasses.asdict(prereg).items()} if prereg is not None else None),
        "hashes": {k: _hex(hashes[k]) for k in HASH_FIELDS if k in hashes},
        "identity_id": _hex(identity_id),
        "decided_at": _iso(decided_at),
    }
    validate(doc)
    return doc


def _no_nan(obj, where="") -> None:
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        raise VerdictSchemaError(f"número não finito em {where or 'raiz'}")
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise VerdictSchemaError(f"chave não textual em {where}")
            _no_nan(v, f"{where}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _no_nan(v, f"{where}[{i}]")


def validate(doc: Mapping) -> None:
    """Confere o esquema dnat.verdict.v1; levanta VerdictSchemaError no primeiro problema."""
    if not isinstance(doc, Mapping):
        raise VerdictSchemaError("documento tem de ser um objeto")
    keys = set(doc)
    if keys != set(TOP_FIELDS):
        raise VerdictSchemaError(f"chaves erradas: faltam {sorted(set(TOP_FIELDS) - keys)}, sobram {sorted(keys - set(TOP_FIELDS))}")
    if doc["schema"] != SCHEMA_ID:
        raise VerdictSchemaError(f"schema {doc['schema']!r}")
    if doc["state"] not in STATES:
        raise VerdictSchemaError(f"state {doc['state']!r}")
    if doc["rule"] not in RULES:
        raise VerdictSchemaError(f"rule {doc['rule']!r}")
    if (doc["state"] == "aprovado") != (doc["rule"] == "-"):
        raise VerdictSchemaError("aprovado se e só se nenhuma regra disparou")
    if not isinstance(doc["reasons"], list) or any(not isinstance(r, Mapping) or r.get("code") not in REASON_INSTRUMENT
                                                   for r in doc["reasons"]):
        raise VerdictSchemaError("reasons: lista de {code, ...} com códigos conhecidos")
    if (doc["rule"] == "-") != (not doc["reasons"]):
        raise VerdictSchemaError("regra disparada sem motivo, ou motivo sem regra")
    inst = doc["instruments"]
    if not isinstance(inst, Mapping) or set(inst) != set(INSTRUMENTS):
        raise VerdictSchemaError(f"instruments tem de ter {INSTRUMENTS}")
    expected = {k: sorted({r["code"] for r in doc["reasons"] if REASON_INSTRUMENT[r["code"]] == k}) for k in INSTRUMENTS}
    if {k: list(v) for k, v in inst.items()} != expected:
        raise VerdictSchemaError("instruments não bate com reasons")
    m = doc["measures"]
    if not isinstance(m, Mapping) or set(m) != {"n_tests", "s1", "signals", "utility"}:
        raise VerdictSchemaError("measures: n_tests, s1, signals, utility")
    # Hash que não confere (E14 §4) reprova na regra 0 antes de medir: só aí s1 e limiares ficam vazios.
    unmeasured = doc["state"] == "reprovado" and doc["rule"] == "0" and \
        {r["code"] for r in doc["reasons"]} == {"hash_mismatch"}
    if not isinstance(m["n_tests"], int) or m["n_tests"] < 0 or not isinstance(m["s1"], list) \
            or (not m["s1"] and not unmeasured):
        raise VerdictSchemaError("measures: n_tests inteiro ≥ 0 e s1 com pelo menos uma célula")
    for c in m["s1"]:
        if not {"format", "condition", "block", "kind", "category", "n_items", "failed", "derivative", "parent",
                "diff"} <= set(c):
            raise VerdictSchemaError("célula do s1 fora do esquema de metrics.compare")
    for s in m["signals"]:
        if set(s) != {"format", "condition", "rho", "e1"}:
            raise VerdictSchemaError("sinal fora do esquema")
    if m["utility"] is not None and set(m["utility"]) != {"relative_ce_loss", "degenerate_rate"}:
        raise VerdictSchemaError("utility fora do esquema")
    if unmeasured and doc["thresholds"] is None:
        pass
    elif not isinstance(doc["thresholds"], Mapping) or "delta" not in doc["thresholds"]:
        raise VerdictSchemaError("thresholds sem delta")
    h = doc["hashes"]
    if not isinstance(h, Mapping) or set(h) != set(HASH_FIELDS):
        raise VerdictSchemaError(f"hashes tem de ter exatamente {HASH_FIELDS}")
    for k, v in h.items():
        if not isinstance(v, str) or not _HEX64.match(v):
            raise VerdictSchemaError(f"hashes.{k} não é SHA-256 em 64 hex minúsculos")
    if not isinstance(doc["identity_id"], str) or not _HEX64.match(doc["identity_id"]):
        raise VerdictSchemaError("identity_id não é SHA-256 em 64 hex minúsculos")
    if not isinstance(doc["decided_at"], str) or not _ISO_Z.match(doc["decided_at"]):
        raise VerdictSchemaError("decided_at tem de ser ISO 8601 em UTC com Z")
    _no_nan(doc)


def canonical_bytes(doc: Mapping) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def verdict_hash(doc: Mapping) -> str:
    """SHA-256 da forma canônica, em 64 hex: o verdictHash do recibo (0x + isto no contrato)."""
    return hashlib.sha256(canonical_bytes(doc)).hexdigest()


def write(doc: Mapping, path: Path) -> str:
    """Valida, grava na forma canônica e devolve o hash. Nada é gravado se o esquema falha."""
    validate(doc)
    data = canonical_bytes(doc)
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> tuple[dict, str]:
    """Lê, valida e devolve (documento, hash dos bytes lidos): a conferência que a CVM1 faz."""
    data = Path(path).read_bytes()
    doc = json.loads(data)
    validate(doc)
    if canonical_bytes(doc) != data:
        raise VerdictSchemaError("arquivo fora da forma canônica")
    return doc, hashlib.sha256(data).hexdigest()
