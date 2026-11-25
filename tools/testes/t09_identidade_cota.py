#!/usr/bin/env python3
"""Teste 9 · Identidade e cota: o mecanismo (P6). Registrar exige prova de trabalho, todo pedido é
assinado e a cota acaba. Igual nos dois perfis (só CPU, segundos a minutos).

    python3 -I tools/testes/t09_identidade_cota.py --perfil mini
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from executor import Passo, Teste, check, main, read_json, tool


def passos(perfil: str) -> list[Passo]:
    return [
        Passo("testes", "Testes automáticos de identidade e cota (hardhat/mocha)",
              "cd smart-contract && npm run --silent test:identity", requer=(tool("node"), tool("npm"))),
        Passo("demo", "Demonstração: registro, assinatura, reservas e o 5º job recusado",
              "cd smart-contract && DEMO_COTA_DIR=$PASSO_DIR node e2e/demo_cota.js"),
    ]


def conferir(ctx) -> list[dict]:
    r = read_json(ctx.passo_dir("demo") / "demo_cota.json")
    st = (ctx.dir / "estado.json")
    tests_ok = (read_json(st) or {}).get("passos", {}).get("testes", {}).get("estado") == "ok"
    out = [check("testes automáticos de identidade e cota passam", tests_ok)]
    if not r:
        return out + [check("demonstração", None, "faltando")]
    return out + [check(c["name"], bool(c["ok"])) for c in r.get("checks", [])]


TESTE = Teste(
    id="T9", nome="Identidade e cota: o mecanismo", perguntas="P6",
    objetivo="Confere que registrar exige prova de trabalho, que todo pedido é assinado e que a cota acaba.",
    gabarito=("Prova válida registra; inválida, de outro desafio ou de chave repetida é recusada.",
              "Pedido sem assinatura ou com carimbo velho: 401.",
              "Saldo 20; cada reprovado gasta 5; depois de 4, o 5º job recebe 402; falha devolve a reserva."),
    passos=passos, conferir=conferir,
)

if __name__ == "__main__":
    sys.exit(main(TESTE))
