# DSN 2027 — página de trabalho

Tudo o que está em andamento para o artigo do **DSN 2027 (Berlim)**: plano, rumo, Juiz de IA,
decisões vigentes, etapas e o LaTeX.

| Prazo (AoE) | Marco |
|---|---|
| **25/nov/2026** | Resumo (título e autores congelam) |
| **02/dez/2026** | Artigo (11 páginas com tudo, IEEE CS, double-blind) |

## Onde está cada coisa

| Arquivo | O que é |
|---|---|
| [PLANO.md](PLANO.md) | Cronograma semana a semana, escopo do MVP, riscos |
| [ARTIGO.md](ARTIGO.md) | Tese, contribuições, escopo e o que muda em relação ao LADC |
| [JUIZ_IA.md](JUIZ_IA.md) | **Documento central do Juiz**: casos de uso, tags, problemas, abordagens, pesquisa, testes |
| [DECISOES.md](DECISOES.md) | Só as decisões vigentes, por tema |
| [etapas/](etapas/) | Análises que embasam as decisões (tabela abaixo) |
| [referencias/](referencias/) | Artigos do DSN 2021–2026 (PDFs abertos), o [guia/glossário](referencias/GUIA_DSN.md) e a [classificação por tema](referencias/TEMAS_DSN.md) dos 393 aceitos |
| [artigo/](artigo/) | LaTeX do artigo (template IEEE, uma seção por arquivo) |

> **Rumo em reavaliação (2026-10-26).** O Juiz como avaliador geral de vazamento foi julgado amplo
> demais. Estão em comparação a alternativa A (bug bounty sobre a cadeia de suprimentos, E5) e a B
> (modelos abertos com guardrails, E6). A decisão sai na E7; até lá D1–D4 seguem valendo.

## Etapas

| # | Etapa | Status | Documento |
|---|---|---|---|
| E1 | Auditoria do código | ✅ concluída; achados A1–A16 valem como retrato do código | [E1](etapas/E1_auditoria_codigo.md) |
| E2 | Isolamento confidencial por job | ✅ decidida; falta medir | [E2](etapas/E2_isolamento_confidencial.md) |
| E2b | Build seguro de imagens OCI | 🔄 rascunho; duas fases em duas CVMs; todo build atestado, sem imagem pronta | [E2b](etapas/E2b_build_oci.md) |
| E2c | Ameaças do build e da execução OCI (problemas → soluções; rede zero; Juiz e rede) | ✅ decidida; falta verificar no Azure | [E2c](etapas/E2c_ameacas_oci.md) |
| E4 | **Juiz de IA** (contribuição principal) | 🔄 em desenho; rumo em reavaliação | [JUIZ_IA.md](JUIZ_IA.md) |
| E5 | Alternativa A: mercado anônimo de bug bounty sobre a cadeia de suprimentos | 🔄 coleta concluída | [E5](etapas/E5_alt_bug_bounty.md) |
| E6 | Alternativa B: modelos abertos com guardrails por custódia | 🔄 coleta concluída | [E6](etapas/E6_alt_modelos_abertos.md) |
| E7 | Decisão de rumo (matriz A × B + segunda opinião) | 🔄 proposta: B com condições, depende do piloto de 27–29/out | [E7](etapas/E7_decisao_rumo.md) |
| E8 | Alinhamento com o DSN (só teor da conferência; 307 artigos de 2021–2026 + 16 âncoras lidas) | ✅ B se alinha melhor, se vendido como dependabilidade | [E8](etapas/E8_alinhamento_dsn.md) |

A E3 (descentralização) foi concluída e **descartada** com o orientador (D3). O histórico
completo, com o material do LADC 2026, está na tag git `ladc-2026`.

## Convenções

- Uma ideia só vira decisão em [DECISOES.md](DECISOES.md) (D1–D4); manter poucas e relevantes.
- Afirmações sobre código citam `arquivo:linha`; sobre literatura, a fonte. O que não foi
  conferido leva **(a verificar)**.

## Compilar o artigo

```bash
cd DSN2027/artigo && latexmk -pdf main.tex
```
