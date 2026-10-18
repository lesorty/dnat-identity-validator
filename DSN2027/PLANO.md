# Plano DSN 2027 (Berlim)

**Criado:** 2026-10-18 (D-033) · **Rumo:** [ARTIGO.md](ARTIGO.md) · **Juiz:** [JUIZ_IA.md](JUIZ_IA.md) · **Artigo LaTeX:** [artigo/](artigo/)

## 0. Datas e regras ([CFP](https://dsn2027-berlin.github.io/call-for-contributions/))

| Data (AoE) | Marco |
|---|---|
| **25/nov/2026** | Resumo. **Título e autores não mudam depois** |
| **02/dez/2026** | Artigo |
| 26/jan/2027 | Rejeição antecipada |
| 12–26/fev/2027 | Rebuttal (750 palavras) e revisão (+1 página, ≤ 30% novo) |
| 18/mar/2027 | Notificação |

- **Regular paper: 11 páginas com tudo** (figuras e apêndices); só as referências ficam de fora. Passou, rejeição sem revisão.
- Template **IEEE Computer Society**, duas colunas; resumo ≤ 150 palavras; tipo do artigo na 1ª página.
- **Double-blind**: link do artefato anonimizado; autocitação em 3ª pessoa.
- Seção **"AI Tool Usage"** obrigatória se houver conteúdo gerado por IA (fora do limite de páginas).
- Artefato: declarar na submissão a intenção (código, dados ou ambos).
- Tópicos do CFP que nos cobrem: *AI/ML/LLM applications for security*, *agentic AI security, prompt injection*, *TEEs*.

## 1. Tese e contribuições

**Contribuição principal: o Juiz de IA** (D-032). Pergunta central: **um Juiz barato, com
evidências mecânicas, detecta vazamentos escondidos por atacantes caros?**

| # | Contribuição | Prova no artigo |
|---|---|---|
| C1 | Juiz em camadas (contrato, testes dinâmicos, LLM com evidências, portão de saída) contra vazamento pelo canal de saída | Batalha atacante × defensor |
| C2 | Juiz como aplicação do próprio sistema (whitelist, entrada = outra app) | Demonstração integrada no DNAT |
| C3 | Benchmark de apps com vazamento escondido (não existe hoje) | Artefato publicado |
| C4 | Execução de imagens OCI em CVM, container sem rede | Pré-requisito; custo medido |

## 2. Escopo do MVP

| Prioridade | Item |
|---|---|
| **Obrigatório** | Juiz: L0 (contrato + 2–3 tags), **L2** (canários, troca de um registro, cópia de linhas), **L3** (LLM com evidências), L4 (portão de saída) |
| **Obrigatório** | Benchmark: tarefas de processamento de dados, versões benignas e com vazamento, verdade de referência mecânica |
| **Obrigatório** | Batalha: atacantes × defensores; defensor com e sem evidências; detecção, falsos positivos, custo |
| **Obrigatório** | Executor OCI mínimo: `--network none`, rootfs somente leitura, sem capacidades, volume de saída; modo direto na CVM |
| **Obrigatório** | Juiz como app no DNAT: app-alvo como entrada, veredito registrado |
| Desejável | Build OCI em duas fases (E2b); L1 (taint para Python); rodada adaptativa; reamostragem (Ctrl-Z) |
| Desejável | Custo do executor OCI em CVM (reaproveitar as campanhas da branch `feat/cvm-direct-mode-deploy`) |
| **Fora** | Distribuição (D-031); atestação real (D-017 iii); Firecracker; U1 (pesos de modelo) só como motivação ou discussão |

## 3. Cronograma

| Semana | Implementação | Escrita |
|---|---|---|
| **S0** 18–19/out | Fechar escopo; limpar o repositório ✅; integrar a branch `feat/cvm-direct-mode-deploy` | Esqueleto LaTeX ✅ |
| **S1** 20–26/out | Especificar tarefas, canários e tags; executor OCI mínimo; escolher modelos e orçamento | Esqueleto no template IEEE |
| **S2** 27/out–02/nov | L2 + L4; gerador de apps (sementes + mutação pelos atacantes); versões benignas | Threat model, problema |
| **S3** 03–09/nov | L3 com evidências; rodador da batalha; **piloto**; Juiz como app no DNAT | Design |
| **S4** 10–16/nov | Batalha completa; ablação (com/sem evidência, por camada); custo | Implementação |
| **S5** 17–25/nov | Desejáveis, se der; congelar resultados | Avaliação, related work; **resumo em 25/nov** |
| **S6** 26/nov–02/dez | Só correções | Rascunho aos coautores até **28/nov**; corte de páginas; submissão em **02/dez** |

**Se apertar, cortar nesta ordem:** desejáveis → L4 → integração no DNAT (vira descrição) → número de modelos na batalha.
**Inegociáveis:** L2 + L3, benchmark, batalha com e sem evidências.

## 4. Riscos

| Risco | Mitigação |
|---|---|
| Guardrails dos atacantes | Sementes nossas + mutação; modelos abertos locais; taxa de recusa como resultado (JUIZ_IA §6.2) |
| Custo de API | Orçamento fixo por célula da matriz; modelos baratos no piloto |
| Não determinismo do LLM | Repetições por par; temperatura fixa; reportar variância |
| Prazo | Escrita em paralelo desde S1; piloto em S3 decide o tamanho da batalha |
| 11 páginas com tudo | Planejar figuras e tabelas cedo; sem apêndice |

## 5. Decisões pendentes

1. Quais modelos atacantes e defensores, e qual orçamento de API?
2. Há crédito na Azure para rodar em CVM?
3. Datas de revisão dos coautores.
4. U1 (pesos de modelo) aparece no artigo?
