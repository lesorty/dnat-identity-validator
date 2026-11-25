#!/usr/bin/env python3
"""Roda os Testes T1 a T11 na ordem, confere antes de gastar máquina e empacota tudo para trazer de volta.

    python3 -I tools/testes/todos.py verificar --perfil nuvem [--fase 1|2]   pré-voo de todos, sem rodar nada
    python3 -I tools/testes/todos.py rodar --perfil mini                      os 11, na ordem (~30 min no notebook)
    python3 -I tools/testes/todos.py rodar --perfil nuvem --fase 1            T1, T9, T10, T11, T2
    python3 -I tools/testes/todos.py rodar --perfil nuvem --fase 2            T3, T5, T6, T7, T8, T11 de novo, T4
    python3 -I tools/testes/todos.py status --perfil nuvem                    a situação de cada teste
    python3 -I tools/testes/todos.py pacote --perfil nuvem                    .tar.gz da campanha (sem textos gerados)

(ou: make testes-verificar | make testes | make testes-status | make testes-pacote, com PERFIL= e FASE=)

Na nuvem, a campanha tem duas fases porque o prereg só se fixa depois do T2: a fase 1 mede custo,
identidade e calibração com o prereg provisório; entre as fases, uma pessoa revisa a proposta do T2,
copia para model_gate/prereg.yaml (T-606) e congela (make congelar); a fase 2 usa o Juiz congelado.
As duas gravam na mesma pasta ($MODEL_GATE_DATA/testes/nuvem/tst/), então nada da fase 1 se refaz.

Cada teste roda num processo próprio: uma falha não derruba os outros (os que dependem dela param no
pré-voo, com o motivo). Ao fim, um resumo de todos vai para todos_<data>.json na pasta da campanha.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from executor import DATA, REPO, ACOMP_DIR, campaign_key, head, now, read_json, write_json  # noqa: E402

SCRIPTS = {
    "T1": "t01_sanidade.py", "T2": "t02_calibracao.py", "T3": "t03_deteccao.py", "T4": "t04_familia_nao_vista.py",
    "T5": "t05_campo_cego.py", "T6": "t06_atacante_adaptativo.py", "T7": "t07_ablacao_custo.py",
    "T8": "t08_ponta_a_ponta.py", "T9": "t09_identidade_cota.py", "T10": "t10_preco_identidade.py",
    "T11": "t11_atacante_sybil.py",
}
ORDEM = {
    ("mini", "todas"): ["T1", "T2", "T3", "T5", "T4", "T6", "T7", "T8", "T9", "T10", "T11"],
    ("nuvem", "1"): ["T1", "T9", "T10", "T11", "T2"],
    ("nuvem", "2"): ["T3", "T5", "T6", "T7", "T8", "T11", "T4"],
}
REFAZER_NA_FASE2 = {"T11": ["t11"]}  # com o e medido pelo T6


def order(perfil: str, fase: str) -> list[str]:
    if perfil in ("mini", "ensaio"):
        return ORDEM[("mini", "todas")]
    if fase == "todas":
        return ORDEM[("nuvem", "1")] + [t for t in ORDEM[("nuvem", "2")] if t not in ORDEM[("nuvem", "1")]]
    return ORDEM[("nuvem", fase)]


def script(tid: str) -> list[str]:
    return [sys.executable, "-I", str(HERE / SCRIPTS[tid])]


def campaign_dir(perfil: str, campanha: str | None) -> Path:
    return DATA / "testes" / perfil / campaign_key(perfil, head(), campanha)


def verificar(a) -> int:
    bad = 0
    for tid in order(a.perfil, a.fase):
        r = subprocess.run(script(tid) + ["--verificar", "--perfil", a.perfil, *a.extra], capture_output=True, text=True)
        print((r.stdout or r.stderr).strip())
        bad += r.returncode != 0
    print(f"\n{bad} de {len(order(a.perfil, a.fase))} testes NÃO podem rodar no perfil {a.perfil}" if bad else
          "\ntodos prontos para rodar")
    return 1 if bad else 0


def rodar(a) -> int:
    rows = []
    t0 = time.time()
    for tid in order(a.perfil, a.fase):
        extra = list(a.extra)
        if a.perfil == "nuvem" and a.fase == "2" and tid in REFAZER_NA_FASE2:
            extra += ["--refazer", *REFAZER_NA_FASE2[tid]]
        print(f"\n################ {tid} ({a.perfil}) · {now()}", flush=True)
        t = time.time()
        rc = subprocess.run(script(tid) + ["--perfil", a.perfil, *extra]).returncode
        res = read_json(campaign_dir(a.perfil, a.campanha) / tid / "resumo.json") or {}
        rows.append({"teste": tid, "codigo": rc, "estado": res.get("estado") if rc != 2 else "não rodou (pré-voo)",
                     "minutos": round((time.time() - t) / 60, 1)})
    d = campaign_dir(a.perfil, a.campanha)
    write_json(d / f"todos_{time.strftime('%Y%m%dT%H%M%S')}.json",
               {"perfil": a.perfil, "fase": a.fase, "quando": now(), "commit": head()["commit"], "testes": rows,
                "minutos": round((time.time() - t0) / 60, 1)})
    print(f"\n{'teste':<6} {'estado':<24} {'min':>6}")
    for r in rows:
        print(f"{r['teste']:<6} {str(r['estado']):<24} {r['minutos']:>6}")
    print(f"total {round((time.time() - t0) / 60, 1)} min · pasta {d}")
    return 0 if all(r["codigo"] == 0 for r in rows) else 1


def status(a) -> int:
    d = campaign_dir(a.perfil, a.campanha)
    print(f"campanha {a.perfil} em {d}\n")
    for tid in SCRIPTS:
        res = read_json(d / tid / "resumo.json")
        st = read_json(d / tid / "estado.json") or {}
        if not res and not st:
            print(f"  {tid:<4} não rodou")
            continue
        passos = " ".join(f"{k}:{v.get('estado')}" for k, v in st.get("passos", {}).items())
        conf = res.get("conferencias", []) if res else []
        nok = sum(1 for c in conf if c["ok"])
        print(f"  {tid:<4} {(res or {}).get('estado', 'em andamento'):<11} {nok}/{len(conf)} conferências · {passos}")
    return 0


GRANDE_MB = 50   # no pacote completo, arquivo de pesos maior que isto fica de fora (o derivado se refaz pela receita)


def insumos(d: Path) -> list[Path]:
    """O que os vereditos e rótulos da campanha usaram fora da pasta dela: as referências do pai (testes_*,
    rotulo_*, forjada_*) e os derivados que a população montou (adaptadores LoRA, receitas, carimbos)."""
    refs, ders = set(), set()
    for f in d.rglob("contexto.json"):
        r = (read_json(f) or {}).get("referencia")
        if r:
            refs.add(Path(r))
    for f in d.rglob("populacao.json"):
        for row in read_json(f) or []:
            c = str(row.get("caminho") or "")
            if c.startswith("derivatives/"):
                ders.add(DATA / c)
    if (DATA / "references").is_dir():
        refs |= set((DATA / "references").glob("rotulo_*")) | set((DATA / "references").glob("forjada_*"))
    return sorted(p for p in refs | ders if p.exists())


def pacote(a) -> int:
    """Leve (padrão): tudo da campanha menos os textos gerados (T-211) e as respostas dos jobs, mais o
    acompanhamento e a ficha. É o que vai para resultados_nuvem/ e para o git.
    Completo (--completo): também os textos, as respostas, as referências do pai, os adaptadores e o log do
    serviço; só pesos grandes ficam de fora. Para guardar fora do git (notebook, bucket), para investigar."""
    d = campaign_dir(a.perfil, a.campanha)
    if not d.exists():
        raise SystemExit(f"nada em {d}")
    out_dir = DATA / "pacotes"
    out_dir.mkdir(parents=True, exist_ok=True)
    import socket
    completo = getattr(a, "completo", False)
    name = (f"testes_{a.perfil}_{d.name}_{socket.gethostname()}_{time.strftime('%Y%m%dT%H%M%S')}"
            + ("_completo" if completo else ""))
    out = out_dir / f"{name}.tar.gz"
    skip_names = () if completo else ("_texts.json", "_texts.jsonl", "responses.jsonl")

    def keep(ti):
        if completo:
            big = ti.isfile() and ti.size > GRANDE_MB * 2**20 and ti.name.endswith((".safetensors", ".bin", ".pt"))
            return None if big else ti
        return None if ti.name.endswith(skip_names) else ti

    machine = sorted((DATA / "machine").glob("*.json")) if (DATA / "machine").is_dir() else []
    with tarfile.open(out, "w:gz") as tar:
        tar.add(d, arcname=f"{name}/campanha", filter=keep)
        for f in ACOMP_DIR.glob("*"):
            tar.add(f, arcname=f"{name}/acompanhamento/{f.name}")
        for f in machine:
            tar.add(f, arcname=f"{name}/maquina/{f.name}")
        if completo:
            for p in insumos(d):
                tar.add(p, arcname=f"{name}/insumos/{p.relative_to(DATA)}", filter=keep)
            svc = Path.home() / ".dnat-testes" / "servico.log"
            if svc.exists():
                tar.add(svc, arcname=f"{name}/servico.log")
        meta = {"perfil": a.perfil, "campanha": d.name, "criado": now(), "head": head(), "host": socket.gethostname(),
                "completo": completo, "aviso": "contém textos gerados: fora do git (T-211)" if completo else None}
        mf = out_dir / f"{name}.json"
        mf.write_text(json.dumps(meta, indent=1, ensure_ascii=False))
        tar.add(mf, arcname=f"{name}/pacote.json")
    print(f"pacote: {out} ({out.stat().st_size / 2**20:.1f} MB)")
    print(f"para trazer: scp {os.environ.get('USER', 'usuario')}@{socket.gethostname()}:{out} .")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("acao", choices=("verificar", "rodar", "status", "pacote"))
    ap.add_argument("--perfil", choices=("mini", "ensaio", "nuvem"), default=os.environ.get("PERFIL", "mini"))
    ap.add_argument("--fase", choices=("1", "2", "todas"), default=os.environ.get("FASE", "todas"))
    ap.add_argument("--campanha", default=os.environ.get("TESTES_CAMPANHA"))
    ap.add_argument("--completo", action="store_true", help="pacote: com textos, referências e adaptadores (fora do git)")
    a, extra = ap.parse_known_args(argv)
    a.extra = extra + (["--campanha", a.campanha] if a.campanha else [])
    return {"verificar": verificar, "rodar": rodar, "status": status, "pacote": pacote}[a.acao](a)


if __name__ == "__main__":
    sys.exit(main())
