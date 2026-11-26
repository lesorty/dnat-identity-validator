#!/usr/bin/env python3
"""Teste 11 · Atacante com muitas identidades (P6, P5): quanto cada tentativa custa, contra um usuário honesto.

Usa o preço medido no T10 (mesmo perfil e commit) e, se o T6 já rodou, acrescenta a taxa de escape
medida por ele (e > 0) às taxas da conta.

mini:  d = 12 (segundos).   nuvem: d = 20.

    python3 -I tools/testes/t11_atacante_sybil.py --perfil mini       # depois do T10
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from executor import PEQUENOS, Passo, Teste, check, main, read_json, tool
from perfis import dep

RATES = ("E=$(python3 -I -c 'import json,sys\n"
         "try: e=json.load(open(sys.argv[1]))[\"e\"]\n"
         "except Exception: e=0\n"
         "base=[0.005,0.01,0.02,0.05]\n"
         "print(\",\".join(map(str,sorted(set(base+([e] if 0<e<1 else []))))))' "
         f"{dep('T6', 'atacante', 'atacante.json')}) && ")


def passos(perfil: str) -> list[Passo]:
    d = 12 if perfil in PEQUENOS else 16 if perfil == "piloto" else 20
    return [Passo("t11", "Atacantes e honestos contra as rotas reais de identidade e cota, e a economia do ataque",
                  RATES + f"cd smart-contract && node e2e/t11_atacante_sybil.js --d {d} --e $E "
                  f"--t10 {dep('T10', 't10', 'T10_preco_identidade.json')} --out $PASSO_DIR/T11_atacante_sybil",
                  requer=(tool("node"),))]


def conferir(ctx) -> list[dict]:
    r = read_json(ctx.passo_dir("t11") / "T11_atacante_sybil.json")
    if not r:
        return [check("resultado do T11", None, "faltando")]
    out = [check(c["name"], bool(c["ok"])) for c in r.get("checks", [])]
    per = r.get("perIdentity") or {}
    out.append(check("tentativas por identidade (reprovado / inconclusivo / aprovado)",
                     (per.get("rejected"), per.get("inconclusive"), per.get("approved")) == (4, 8, 16),
                     per, "4 / 8 / 16"))
    return out


def numeros(ctx) -> dict:
    r = read_json(ctx.passo_dir("t11") / "T11_atacante_sybil.json") or {}
    return {"por_identidade": r.get("perIdentity"), "taxas_e": (r.get("params") or {}).get("escapeRates")}


TESTE = Teste(
    id="T11", nome="Atacante com muitas identidades", perguntas="P6 · P5",
    objetivo="Simula um atacante que cria várias identidades e mede quanto cada tentativa lhe custa, contra um usuário honesto.",
    gabarito=("Nenhuma identidade passa de 4 reprovações (402 depois); sem saldo, nada é aceito.",
              "Os truques (reusar a prova, registrar de novo, sem assinatura, repetir o pedido) são recusados.",
              "O honesto faz 16 aprovações por identidade; com e = 1%, um escape custa 400 aprovações honestas."),
    passos=passos, conferir=conferir, numeros=numeros, depende=("T10",),
    pendencias=("Decidir d, Q e se a prova deve gastar memória (Argon2) para tirar a vantagem da GPU.",),
)

if __name__ == "__main__":
    sys.exit(main(TESTE))
