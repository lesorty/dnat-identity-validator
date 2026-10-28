# Plano DSN 2027 (Berlim)

**Atualizado:** 2026-10-27 (rumo: proteção de modelos, D1; plano na [E13](etapas/E13_plano_trabalho.md)) · **Rumo:** [ARTIGO.md](ARTIGO.md) ·
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

O plano de trabalho completo (frentes, critérios de aceite, marcos e recursos) está na
[E13](etapas/E13_plano_trabalho.md). Resumo:

| Semana | Marco |
|---|---|
| **S1** 28/out–02/nov | Piloto; **G1 em 01/nov** (algum sinal separa e o veredito cabe em 80 min) |
| **S2** 03–09/nov | População F1–F3, verdade de referência, contrato; **G2 em 09/nov** (pré-registro commitado) |
| **S3** 10–16/nov | Adaptativo (bounty interno), família não vista, campo; **G3 em 16/nov** (integração) |
| **S4** 17–25/nov | Campanha com IC; **G4 em 23/nov** (congelar); **resumo em 25/nov** |
| **S5** 26/nov–02/dez | Rascunho aos coautores em 28/nov; submissão em **02/dez** |

**Se apertar, cortar nesta ordem:** bounty vira só desenho → recibo vira log assinado pela CVM1 → contrato do
derivado não exportável → segunda família em escala menor → extras do adaptativo.
**Inegociáveis:** F1–F3, verdade de referência independente, falso alarme em fine-tuning benigno,
teste cego de campo e um atacante adaptativo mínimo.

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

Lista completa na [E13](etapas/E13_plano_trabalho.md) §8:
1. Máquinas para a campanha.
2. Juiz da verdade de referência (modelo aberto maior ou API externa).
3. Família não vista.
4. Nuvem e crédito para as CVMs (Azure, AWS ou Oracle, pelo custo; T-102).
5. Anotadores da amostra humana e datas de revisão dos coautores.
6. Bounty interno como formato da RQ4.
