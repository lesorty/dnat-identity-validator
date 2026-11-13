"""T-608: verdict.json de esquema fixo, gerado a partir da escada e conferido antes de gravar."""

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from model_gate.verdict.combine import REJECTED
from model_gate.verdict.emit import (HASH_FIELDS, INSTRUMENTS, REASON_INSTRUMENT, SCHEMA_ID, TOP_FIELDS,
                                     VerdictSchemaError, build, canonical_bytes, read, validate, verdict_hash, write)
from tests.test_combine import OK_INTEGRITY, OK_SIGNALS, OK_UTILITY, PREREG, build as build_cells, run

H = {k: hashlib.sha256(k.encode()).hexdigest() for k in HASH_FIELDS}
ID = hashlib.sha256(b"identidade").hexdigest()
WHEN = datetime(2026, 11, 12, 23, 0, 0, tzinfo=timezone.utc)


def doc_for(cells=None, **kw):
    cells = cells or build_cells()
    v = run(cells, **kw)
    return build(v, cells=cells, prereg=kw.get("prereg", PREREG), hashes=H, identity_id=ID, decided_at=WHEN,
                 signals=kw.get("signals", OK_SIGNALS), utility=kw.get("utility", OK_UTILITY))


def test_aprovado_tem_o_esquema_fixo():
    d = doc_for()
    assert tuple(sorted(d)) == tuple(sorted(TOP_FIELDS))
    assert (d["schema"], d["state"], d["rule"], d["reasons"]) == (SCHEMA_ID, "aprovado", "-", [])
    assert d["instruments"] == {k: [] for k in INSTRUMENTS}
    assert d["hashes"] == H and d["identity_id"] == ID and d["decided_at"] == "2026-11-12T23:00:00Z"
    assert d["measures"]["n_tests"] == 12 and len(d["measures"]["s1"]) > 0
    assert d["measures"]["signals"][0] == {"format": "fp", "condition": "vazio", "rho": 0.95, "e1": 0.1}
    assert d["thresholds"]["delta"] == {"*": 0.12} and d["thresholds"]["veto_blocks"] == ["anchors", "secret", "encoded"]


def test_reprovado_leva_motivo_por_instrumento():
    d = doc_for(build_cells(harm=lambda f, c, cat: 45 if cat == "A" else 0))
    assert (d["state"], d["rule"]) == (REJECTED, "1")
    assert d["instruments"]["s1"] == ["harm_veto"] and d["instruments"]["guards"] == []
    assert all(r["code"] == "harm_veto" and "harm_excess_lower" in r for r in d["reasons"])


def test_cada_motivo_da_escada_tem_instrumento():
    import inspect
    from model_gate.verdict import combine
    import re
    codes = set(re.findall(r'Reason\("([a-z0-9_]+)"', inspect.getsource(combine)))
    assert codes and codes <= set(REASON_INSTRUMENT)


def test_hashes_aceitam_0x_e_prefixo_sha256_mas_gravam_64_hex():
    cells = build_cells()
    v = run(cells)
    hs = {k: ("0x" + h if i % 2 else "sha256:" + h.upper()) for i, (k, h) in enumerate(H.items())}
    d = build(v, cells=cells, prereg=PREREG, hashes=hs, identity_id="0x" + ID, decided_at=WHEN,
              signals=OK_SIGNALS, utility=OK_UTILITY)
    assert d["hashes"] == H and d["identity_id"] == ID


def test_hash_faltando_ou_invalido_e_recusado():
    cells = build_cells()
    v = run(cells)
    with pytest.raises(VerdictSchemaError, match="hashes"):
        build(v, cells=cells, prereg=PREREG, hashes={k: H[k] for k in HASH_FIELDS[:-1]}, identity_id=ID,
              decided_at=WHEN)
    with pytest.raises(VerdictSchemaError, match="64 hex"):
        build(v, cells=cells, prereg=PREREG, hashes=H | {"judge": "abc"}, identity_id=ID, decided_at=WHEN)
    with pytest.raises(VerdictSchemaError, match="fuso"):
        build(v, cells=cells, prereg=PREREG, hashes=H, identity_id=ID, decided_at=datetime(2026, 1, 1))


def test_fuso_diferente_vira_utc():
    cells = build_cells()
    d = build(run(cells), cells=cells, prereg=PREREG, hashes=H, identity_id=ID,
              decided_at=WHEN.astimezone(timezone(timedelta(hours=-3))), signals=OK_SIGNALS, utility=OK_UTILITY)
    assert d["decided_at"] == "2026-11-12T23:00:00Z"


@pytest.mark.parametrize("mutate,match", [
    (lambda d: d.update(extra=1), "sobram"),
    (lambda d: d.pop("hashes"), "faltam"),
    (lambda d: d.update(state="talvez"), "state"),
    (lambda d: d.update(rule="9"), "rule"),
    (lambda d: d.update(rule="3"), "aprovado se e só se"),
    (lambda d: d["instruments"].update(s1=["harm_veto"]), "instruments"),
    (lambda d: d["measures"].update(s1=[]), "s1"),
    (lambda d: d["measures"]["s1"][0].pop("diff"), "célula"),
    (lambda d: d["measures"]["signals"][0].update(extra=1), "sinal"),
    (lambda d: d["measures"]["s1"][0]["derivative"].update(harm_rate=float("nan")), "não finito"),
    (lambda d: d.update(decided_at="2026-11-12 23:00"), "decided_at"),
    (lambda d: d["hashes"].update(judge="A" * 64), "64 hex"),
])
def test_validate_recusa_documento_fora_do_esquema(mutate, match):
    d = copy.deepcopy(doc_for())
    mutate(d)
    with pytest.raises(VerdictSchemaError, match=match):
        validate(d)


def test_motivo_desconhecido_ou_regra_sem_motivo():
    d = copy.deepcopy(doc_for(build_cells(refusals=8)))
    assert d["rule"] == "3"
    bad = copy.deepcopy(d)
    bad["reasons"] = [{"code": "inventado"}]
    with pytest.raises(VerdictSchemaError, match="códigos conhecidos"):
        validate(bad)
    bad = copy.deepcopy(d)
    bad["reasons"] = []
    with pytest.raises(VerdictSchemaError):
        validate(bad)


def test_grava_canonico_e_o_hash_e_o_dos_bytes(tmp_path):
    d = doc_for()
    p = tmp_path / "verdict.json"
    h = write(d, p)
    data = p.read_bytes()
    assert h == hashlib.sha256(data).hexdigest() == verdict_hash(d)
    assert data == canonical_bytes(d) and b" " not in data.replace(b"\xc3", b"")[:2]
    again, h2 = read(p)
    assert again == json.loads(data) and h2 == h
    # a mesma entrada em outra ordem de chaves dá o mesmo hash
    shuffled = dict(reversed(list(d.items())))
    assert verdict_hash(shuffled) == h


def test_nada_e_gravado_se_o_esquema_falha(tmp_path):
    d = copy.deepcopy(doc_for())
    d["state"] = "x"
    p = tmp_path / "verdict.json"
    with pytest.raises(VerdictSchemaError):
        write(d, p)
    assert not p.exists() and not list(tmp_path.iterdir())


def test_read_recusa_arquivo_fora_da_forma_canonica(tmp_path):
    d = doc_for()
    p = tmp_path / "verdict.json"
    p.write_text(json.dumps(d, indent=2))
    with pytest.raises(VerdictSchemaError, match="canônica"):
        read(p)
