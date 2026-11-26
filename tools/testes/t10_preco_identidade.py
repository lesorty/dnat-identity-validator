#!/usr/bin/env python3
"""Teste 10 · O preço da identidade (P6): cara de criar, barata de conferir, medido na máquina real.

mini:  d de 16 a 18, 2 repetições (segundos).   nuvem: d de 16 a 27, 3 repetições (~1 h em 4 vCPU).
Com GPU, passe a taxa de SHA-256 dela (hashcat -b -m 1400) em GPU_RATE para a extrapolação.

    python3 -I tools/testes/t10_preco_identidade.py --perfil mini
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from executor import PEQUENOS, Passo, Teste, check, main, read_json, tool
from perfis import PERFIL


# Taxa de SHA-256 da GPU pelo hashcat (modo 1400, SHA-256 puro): a linha "Speed.#1....: 12345.6 MH/s".
HASHCAT = ("hashcat -b -m 1400 --quiet 2>&1 | tee $PASSO_DIR/hashcat.txt | python3 -I -c "
           "'import re,sys; u={\"H\":1,\"kH\":1e3,\"MH\":1e6,\"GH\":1e9,\"TH\":1e12}; "
           "m=[float(a)*u[b] for a,b in re.findall(r\"Speed\\.#\\d+\\.+:\\s*([\\d.]+)\\s*([kMGT]?H)/s\", sys.stdin.read())]; "
           "print(int(m[0])) if m else sys.exit(\"hashcat sem linha de Speed\")' > $PASSO_DIR/taxa.txt && cat $PASSO_DIR/taxa.txt")


def passos(perfil: str) -> list[Passo]:
    # piloto: d até 22 (segundos), o bastante para a lei do custo; a campanha vai até 27 com 3 repetições
    args = "--max 18 --reps 2" if perfil in PEQUENOS else "--max 22 --reps 2" if perfil == "piloto" else "--max 27 --reps 3"
    ps = []
    if PERFIL[perfil].get("env", {}).get("MODEL_GATE_DISPOSITIVO") == "cuda":
        # Página dos testes: "se houver GPU, mede quantos SHA-256 por segundo ela faz" (a vantagem de quem ataca
        # com hardware). Opcional: sem hashcat ou sem a taxa, o T10 segue só com a CPU.
        ps.append(Passo("gpu-sha256", "Taxa de SHA-256 da GPU (hashcat -b -m 1400)", HASHCAT,
                        requer=(tool("hashcat"),), opcional=True))
    ps.append(Passo("t10", "Prova de trabalho por d, todos os núcleos, conferência, reuso e extrapolação",
                    "GPU_RATE=${GPU_RATE:-$(cat $TESTE_DIR/passos/gpu-sha256/taxa.txt 2>/dev/null)}; "
                    f"cd smart-contract && node e2e/t10_preco_identidade.js {args} --out $PASSO_DIR/T10_preco_identidade"
                    " ${GPU_RATE:+--gpu-rate $GPU_RATE}", requer=(tool("node"),)))
    return ps


def conferir(ctx) -> list[dict]:
    r = read_json(ctx.passo_dir("t10") / "T10_preco_identidade.json")
    if not r:
        return [check("resultado do T10", None, "faltando")]
    return [check(c["name"], bool(c["ok"])) for c in r.get("checks", [])]


def numeros(ctx) -> dict:
    r = read_json(ctx.passo_dir("t10") / "T10_preco_identidade.json") or {}
    ref = (r.get("extrapolation") or {}).get("reference") or []
    return {"hashes_por_segundo_1_nucleo": (r.get("bench") or {}).get("hashesPerSecond"),
            "inclinacao": (r.get("law") or {}).get("slope"),
            "d_referencia": {str(x.get("hours")): x.get("difficulty") for x in ref}}


TESTE = Teste(
    id="T10", nome="O preço da identidade", perguntas="P6",
    objetivo="Prova que uma identidade é cara de criar e barata de conferir, e mede esse preço na máquina real.",
    gabarito=("O custo dobra a cada bit: inclinação de log2(hashes) em d a até 3 erros-padrão de 1.",
              "Conferir uma prova leva microssegundos e não depende de d.",
              "Uma prova não serve para outra chave nem para outra implantação; chave repetida dá 409.",
              "Todos os núcleos juntos são mais rápidos que um; a extrapolação dá o d de 1 h e de 5 h."),
    passos=passos, conferir=conferir, numeros=numeros,
    pendencias=("Taxa da GPU (hashcat -b -m 1400) se houver GPU: GPU_RATE=<hashes/s> no ambiente.",),
)

if __name__ == "__main__":
    sys.exit(main(TESTE))
