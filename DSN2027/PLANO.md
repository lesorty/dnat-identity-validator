# Plano DSN 2027 (Berlim)

**Atualizado:** 2026-10-27 (rumo: proteção de modelos, D1) · **Rumo:** [ARTIGO.md](ARTIGO.md) ·
**Artigo LaTeX:** [artigo/](artigo/)

## 0. Datas e regras ([CFP](https://dsn2027-berlin.github.io/call-for-contributions/))

| Data (AoE) | Marco |
|---|---|
| **25/nov/2026** | Resumo. **Título e autores não mudam depois** |
| **02/dez/2026** | Artigo |
| 26/jan/2027 | Rejeição antecipada |
| 12–26/fev/2027 | Rebuttal (750 palavras) e revisão |
| 18/mar/2027 | Notificação |

- **Regular paper: 11 páginas com tudo**; só as referências ficam de fora.
- Template IEEE Computer Society; resumo ≤ 150 palavras; **double-blind**.
- Seções obrigatórias: **ética** (geramos modelos sem recusa) e **AI Tool Usage**.
- Artefato: declarar a intenção na submissão.

## 1. Cronograma

| Semana | Pesquisa e implementação | Escrita |
|---|---|---|
| **S1** 27/out–02/nov | Levantamento (DSN e externo); **definir o problema** ([E10](etapas/E10_problema.md)) até 29/out; **piloto** de 2–3 dias (E7 §7) até 01/nov; escopo do MVP fechado em 02/nov | Problema e modelo de ameaça |
| **S2** 03–09/nov | População F1–F3 em Qwen2.5-0.5B/1.5B; sinais do portão; verdade de referência independente; executor de modelos em modo direto na CVM | Introdução, modelo de falhas |
| **S3** 10–16/nov | F4 adaptativo; família não vista (ex.: Llama-3.2-1B); obliterados de campo como teste cego; derivado não exportável no contrato | Desenho |
| **S4** 17–25/nov | Campanha completa com ICs; custo na CVM; congelar resultados | Avaliação, related work; **resumo em 25/nov** |
| **S5** 26/nov–02/dez | Só correções | Rascunho aos coautores até **28/nov**; corte de páginas; submissão em **02/dez** |

**Se apertar, cortar nesta ordem:** bounty (C4) → contrato (derivado não exportável) → ponto
em 7–8B → extras do atacante adaptativo.
**Inegociáveis:** F1–F3, verdade de referência independente, família não vista, falso alarme em
fine-tuning benigno.

## 2. Riscos

| Risco | Mitigação |
|---|---|
| Revisor ler como "SaTML" | Escrever como dependabilidade, no molde de Multi-version ML, ReMlX e TPU-FI (E8 §9) |
| Portão não separar os casos | Piloto com critério de corte (E7 §7) antes de S2 |
| Veredito lento em CPU | Medir no piloto; corte se passar de 80 min |
| População construída por nós | Teste cego com obliterados públicos (E9 B4) |
| Ética | Modelos pequenos; não publicar pesos nem gerações nocivas |
| Rascunho LaTeX é do Juiz | Reescrever introdução, ameaça e avaliação desde S1 |

## 3. Decisões pendentes

1. O problema exato ([E10](etapas/E10_problema.md)).
2. Crédito na Azure para a CVM SEV-SNP.
3. Datas de revisão dos coautores.
