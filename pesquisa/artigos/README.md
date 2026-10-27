# Acervo de artigos: a base teórica

**Atualizado:** 2026-10-27 · **Decisão:** [D5](../../DSN2027/DECISOES.md) · **Motivos de cada
escolha:** [E12](../../DSN2027/etapas/E12_base_teorica.md) §2–§3.

Ficam aqui só os artigos que sustentam o trabalho, organizados por **camada** (quanto ler) e por
**tema** (que afirmação sustentam). Os 40 PDFs descartados na triagem de 2026-10-27 seguem no
histórico do git (commit `f0fba2a`). As notas de leitura citam cada PDF pelo nome do arquivo; use
este índice para achar a pasta.

## Camadas

| Pasta | Quanto ler | Artigos |
|---|---|---|
| `1_base/` | Corpo inteiro | 12 PDFs + Natella (sem PDF) |
| `2_vizinhos/` | Seções-chave | 5 |
| `3_citacao/` | Uma frase no texto | 16 |

## 1 · Base (pastas pelas afirmações A1–A5 da E12 §3)

| Pasta | Afirmação | Arquivos |
|---|---|---|
| `A1_derivacao/` | A recusa não sobrevive à derivação | `2024_qi_finetuning`, `2024_arditi_refusal`, `2025_lin_consiglieres` |
| `A2_defesas_nos_pesos/` | Proteger nos pesos não basta | `2025_qi_durability` |
| `A3_deteccao/` | Detectar só funciona sob custódia | `2026_hurtado_abliterated`, `2025_egler_auditing` |
| `A4_engano_do_portao/` | O derivado tenta enganar o portão | `2024_halawi_covert`, `2024_egashira_quantization`, `2025_nasr_attacker` |
| `A5_medida_valida/` | Medida válida e população representativa | `2024_souly_strongreject`, `2024_rottger_xstest`, `2024_mazeika_harmbench` |

**Falta baixar (A5):** Natella, Cotroneo, Durães, Madeira, *On Fault Representativeness of
Software Fault Injection*, IEEE TSE 39(1):80–96, 2013, DOI 10.1109/TSE.2011.124. Sem versão
aberta; baixar pelo acesso institucional como `A5_medida_valida/2013_natella_representativeness.pdf`.

## 2 · Vizinhos e extensões

| Pasta | Para quê | Arquivos |
|---|---|---|
| `custodia_atestacao/` | Diferenciar do recibo P2 e da arquitetura | `2025_schnabl_attestable`, `2025_spoczynski_atlas` |
| `bounty/` | Molde do bounty P4 | `2024_rando_backdoors` |
| `defesas_nos_pesos/` | Reforçar A2 e as sondas sem treino | `2026_casper_openweight`, `2026_kuo_defenses` |

## 3 · Só citação

| Pasta | Arquivos |
|---|---|
| `derivacao/` | `2025_wollschlager_geometry`, `2025_qi_shallow`, `2025_wallace_worstcase`, `2025_huang_virus`, `2026_10alabs_redistribution` |
| `defesas_nos_pesos/` | `2025_tamirisa_tar`, `2024_rosati_repnoise`, `2025_huang_antidote`, `2025_abushairah_abliteration` |
| `medida_valida/` | `2025_xie_sorrybench` |
| `custodia_atestacao/` | `2025_duddu_laminator`, `2025_anthropic_confidential`, `2024_google_aisupplychain`, `2026_jin_guardrail`, `2026_erfan_aibom` |
| `bounty/` | `2023_schulhoff_hackaprompt` |

Citado sem PDF: Waiwitlikhit et al., *Trustless Audits without Revealing Data or Models*
(ZkAudit, ICML 2024, arXiv 2404.04500), como alternativa sem TEE ao recibo P2.
