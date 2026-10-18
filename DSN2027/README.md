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
| [artigo/](artigo/) | LaTeX do artigo (template IEEE, uma seção por arquivo) |

## Etapas

| # | Etapa | Status | Documento |
|---|---|---|---|
| E1 | Auditoria do código | ✅ concluída; achados A1–A16 valem como retrato do código | [E1](etapas/E1_auditoria_codigo.md) |
| E2 | Isolamento confidencial por job | ✅ decidida; falta medir | [E2](etapas/E2_isolamento_confidencial.md) |
| E2b | Build seguro de imagens OCI | 🔄 rascunho; duas fases em duas CVMs; imagem pronta aceita (nível 0 padrão) | [E2b](etapas/E2b_build_oci.md) |
| E2c | Ameaças do build e da execução OCI (problemas → soluções; rede zero; Juiz e rede) | ✅ decidida; falta verificar no Azure | [E2c](etapas/E2c_ameacas_oci.md) |
| E4 | **Juiz de IA** (contribuição principal) | 🔄 em desenho | [JUIZ_IA.md](JUIZ_IA.md) |

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
