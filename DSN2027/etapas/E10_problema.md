# E10 · Definição do problema (proteção de modelos)

**Data:** 2026-10-27 · **Status:** **decidido em 2026-10-27** (§5).
**Base:** [DECISOES](../DECISOES.md) D1–D2, [E6](E6_alt_modelos_abertos.md),
[E8](E8_alinhamento_dsn.md) §9, [E9](E9_testes_validos.md), e os levantamentos de 2026-10-27:
- [MODELOS_DSN.md](../referencias/MODELOS_DSN.md): 96 trabalhos do DSN e do DSML de 2021–2026;
- [pesquisa/05](../../pesquisa/05_protecao_modelos.md): outras conferências, em seis eixos.

## 1. O que o orientador trouxe (2026-10-27)

- Proteção de modelos, do jeito proposto, já é proteção de **cadeia de suprimentos de modelos**.
- A ideia de bounty pode voltar: prêmio para quem mostrar uma entrada que explora o modelo.
- Falar em modelos, e não em mercado, aproxima o artigo do projeto.
- O formato de modelo resolve a exposição de código confidencial na saída, limitação do Juiz.

## 2. O que a literatura já resolve e o que sobra

| Pedaço do problema | Quem já faz | O que falta |
|---|---|---|
| A recusa se perde na derivação | Qi et al. (ICLR'24): fine-tuning nocivo **ou benigno** desfaz a segurança; Lin et al. 2025: **> 11 mil** modelos sem recusa nos hubs, um com > 19 milhões de downloads (arXiv 2508.12622 ✔) | Nada; é a motivação |
| Salvaguardas dentro dos pesos | TAR, RepNoise, Sophon (S&P'24) | Caem sob avaliação adaptativa (Qi et al. 2025); o LymphNode (DSN'26) supõe que ninguém escreve nos pesos |
| Detectar o derivado obliterado | Hurtado 2026 (AUROC 0,95); Egler et al. 2025 (56% a FPR 1%) | Hurtado depende de uma **referência que o atacante pode forjar**; nenhum é um sistema com contenção |
| Derivado que engana a avaliação | *Covert Malicious Finetuning* (ICML'24) | Precisa entrar no modelo de falhas |
| Avaliação atestada | Attestable Audits; Plinius e AnBridge (DSN) | Só modelo fixo, ou protegem o modelo **do host**, não **do usuário com os pesos** |
| Red teaming com prêmio | Competição de backdoors do SaTML 2024 (oráculo automático); desafios de jailbreak | Ninguém paga por quebrar um **portão de derivados** com verificação atestada |

**No DSN** ([MODELOS_DSN](../referencias/MODELOS_DSN.md)):
- Não há trabalho que trate pesos abertos e seus derivados como **cadeia de suprimentos**. O mais
  próximo é o ecossistema MCP (DSN'26), que é cadeia de suprimentos de ferramentas de LLM.
- Ninguém define "a recusa sobrevive à derivação" como propriedade de dependabilidade.
- O mais próximo em espírito é o DSML'26 sobre *unlearning* que não sobrevive à quantização: uma
  transformação do derivado desfaz uma propriedade de segurança (só o título foi lido).

## 3. Rascunho do enunciado (base: formulação P1)

> Plataformas que hospedam modelos de pesos abertos para uso e fine-tuning por terceiros formam
> uma **cadeia de suprimentos de modelos**. Nela, a propriedade de segurança do modelo — recusar
> pedidos nocivos — não sobrevive à derivação. Falhas acidentais (fine-tuning benigno) e maliciosas
> (dados nocivos, edição dos pesos, adaptação contra o detector) produzem derivados
> **comprometidos mas funcionais**, que hoje circulam aos milhares. As salvaguardas embutidas nos
> pesos não resistem a quem escreve neles, e os detectores dependem de uma referência que o
> atacante pode forjar.
>
> **Problema:** garantir que **nenhum derivado comprometido seja liberado** pela plataforma, com
> baixo falso alarme para quem faz fine-tuning legítimo e custo baixo por veredito, contra um
> adversário que controla o código e os dados de treino **dentro** do ambiente confidencial.

## 4. Formulações candidatas

| # | Formulação | Papel sugerido | Novo em relação à literatura |
|---|---|---|---|
| **P1** | **Integridade de segurança na cadeia de derivados:** todo derivado liberado mantém a recusa ≥ a do pai − δ, sob falhas F1–F4 | **Espinha do artigo** | Custódia (referência não forjável) + portão + contenção + revogação, avaliados com dados de campo e atacante adaptativo |
| P2 | **Liberação verificável:** um recibo atestado prova a quem não confia no operador que o derivado passou no portão | Componente da P1 | Recibo para **derivados**, não para modelo fixo |
| P3 | **Contenção de exportação:** nenhum byte de peso sai pela saída legítima do job | Seção curta | Pesos tratados como dataset pela saída do job |
| P4 | **Bounty como avaliação adaptativa contínua:** prêmio para quem produzir um derivado ou uma entrada que passe pelo portão e falhe na bateria secreta (ideia do orientador) | Extensão; desenho + piloto interno | Ninguém paga por quebrar um portão de derivados com verificação atestada |
| P5 | **Representatividade:** as falhas injetadas por nós se parecem com os derivados de campo? | Pergunta de pesquisa (RQ3 da E8 §9.3) | Ninguém compara injeção × campo para obliteração |

**Leitura:** só a P1 sustenta um artigo de DSN sozinha. As outras são componentes ou extensões dela.
A escolha real é quais delas entram junto da P1 e com que peso.

## 5. Decisão (2026-10-27)

| Ponto | Escolha |
|---|---|
| Espinha | **P1**: integridade de segurança na cadeia de derivados |
| Junto da P1 | **P5** (representatividade, como RQ), **P2** (recibo atestado, como componente) e **P4** (bounty, como desenho + piloto interno) |
| Fora | **P3** (exportação de pesos): limitação ou trabalho futuro |
| Propriedade | **Recusa + utilidade**: recusa ≥ a do pai − δ em pedidos nocivos, sem aumentar a recusa excessiva em pedidos seguros, e utilidade preservada no derivado legítimo |
| Adversário | **Usuário com os pesos** dentro da CVM: controla código e dados de treino e conhece o portão; o operador é confiável (D3) |
| Enquadramento | **Os dois**: cadeia de suprimentos de modelos na motivação; dependabilidade no mecanismo e nas métricas |

**Ordem de corte se o prazo apertar:** P4 vira só desenho → P2 vira só desenho. P1 e P5 não
são cortadas.
