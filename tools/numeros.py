#!/usr/bin/env python3
"""Números do artigo tirados dos arquivos de resultado, nunca copiados à mão (make numeros).

    python3 -I tools/numeros.py            gera DSN2027/artigo/numeros.tex e numeros.md

Para cada número do catálogo abaixo, procura o resultado primeiro nos pacotes da nuvem importados em
commit congelado (resultados_nuvem/, tools/cloud/importar.sh) e, sem eles, na verificação local
(model_gate/results, smart-contract/results). O .tex define uma macro por número:

    \\numGasReciboAprovado     →  494.028          (nuvem, commit congelado)
    \\numGasReciboAprovado     →  \\local{494.028}  (verificação local: sai em vermelho no PDF)

e um comentário com a origem (arquivo, commit, run). O .md lista tudo para conferir. Número que o
resultado não tem vira \\tbd. Só biblioteca padrão.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_TEX = REPO / "DSN2027" / "artigo" / "numeros.tex"
OUT_MD = REPO / "DSN2027" / "artigo" / "numeros.md"
LOCAL = {"model_gate": REPO / "model_gate" / "results", "smart_contract": REPO / "smart-contract" / "results"}


def br(x: float, d: int = 0) -> str:
    """Número no padrão do artigo (inglês: vírgula de milhar, ponto decimal)."""
    return f"{x:,.{d}f}"


def find(rows, **kw):
    return next((r for r in rows or [] if all(r.get(k) == v for k, v in kw.items())), None)


# nome da macro → (arquivo de resultado "raiz/stem", extrator(json) → texto, descrição)
CATALOG = {
    "GasReciboAprovado": ("smart_contract/gas", lambda d: br(find(d["rows"], fn="registerDerivative (recibo, aprovado)")["gasUsed"]),
                          "gás do recibo de um aprovado (T-709)"),
    "GasReciboReprovado": ("smart_contract/gas", lambda d: br(find(d["rows"], fn="registerDerivative (recibo, reprovado)")["gasUsed"]),
                           "gás do recibo de um reprovado (T-709)"),
    "GasRevogacao": ("smart_contract/gas", lambda d: br(find(d["rows"], fn="revokeDerivative")["gasUsed"]), "gás da revogação (T-709)"),
    "HashesPorSegundo": ("smart_contract/identity_pow_cost", lambda d: br(d["hashesPerSecond"]), "hashes SHA-256 por segundo, 1 núcleo (T-1705)"),
    "ProvaDvinteSegundos": ("smart_contract/identity_pow_cost", lambda d: br(find(d["rows"], difficulty=20)["medianSeconds"], 1),
                            "mediana da prova de trabalho com d = 20, em s (T-1705)"),
    "IdentidadeDUmaHora": ("smart_contract/T10_preco_identidade",
                           lambda d: str(find(d["extrapolation"]["reference"], hours=1)["difficulty"]["1 núcleo"]),
                           "menor d em que criar uma identidade custa 1 h de um núcleo (Teste 10)"),
    "IdentidadeConferirMicrossegundos": ("smart_contract/T10_preco_identidade", lambda d: br(max(v["microseconds"] for v in d["verify"]), 1),
                                         "tempo de conferir uma prova, em µs (Teste 10)"),
    "AtacanteTentativasPorIdentidade": ("smart_contract/T11_atacante_sybil", lambda d: str(d["perIdentity"]["rejected"]),
                                        "tentativas reprovadas que uma identidade consegue (Teste 11)"),
    "HonestoAprovacoesPorIdentidade": ("smart_contract/T11_atacante_sybil", lambda d: str(d["perIdentity"]["approved"]),
                                       "aprovações que uma identidade honesta consegue (Teste 11)"),
    "RazaoEscapeHonestoUmPorCento": ("smart_contract/T11_atacante_sybil",
                                     lambda d: br(find(d["economics"]["perD"][0]["attacker"], e=0.01)["ratioToHonest"]),
                                     "custo de um escape ÷ custo de uma aprovação honesta, com e = 1% (Teste 11)"),
    "VazaoLoteUm": ("model_gate/T-208_vazao", lambda d: br(find(d["cells"], batch_size=1, max_new_tokens=64)["mean_tok_s"], 1),
                    "tokens/s em 4 vCPU, lote 1 (T-208)"),
    "VazaoLoteQuatro": ("model_gate/T-208_vazao", lambda d: br(find(d["cells"], batch_size=4, max_new_tokens=64)["mean_tok_s"], 1),
                        "tokens/s em 4 vCPU, lote 4 (T-208)"),
    "AvaliadorMinutosVeredito": ("model_gate/T-309_avaliador", lambda d: br(d["runs"][0]["verdict_minutes"]),
                                 "minutos do avaliador por veredito (T-309)"),
    "AvaliadorSegundosItem": ("model_gate/T-309_avaliador", lambda d: br(d["runs"][0]["seconds_per_item"], 1),
                              "segundos do avaliador por item (T-309)"),
    "AncorasTotal": ("model_gate/T-301_ancoras", lambda d: br(sum(d["anchors_in_both_conditions"].values())),
                     "âncoras recusadas nas duas condições (T-301)"),
    "ArditiCandidatos": ("model_gate/T-414_arditi", lambda d: br(len(d["candidatos"])), "candidatos de direção avaliados (T-414)"),
    "ArditiPassam": ("model_gate/T-414_arditi", lambda d: br(d["passam_induce_e_kl"]), "candidatos que passam na regra de Arditi (T-414)"),
    "ArditiNocivosRecusados": ("model_gate/T-414_arditi", lambda d: f"{d['validacao']['n_harmful_kept']} of {d['validacao']['n_harmful_val']}",
                               "nocivos da validação que o base recusa (T-414)"),
    "TreinoPicoRssGB": ("smart_contract/T-806_lora_uso_unico", lambda d: br(d["jobVm"]["peakRssBytes"] / 2**30, 1),
                        "pico de RSS do treino LoRA na CVM de uso único, GB (T-806)"),
    "TreinoSegundos": ("smart_contract/T-806_lora_uso_unico", lambda d: br(d["job"]["metrics"]["train_seconds"]),
                       "segundos de treino LoRA, 10 passos (T-806)"),
}


def cloud_sources() -> list[tuple[Path, dict]]:
    """Pacotes importados em commit congelado, do mais novo para o mais velho."""
    root = REPO / "resultados_nuvem"
    out = []
    for d in sorted(root.iterdir(), reverse=True) if root.is_dir() else []:
        try:
            meta = json.loads((d / "pacote.json").read_text())
        except (OSError, ValueError):
            continue
        if meta.get("congelado"):
            out.append((d, meta))
    return out


def locate(key: str) -> tuple[Path | None, str, dict | None]:
    base, stem = key.split("/")
    sub = "smart-contract" if base == "smart_contract" else "model_gate"
    for d, meta in cloud_sources():
        f = d / "results" / sub / f"{stem}.json"
        if f.exists():
            return f, "nuvem", meta
    f = LOCAL[base] / f"{stem}.json"
    return (f, "local", None) if f.exists() else (None, "ausente", None)


def tex_escape(s: str) -> str:
    return s.replace("%", r"\%").replace("&", r"\&").replace("_", r"\_")


def main() -> int:
    tex = ["% Gerado por tools/numeros.py (make numeros). NÃO EDITE À MÃO: rode de novo.",
           "% \\local{...}: verificação local, não dado do artigo (regra de 12/11); sai em vermelho.",
           "\\providecommand{\\local}[1]{\\textcolor{red}{#1\\textsuperscript{local}}}",
           "\\providecommand{\\tbd}{\\textcolor{red}{TBD}}", ""]
    md = ["# Números do artigo", "", "Gerado por `tools/numeros.py` (`make numeros`). Origem: **nuvem** (pacote importado, commit congelado) ou **local** (verificação de funcionamento, marcado em vermelho no PDF).", "",
          "| Macro | Valor | Origem | Descrição | Arquivo |", "|---|---|---|---|---|"]
    counts = {"nuvem": 0, "local": 0, "ausente": 0}
    for name, (key, fn, desc) in CATALOG.items():
        f, origin, meta = locate(key)
        value = None
        if f:
            try:
                value = fn(json.loads(f.read_text()))
            except Exception as e:  # o resultado não tem o campo: o número fica TBD, com o motivo
                origin, why = "ausente", f"{type(e).__name__}: {e}"
        counts[origin] += 1
        rel = f.relative_to(REPO).as_posix() if f else key
        data = json.loads(f.read_text()) if f and origin != "ausente" else {}
        prov = (f"commit {meta['head']['commit'][:12]} em {meta['host']}" if meta
                else f"commit {str(data.get('git_commit', '?'))[:12]}" + (f", run {data['run_id']}" if data.get("run_id") else ""))
        tex.append(f"% {desc} · {rel} · {origin} · {prov}")
        body = "\\tbd" if value is None or origin == "ausente" else (tex_escape(value) if origin == "nuvem" else f"\\local{{{tex_escape(value)}}}")
        tex.append(f"\\newcommand{{\\num{name}}}{{{body}}}")
        md.append(f"| `\\num{name}` | {value if origin != 'ausente' else 'TBD'} | {origin} | {desc} | `{rel}` |")
    OUT_TEX.write_text("\n".join(tex) + "\n")
    OUT_MD.write_text("\n".join(md) + "\n")
    print(f"{len(CATALOG)} números: {counts['nuvem']} da nuvem, {counts['local']} locais (em vermelho), {counts['ausente']} TBD")
    print(f"→ {OUT_TEX.relative_to(REPO)} e {OUT_MD.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
