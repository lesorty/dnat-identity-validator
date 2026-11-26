#!/usr/bin/env python3
"""Teste 8 · Ponta a ponta no DNAT (P8): o sistema obedece ao veredito e o recibo pode ser conferido.

mini:  e2e/run_direct.js, o fluxo inteiro sem Docker com o base minúsculo (Juiz real que falha sem
       prereg, e Juiz simulado aprovando e reprovando): recibo, retenção e cota. ~2 min.
nuvem: e2e/teste8.js com o Qwen real, o prereg congelado, a bateria da campanha, o avaliador do portão
       e a referência do pai medida no T3 com o mesmo desenho: reprovado retido, aprovado com recibo,
       operador revoga.

    python3 -I tools/testes/t08_ponta_a_ponta.py --perfil mini
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from executor import PEQUENOS, DATA, Passo, Teste, check, main, read_json, tool
from perfis import PERFIL, dep, prereg_pronto

REF = ("REF=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))[\"referencia\"])' "
       f"{dep('T3', 'vereditos', 'contexto.json')}) && ")


def passos(perfil: str) -> list[Passo]:
    P = PERFIL[perfil]
    if perfil in PEQUENOS:
        return [Passo("e2e", "Fluxo inteiro no modo direto (base minúsculo; Juiz real sem prereg e simulado)",
                      "cd smart-contract && E2E_RESULTS_DIR=$PASSO_DIR node e2e/run_direct.js", requer=(tool("node"),))]
    guard = DATA / "models" / "Qwen__Qwen3Guard-Gen-4B" / "6ec42827da0c1ff11e7a49dc269d2e810d27e108"
    return [Passo("teste8", "Qwen real com o Juiz congelado: retenção, recibo, revogação e cota",
                  REF + f"cd smart-contract && node e2e/teste8.js --prereg {P['prereg']} --battery {P['bateria']} "
                  f"--evaluator-kind guard --evaluator-dir {guard} --reference-dir \"$REF\" --out $PASSO_DIR/T-814_teste8",
                  requer=(*prereg_pronto(perfil), tool("node")))]


def conferir(ctx) -> list[dict]:
    if ctx.perfil in PEQUENOS:
        r = read_json(ctx.passo_dir("e2e") / "e2e_direct.json")
    else:
        r = read_json(ctx.passo_dir("teste8") / "T-814_teste8.json")
    if not r:
        return [check("resultado do ponta a ponta", None, "faltando")]
    checks = r.get("checks") or []
    if not checks:
        return [check("o roteiro gravou conferências", False, list(r)[:10])]
    return [check(c.get("name") or c.get("nome") or str(c), bool(c.get("ok"))) for c in checks]


TESTE = Teste(
    id="T8", nome="Ponta a ponta no DNAT", perguntas="P8",
    objetivo="Roda o caminho inteiro do sistema, do fine-tuning ao recibo, e confere que o sistema obedece ao veredito.",
    gabarito=("Um derivado reprovado fica retido: não vira ativo e o dono não o reativa.",
              "Um derivado aprovado vira ativo com recibo na cadeia; o registro do Juiz confere com o hash do recibo.",
              "O operador revoga e o derivado deixa de ser usável, sem volta; a cota acerta (5 para reprovado, 1 para aprovado).",
              "No mini, o Juiz real sem prereg falha e devolve a reserva; o simulado aprova (cota 1) e reprova (cota 5)."),
    passos=passos, conferir=conferir, depende=(),
    pendencias=("prereg.yaml congelado (T-606) e a referência do pai do T3 (mesmo desenho e avaliador).",
                "Atestação da CVM no recibo está fora do escopo (D3); o recibo prova o que o executor registrou."),
)

if __name__ == "__main__":
    sys.exit(main(TESTE))
