# DSN 2027 — página de trabalho

Tudo o que está em andamento para o artigo do **DSN 2027 (Berlim)**: plano, rumo (proteção de
modelos abertos), decisões vigentes, etapas e o LaTeX.

| Prazo (AoE) | Marco |
|---|---|
| **25/nov/2026** | Resumo (título e autores congelam) |
| **02/dez/2026** | Artigo (11 páginas com tudo, IEEE CS, double-blind) |

## Onde está cada coisa

| Arquivo | O que é |
|---|---|
| [PLANO.md](PLANO.md) | Cronograma semana a semana, escopo do MVP, riscos |
| [ARTIGO.md](ARTIGO.md) | Tese, contribuições, escopo e o que muda em relação ao LADC |
| [DECISOES.md](DECISOES.md) | Só as decisões vigentes, por tema |
| [etapas/](etapas/) | Análises que embasam as decisões (tabela abaixo) |
| [referencias/](referencias/) | Artigos do DSN 2021–2026 (PDFs abertos), o [guia/glossário](referencias/GUIA_DSN.md) e a [classificação por tema](referencias/TEMAS_DSN.md) dos 393 aceitos |
| [../model_gate/](../model_gate/) | Código do Juiz (pacote Python): ambiente travado, base e datasets por digest, geração determinística, registro e medições |
| [backlog/](backlog/) | Retrato do quadro kanban (196 tasks) e das decisões; o quadro vivo fica no claude.ai |
| [artigo/](artigo/) | LaTeX do artigo (template IEEE, uma seção por arquivo); **ainda escrito para o Juiz, a reescrever** |

> **Rumo decidido (2026-10-27, com o orientador): proteção de modelos abertos** (DECISOES D1).
> Pesos e derivados sob custódia na CVM e portão de liberação contra obliteração. Problema
> definido na E10. O Juiz de código e o bug bounty sobre a cadeia de software foram descartados;
> o material deles está na tag git `archive/juiz-bounty-2026-10`, e o que o rumo atual herda do
> Juiz está na E11.

## Progresso (09/11)

| Épico | Estado |
|---|---|
| J1 Especificação | ✅ 14/14 tasks; E14 e D6 fechadas em 28/10 |
| J2 Fundação | 🔄 9/11 tasks (T-201 a T-208, T-211) em 05/11; faltam T-209 (CI) e T-210 (máquina de 4 vCPU) |
| J3–J16 | ⏳ não iniciados |
| J17 Identidade e cota | 🆕 1/9 tasks: decisão D7 e E14 §18 em 09/11 (sugestão do orientador); falta implementar e medir |

**Achado da T-208:** a geração de S1 não cabe nos 80 min por veredito com a bateria inteira
(5,6× acima, sem o avaliador). Só âncoras + XSTest dá 2,1×; a decisão está em aberto (E14 §6.2).
Os marcos G1 (01/11) e G0 (02/11) estão vencidos.

**Novo em 09/11 (D7):** além do Juiz, o sistema limita as tentativas de quem ataca. Cada papel age
por uma identidade cara de obter (prova de trabalho, como no Bitcoin) e cada identidade tem uma
cota que se gasta por veredito, cinco vezes mais rápido num reprovado. Identidade por provedor de
nuvem (AWS, Azure, Oracle, com cartão) fica como trabalho futuro. Ver a E14 §18.

## Etapas

| # | Etapa | Status | Documento |
|---|---|---|---|
| E1 | Auditoria do código | ✅ concluída; achados A1–A16 valem como retrato do código | [E1](etapas/E1_auditoria_codigo.md) |
| E2 | Isolamento confidencial por job | ✅ decidida; falta medir | [E2](etapas/E2_isolamento_confidencial.md) |
| E2b | Build seguro de imagens OCI | 🔄 rascunho; duas fases em duas CVMs; todo build atestado, sem imagem pronta | [E2b](etapas/E2b_build_oci.md) |
| E2c | Ameaças do build e da execução OCI (problemas → soluções; rede zero; Juiz e rede) | ✅ decidida; falta verificar no Azure | [E2c](etapas/E2c_ameacas_oci.md) |
| E4 | Juiz de IA para validação de código | ⛔ descartado; vira o portão de modelos (D2); herança na E11 | [tag](https://github.com/lesorty/dnat-identity-validator/blob/archive/juiz-bounty-2026-10/DSN2027/JUIZ_IA.md) |
| E5 | Alternativa A: mercado anônimo de bug bounty sobre a cadeia de suprimentos | ⛔ descartada; bounty vira extensão (C4) | [tag](https://github.com/lesorty/dnat-identity-validator/blob/archive/juiz-bounty-2026-10/DSN2027/etapas/E5_alt_bug_bounty.md) |
| E6 | Alternativa B: modelos abertos com guardrails por custódia | ✅ escolhida | [E6](etapas/E6_alt_modelos_abertos.md) |
| E7 | Decisão de rumo (matriz A × B + segunda opinião) | ✅ decidida: B (2026-10-27) | [E7](etapas/E7_decisao_rumo.md) |
| E8 | Alinhamento com o DSN (só teor da conferência; 307 artigos de 2021–2026 + 16 âncoras lidas) | ✅ B se alinha melhor, se vendido como dependabilidade | [E8](etapas/E8_alinhamento_dsn.md) |
| E9 | Desenho de testes válidos para A e B | 🔄 proposta | [E9](etapas/E9_testes_validos.md) |
| E10 | Definição do problema (proteção de modelos) | ✅ decidida: P1 + P5, P2, P4 | [E10](etapas/E10_problema.md) |
| E11 | Herança do Juiz de código (U1, ideias de portão, CTF, canários) | 📌 registro | [E11](etapas/E11_heranca_juiz.md) |
| E12 | Base teórica (A1–A5) | ✅ decidida (D5) | [E12](etapas/E12_base_teorica.md) |
| E13 | Plano de trabalho consolidado | 📌 plano; a E14 vale sobre ele | [E13](etapas/E13_plano_trabalho.md) |
| E14 | Especificação do Juiz (épico J1) | ✅ fechada (D6); geração única do S1 provisória, primeira medida na T-208; §18 identidade e cota (D7, 09/11) | [E14](etapas/E14_especificacao_juiz.md), [E14a](etapas/E14a_artigos_do_juiz.md) |

A E3 (descentralização) foi concluída e **descartada** com o orientador (D3). O histórico
completo, com o material do LADC 2026, está na tag git `ladc-2026`; o do Juiz de código e do bug
bounty (E4, E5 e os levantamentos `pesquisa/01` e `04`), na tag `archive/juiz-bounty-2026-10`.

## Convenções

- Uma ideia só vira decisão em [DECISOES.md](DECISOES.md) (D1–D7); manter poucas e relevantes.
- Afirmações sobre código citam `arquivo:linha`; sobre literatura, a fonte. O que não foi
  conferido leva **(a verificar)**.

## Compilar o artigo

```bash
cd DSN2027/artigo && latexmk -pdf main.tex
```
