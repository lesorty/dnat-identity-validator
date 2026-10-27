# Proteção de modelos abertos: definição do problema (levantamento para o DSN 2027)

**Data:** 2026-10-27 · **Rumo decidido:** proteção de modelos abertos no DNAT (alternativa B,
[E6](../DSN2027/etapas/E6_alt_modelos_abertos.md), enquadramento *Safety by Custody* da
[E8 §9](../DSN2027/etapas/E8_alinhamento_dsn.md), testes da [E9](../DSN2027/etapas/E9_testes_validos.md)).
**Observação do orientador:** isto é **proteção de cadeia de suprimentos de modelos**; o bounty
pode voltar como "prêmio para quem mostrar uma entrada que explora o modelo".

**Objetivo deste arquivo:** fixar com precisão qual problema o artigo resolve. Não refaz
[02](02_transparencia_execucao_llm.md) e [03](03_confiabilidade_llm.md): confere o que importa,
completa as lacunas e organiza tudo pela pergunta "que problema cada trabalho define".

**Convenções.**
- ✔ = conferido na fonte primária **nesta rodada** (página do arXiv, anais, OpenAlex ou página
  oficial). ✔02 / ✔03 = conferido em rodada anterior, registrado em 02 ou 03 e não reaberto.
- **(a verificar)** = não conferido na fonte primária.
- "Problema" segue o molde *adversário ou falha → propriedade ameaçada → sistema*.
- Nada aqui descreve como executar ataques; os ataques aparecem só no nível do que o artigo mostra.

---

## 0. Resumo em cinco linhas

1. A **cadeia de suprimentos de modelos** já tem assinatura (OMS), linhagem (AI-BOM, CoSAI AIMM) e
   detecção de código malicioso na serialização. **Nada disso diz se o derivado ainda recusa.**
2. Defesas **nos pesos** contra fine-tuning nocivo (TAR, Vaccine, Booster, RepNoise, Antidote,
   Sophon) caem sob avaliação adaptativa; o consenso de 2025–26 é que não duram.
3. A **detecção de recusa removida** existe (Hurtado 2026, Egler et al. 2025, AMS), mas cada uma
   supõe algo que só um custodiante garante: referência autêntica, acesso ao pré e ao pós, e que o
   derivado ainda não saiu.
4. A **custódia** (fine-tuning hospedado, TEE, auditoria atestada) existe em pedaços, sem portão de
   liberação de derivados verificável por terceiros.
5. **Bounties e competições** já verificam "sucesso" por oráculo automático com conjunto privado;
   isso é exatamente o desenho que o bounty do DNAT precisa.

---

## 1. Cadeia de suprimentos de modelos

**Leitura do eixo:** o problema clássico é **integridade e autenticidade do artefato** (o arquivo
que chega é o que o publicador assinou, e carregá-lo não executa código). A propriedade
**comportamental** do artefato (segurança, recusa) fica fora de todas as especificações abertas.

| Trabalho | Venue | Problema que define (1 frase) | Solução | Avaliação | Relação conosco | |
|---|---|---|---|---|---|---|
| OpenSSF Model Signing (OMS) v1.0 + `sigstore/model-transparency` | Spec + software (v1.1.1, out/2025) | Um modelo baixado de um hub pode ter sido trocado ou adulterado no caminho, e o consumidor não tem como provar que é o que o publicador liberou | Manifesto de digests por arquivo, assinado com Sigstore (identidade OIDC) | Adoção (NVIDIA NGC assina tudo; Kaggle opcional; HF não verifica) | O digest OMS do base é a **referência custodiada** do portão; o veredito do portão é uma atestação à parte (issue #586) | ✔02 |
| CoSAI AIMM (Artifact Integrity Maturity Model) | Relatório (set/2026) | Organizações não têm escala para saber quanta garantia de integridade e linhagem um artefato de IA tem | Níveis L1 integridade, L2 linhagem, L3 atestações estruturadas + *admission gating* por política | Modelo de maturidade, sem experimento | **O DNAT é o L3** (atestação de infraestrutura SEV-SNP + motor de política = portão). Dá vocabulário de indústria ao artigo | ✔02 |
| SLSA para ML / in-toto | Spec | Não há `buildType` nem predicado para treino ou fine-tuning; a proveniência de um derivado não é padronizada | Propostas abertas (slsa#978, in-toto #575 `eval-result`) | — | Fine-tuning é "build"; o recibo do portão pode ser `eval-result` | ✔02 |
| SPDX 3 AI / CycloneDX ML-BOM | Spec | O consumidor não sabe de que pai e de que dados um modelo derivou | `AIPackage`, `pedigree`, `DESCENDANT_OF` | — | Linhagem do derivado no contrato (F2 da E6) | ✔02 |
| Model Cards (Mitchell et al.) | FAT* 2019 | Modelos são liberados sem documentação de uso pretendido e limites | Ficha padronizada de desempenho e uso | Exemplos | Antecessor do *property card* atestado (Laminator) | (a verificar) |
| Atlas (Spoczynski, Melara, Szyller, Intel) | Preprint 2025 | O ciclo de vida de ML não tem proveniência verificável de ponta a ponta | TDX + C2PA + log de transparência | 2 pipelines, < 8% de *overhead* (fine-tuning de BERT em CPU) | Vizinho arquitetural mais próximo; **sem portão de segurança nem liberação condicionada** | ✔02 |
| Laminator (Duddu et al.) | CODASPY 2025 | Afirmações sobre um modelo (treino, acurácia, *fairness*) não são verificáveis | SGX atesta *property cards* | < 2,1% de *overhead* | Formato do recibo do portão | ✔02 |
| Models Are Codes / MalHug (Zhao et al.) | ASE 2024 | Hubs de modelos distribuem código malicioso embutido em modelos e scripts de carga | Pipeline de detecção estática + dinâmica | 705 mil modelos: 91 modelos e 9 scripts maliciosos | Ingestão: o DNAT aceita só safetensors | ✔02 |
| PickleBall (Kellas et al.) | CCS 2025 | Carregar pickle executa código arbitrário e scanners não pegam | Política de carga derivada da biblioteca | 100% dos maliciosos rejeitados, 79,8% dos benignos aceitos | Idem; argumento para formato só-tensor | ✔02 |
| Unsupervised Model Tree Heritage Recovery (Horwitz, Shul, Hoshen) | ICLR 2025 | Em hubs com > 1 milhão de modelos, a linhagem pai→filho não é declarada | Recupera a árvore a partir dos pesos (árvore geradora mínima dirigida) | Árvores sintéticas e reais | Linhagem **inferida** é o que existe sem custódia; no DNAT ela é **registrada** | ✔ |
| REEF / Independence Tests / Model Provenance Testing | 2024–25 (REEF ICLR 2025, a verificar) | Não dá para saber se um modelo publicado deriva de outro | Testes por pesos, ativações ou caixa-preta | 90–95% de precisão (caixa-preta) | Complementam o registro de linhagem fora da plataforma | ✔02 parcial |
| **Consiglieres in the Shadow** (Lin, Li, Liao, Wang) | Preprint cs.CR, ago/2025 (venue a verificar) | Modelos abertos sem salvaguarda (*uncensored*), criados por fine-tuning, *merge* ou ablação, circulam nos hubs e abastecem aplicações criminosas | Grafo de conhecimento de modelos, dados e derivações + aprendizado em grafo | **> 11 mil** modelos sem censura; alguns com > 1 milhão de downloads, um com > 19 milhões | **Dado de campo da motivação**: a recusa se perde ao longo da cadeia de derivados, e isso é medido | ✔ |

**O que sobra para nós no eixo 1:** as especificações tratam integridade do *arquivo*, não a
preservação da *propriedade de segurança* ao longo da linhagem. Não achamos especificação ou
artigo que condicione a liberação de um derivado a uma checagem comportamental atestada.

---

## 2. Fine-tuning nocivo e defesas nos pesos

**Leitura do eixo:** o problema é **perda de alinhamento por modificação do modelo**. Os ataques
mostram que é barato; as defesas tentam tornar os pesos resistentes; a avaliação adaptativa mostra
que não resistem.

### 2.1 Ataques (definição do problema)

| Trabalho | Venue | Problema que define (1 frase) | Achado | Relação conosco | |
|---|---|---|---|---|---|
| Qi et al., *Fine-tuning Aligned LMs Compromises Safety* | ICLR 2024 (oral) | Quem pode ajustar um modelo alinhado desfaz a segurança, por intenção ou por acidente | Poucos exemplos nocivos bastam; dados benignos também degradam | Define F1 (acidental) e F2 (maliciosa) da E8 §9.2; portão precisa de **limiar**, não de "zero degradação" | ✔02 |
| Pelrine et al., *Exploiting Novel GPT-4 APIs* | Preprint 2023 (FAR.AI) | A API de fine-tuning de um modelo fechado é uma superfície que remove salvaguardas | Poucos exemplos nocivos ou ~100 benignos removeram proteções; os dados **não foram barrados** pela moderação | A moderação de dados de entrada falha; motiva julgar o **derivado** | ✔ (página do arXiv via busca) |
| Halawi et al., *Covert Malicious Finetuning* | ICML 2024 | Um adversário com fine-tuning caixa-preta pode compromissar o modelo **sem ser detectado** por inspeção de dados ou avaliação em texto claro | Cada exemplo parece inócuo; o modelo resultante obedece a pedidos codificados 99% das vezes | Ataque F4 obrigatório: a bateria do portão **não pode ser só em texto claro** | ✔ (abstract); venue ✔02 |
| Gong et al., *Safety Misalignment Against LLMs* | **NDSS 2025** | Falta medida comparável de quão frágil é o alinhamento sob *system prompt*, fine-tuning e edição de modelo | Arcabouço unificado; SFT é o mais forte; ataque por representação sem respostas nocivas (SSRA); defesa SSRD realinha | **Venue de segurança** que já trata "misalignment" como ameaça de sistema; base para a tabela de classes de falha | ✔ |
| Guan et al., *Benign Samples Matter!* | ICML 2025 | Dados benignos escolhidos degradam a segurança sem conteúdo nocivo visível | 100 amostras benignas atípicas bastam | Moderação de conteúdo não pega; reforça julgar o resultado | ✔02 |
| Kazdan et al., *No, of Course I Can!* | ICLR 2026 | Fine-tuning com dados inofensivos ensina recusar e depois atender | Funciona em APIs comerciais | A bateria lê a resposta inteira | ✔02 |
| Davies et al. (UK AISI), *Fundamental Limitations in Pointwise Defences* | Preprint 2025 | Defesas que olham exemplo a exemplo têm limite teórico | Ataques indetectáveis amostra a amostra | Limite para "inspecionar os dados de treino" | ✔02 |
| Murphy et al., *Jailbreak-Tuning* | EMNLP 2025 | Modelos de fronteira com fine-tuning viram "gêmeos malignos" | Vale para OpenAI, Google, Anthropic | Tratar todo derivado como suspeito até passar no portão | ✔02 |
| Betley et al., *Emergent Misalignment* | ICML 2025 | Fine-tuning estreito gera desalinhamento amplo | Código inseguro → desalinhamento geral | Bateria fora do domínio do fine-tuning | ✔02 |

### 2.2 Defesas nos pesos e o que as quebra

| Defesa | Venue | Problema que define | Solução | O que a quebra | |
|---|---|---|---|---|---|
| Vaccine (Huang, Hu, Liu) | NeurIPS 2024 | O alinhamento deriva sob fine-tuning nocivo ("deriva de embeddings") | Alinhamento ciente de perturbação | Avaliação adaptativa e configurações não testadas (Qi 2025a) (a verificar caso a caso) | ✔ (arXiv) |
| Booster (Huang et al.) | ICLR 2025 | Idem, na fase de alinhamento | Atenua a perturbação nociva | Idem | ✔ (OpenAlex); venue ✔02 |
| RepNoise (Rosati et al.) | NeurIPS 2024 | Representações nocivas continuam recuperáveis após o alinhamento | Ruído nas representações nocivas | Mudança de seed, LR ou template (Qi 2025a) | ✔ |
| TAR (Tamirisa et al.) | ICLR 2025 | Salvaguardas de modelos abertos caem com poucos passos de fine-tuning | Treino adversarial meta-aprendido contra *tampering* | Qi 2025a: quebra com configurações fora das testadas | ✔ (arXiv); venue ✔02 |
| Antidote (Huang et al.) | ICML 2025 | Defesas na fase de alinhamento ou de fine-tuning dependem de hiperparâmetros | Poda pós-fine-tuning de pesos nocivos | Depende de ver o derivado: **funciona num portão, não nos pesos liberados** | ✔ (arXiv); venue ✔02 |
| Sophon (Deng et al.) | **IEEE S&P 2024** | Um modelo aberto pode ser ajustado para tarefas indesejadas | Aprendizado "não ajustável" que restringe a transferência | Escopo em modelos menores; robustez a ataque adaptativo (a verificar) | ✔ (DOI) |
| Qi et al., *On Evaluating the Durability of Safeguards* | arXiv 2024 (ICLR 2025 segundo 02, a verificar) | Defesas "duráveis" parecem mais fortes do que são porque a avaliação é fraca | Estudos de caso de quebra | Mudar detalhes do ataque derruba RepNoise e TAR | ✔ (abstract) |
| Casper et al., *Open Technical Problems in Open-Weight Risk Management* | TMLR 2026 (venue a verificar) | Não há gestão técnica de risco confiável para pesos abertos | 16 problemas abertos | Salvaguardas caem em dezenas de passos | ✔02 |
| Yu, Ye, *Training-Free Tampering* | ICML 2026 WS | Defesas contra fine-tuning nocivo caem sem treino (*prefill*, ablação) | — | — | ✔02 |

**O que sobra para nós no eixo 2:** o consenso aponta para fora dos pesos. Antidote, Safe LoRA e
SafeMERGE pressupõem **alguém que veja o derivado antes de liberá-lo**. Esse alguém é o portão.

---

## 3. Remoção de recusa e sua detecção

| Trabalho | Venue | Problema que define (1 frase) | Solução | Avaliação | Relação conosco | |
|---|---|---|---|---|---|---|
| Arditi et al., *Refusal Is Mediated by a Single Direction* | NeurIPS 2024 | A recusa de modelos de chat é mecanisticamente frágil | Mostra que uma direção nas ativações media a recusa; removê-la tira a recusa | 13 modelos até 72B | Ataque F3 e **sinal S2** do portão | ✔02 |
| **Hurtado**, *Has This Checkpoint Been Abliterated? A Two-Signal Audit and Its Failure Map* | Preprint cs.CR, jul/2026 (v2 ago/2026) | Uma plataforma não sabe, antes de implantar, se um checkpoint aberto teve a recusa removida | Gap de recusa nas ativações + diff de pesos, z-soma | Registro de 273 checkpoints; 57 abliterações públicas × 37 benignos; **AUROC 0,95** (0,84 e 0,90 sozinhos); transferência: acurácia balanceada 0,89, FPR 0,11, 4 de 57 perdidas | Suposições explícitas: **referência atestada**; falhas: referência forjada (a mais grave) e treino *white-box* contra o limiar. "Triagem, não *tamper-proofing*" | ✔ |
| **Egler, Schulman, Carlini**, *Detecting Adversarial Fine-tuning with Auditing Agents* | Preprint cs.CR, out/2025 | Provedores de fine-tuning não detectam jobs adversariais, inclusive cifrados | Agente auditor com dados + modelo pré + modelo pós | 8 ataques, 5 benignos, > 1.400 auditorias; **56,2% de detecção a 1% de FPR** | Linha de base realista; supõe acesso a pré e pós, que o custodiante tem | ✔ |
| Messenger, AMS | IEEE Access 2026 | Modificação do treino de segurança é invisível a quem só vê o checkpoint | Geometria das ativações | Detecta abliteração; fine-tuning puramente comportamental escapa | Limite de S2; S1 (comportamental) é obrigatório | ✔03 |
| Wang et al. (OpenAI), *Persona Features Control Emergent Misalignment* | ICLR 2026 | O desalinhamento de um derivado não aparece no domínio do fine-tuning | *Model diffing* com SAE acha uma *feature* preditiva | — | Sinal opcional em ativações | ✔02 |
| Agnihotri et al., *Granular Study of Safety Pretraining under Model Abliteration* | NeurIPS 2025 WS (Lock-LLM) | Não se sabe quais intervenções de pré-treino sobrevivem à abliteração | Mapa por checkpoint; efeito do juiz | SmolLM2-1.7B | Mostra que a escolha do juiz muda o resultado | ✔ (página do workshop) |
| Abu Shairah et al. / Kuo et al. | Preprints 2025–26 | Defesas do dono contra abliteração e sua fragilidade | Recusas longas; avaliações com *prefill* | Abliteração e *prefill* elevam ASR | Recomendação ao dono; avaliação inclui *prefill* | ✔02 |

**O que sobra para nós no eixo 3:** os detectores existem e têm desempenho conhecido. O que falta
é o **sistema** que satisfaz as suposições deles (referência autêntica, acesso pré e pós, derivado
retido até o veredito) e uma avaliação contra o atacante que conhece o portão.

---

## 4. Fine-tuning hospedado, custódia e controle de exportação

| Trabalho | Venue | Problema que define (1 frase) | Solução | Avaliação | Relação conosco | |
|---|---|---|---|---|---|---|
| Moderação de fine-tuning da OpenAI | Produto (docs; relatos em Pelrine 2023 e Halawi 2024) | O provedor precisa impedir que clientes produzam derivados nocivos via API | Moderação dos dados + avaliação do derivado antes de liberar | Não publicada; contornada por CMFT e dados benignos | **Mesmo serviço, sem verificabilidade por terceiros** | (a verificar: documentação oficial não aberta) |
| Thinking Machines, *A Safe Path to Open Weights* | Blog, jul/2026 | "Recusa não é salvaguarda durável" para pesos abertos | Escalonamento API → GA monitorado → **fine-tuning hospedado com monitoramento e revogação** → pesos | — | O DNAT é o degrau 3 com atestação | ✔02 |
| Wallace et al. (OpenAI), *Worst-Case Frontier Risks of Open-Weight LLMs* | ICLR 2026 | Como decidir se um modelo aberto pode ser lançado se o adversário vai ajustá-lo | Fine-tuning malicioso (MFT) como teste de pior caso | gpt-oss | O portão pode usar MFT curto como sonda | ✔02 |
| **Schnabl et al.**, *Attestable Audits* | Workshop TAIG no ICML (arXiv diz "ICML 2024"; ano a verificar) | Resultados de benchmarks de segurança não são verificáveis e expõem pesos ou dados | Benchmark roda em TEE e o resultado sai atestado, com hash do modelo | Protótipo com Llama-3.1 | Vizinho mais próximo do "portão atestado"; **audita modelo fixo, não derivados** | ✔ |
| Chrapek et al., *Confidential LLM Inference: CPU vs GPU TEEs* | Preprint 2025 | Custo da inferência confidencial | Medição TDX/SGX × GPU CC | < 10% de vazão em CPU TEE (Llama2-7B) | Viabilidade do portão em CVM sem GPU | ✔03 |
| ObfuscaTune (Frikha et al.) | AAAI 2025 WS (PPAI) | Fine-tuning de LLM proprietário em nuvem não confiável expõe modelo e dados | Ofuscação + ~5% dos parâmetros em TEE | GPT-2, 4 datasets | Protege **sigilo** dos pesos, não a **recusa** do derivado | ✔ |
| DistilLock (Mohanty et al.) | Preprint cs.CR, out/2025 (NeurIPS 2025 em E6, **não confirmado**: o arXiv não traz venue) | Fine-tuning na borda expõe o modelo a destilação e roubo | Professor em TEE + pesos ofuscados em acelerador | Sem métricas no abstract | Idem: sigilo, não segurança do derivado | ✔ |
| **Rinberg et al.**, *Verifying LLM Inference to Detect Model Weight Exfiltration* | Preprint cs.CR, nov/2025 (v3 mar/2026) | Um servidor de inferência comprometido pode exfiltrar pesos escondidos nas respostas | Jogo de segurança + verificação da aleatoriedade legítima da inferência | 3B–30B; no MoE-Qwen-30B, informação exfiltrável < 0,5% com FPR < 0,01% (> 200× de lentidão) | **Formaliza o nosso G2** (nenhum peso sai pela saída legítima); modelo para o portão de saída (C3) | ✔ |
| Nevo et al. (RAND), *Securing AI Model Weights* | Relatório RAND 2024 (DOI 10.7249/RRA2849-1) | Pesos de fronteira são alvo de roubo por atores de vários níveis | Níveis de segurança SL1–SL5 e vetores de ataque | Análise | Situa o DNAT num nível (sem proteção física: nível baixo) | ✔ (OpenAlex; texto a verificar) |
| AFTUNE / VeriLoRA / Verifiable FT com ZK | Preprint 2026 / NDSS 2026 / preprint 2025 | O fine-tuning declarado pode não ter sido o executado | Auditoria amostral em TEE; prova ZK de passos LoRA | 11–36% de *overhead*; ZK 122–249 s por passo | Prova o *processo*; não diz nada sobre a *recusa* do resultado | ✔02 |
| Anthropic, defesas contra destilação | Relatórios fev e out/2026 | Concorrentes copiam capacidade por consultas em massa | Classificadores e banimento | 90–99% menos dados colhidos | Limite declarado de G2: destilação passa pela inferência | ✔02 |

**O que sobra para nós no eixo 4:** os trabalhos de TEE protegem o **sigilo** do modelo ou a
**integridade da execução**; a moderação comercial protege a **segurança do derivado** mas não é
verificável. Ninguém junta as duas: segurança do derivado **verificável por quem não confia no
operador**.

---

## 5. Recompensas e red teaming verificável

**Leitura do eixo:** em toda competição séria o "sucesso" é decidido por um **oráculo** (string
exata, segredo extraído, modelo de recompensa ou juiz) sobre um **conjunto privado**. Os bounties
de laboratório usam rubrica com revisão humana e convite com NDA.

| Programa / trabalho | Venue | Problema que define | Como o sucesso é verificado | Escala | Relação conosco | |
|---|---|---|---|---|---|---|
| HackAPrompt (Schulhoff et al.) | EMNLP 2023 | Não há dados em escala de como humanos fazem *prompt injection* | Oráculo mecânico por saída-alvo exata em cada nível (a verificar o detalhe) | Competição global; dataset aberto | Verificação mecânica = o que o contrato pode checar | ✔ (venue) |
| **Rando et al.**, *Competition Report: Finding Universal Jailbreak Backdoors in Aligned LLMs* | Relatório da competição do IEEE SaTML 2024 | Alinhamento envenenado pode esconder um gatilho universal que desliga a recusa | Gatilho anexado a **2.300 perguntas privadas**; nota = recompensa média de um **modelo de recompensa** treinado com dados limpos, em 5 modelos | 12 submissões válidas; US$ 7 mil + *compute*; só uma equipe superou o gatilho injetado em um modelo | **Precedente direto do bounty**: "prêmio para quem mostrar uma entrada que explora o modelo", com oráculo automático e conjunto privado | ✔ |
| Debenedetti et al., *SaTML 2024 LLM CTF* | NeurIPS 2024 D&B segundo 03 (a verificar) | Defesas de *prompt injection* não têm avaliação adaptativa em escala | Extrair um segredo do *system prompt*: verificação mecânica | Dataset de ataques e defesas | Formato CTF da JUIZ §9.2 | ✔ (metadados) |
| Toyer et al., *Tensor Trust* | ICLR 2024 (a verificar) | Idem, com jogo online | Senha de acesso | > 100 mil ataques | Idem | (a verificar) |
| Zou et al. (Gray Swan + UK AISI), *Security Challenges in AI Agent Deployment* | Preprint 2025 | Agentes implantados violam políticas sob *prompt injection* | Juiz + critérios por cenário (detalhe a verificar) | 22 agentes, 44 cenários, 1,8 M de ataques, > 60 mil sucessos; quase todos violam em 10–100 consultas | Escala e taxa de sucesso; prova que a verificação por juiz escala | ✔ (abstract) |
| Sharma et al. (Anthropic), *Constitutional Classifiers* | Preprint 2025 | Salvaguardas contra *jailbreak* universal precisam resistir a red teaming humano prolongado | "Universal" = extrair, na maioria das perguntas-alvo, detalhe comparável ao modelo sem guarda; > 3.000 h de red teaming | Nenhum *jailbreak* universal no protótipo; +0,38% de recusas; +23,7% de *overhead* | Define "sucesso" por **comparação com o modelo sem proteção** = o nosso δ; número de participantes e prêmios **a verificar** | ✔ (abstract) |
| Anthropic Model Safety Bug Bounty; OpenAI Bio Bug Bounty; HackAPrompt 2.0; Gray Swan Arena | Programas 2024–26 | Laboratórios pagam por *jailbreaks* universais em domínios críticos | Rubrica + revisão humana, convite e NDA | Até US$ 15 mil (Anthropic ✔E6); demais a verificar | Diferença do DNAT: alvo é o **portão de um modelo aberto** e a verificação é atestada | E6 |

**O que sobra para nós no eixo 5:** nenhum programa paga pela **quebra de um portão de liberação de
derivados**, e nenhum tem verificação atestada por TEE e pagamento automático. O relatório do SaTML
2024 dá o molde exato do oráculo (modelo de recompensa ou juiz fixo, conjunto privado, nota média).

---

## 6. Metodologia de avaliação

| Trabalho | Venue | Problema que define | O que dá ao portão | |
|---|---|---|---|---|
| StrongREJECT (Souly et al.) | NeurIPS 2024 (D&B) | Avaliadores de *jailbreak* superestimam o sucesso (respostas vazias contam como sucesso) | Juiz pequeno que pontua **utilidade da resposta nociva**, não só ausência de recusa | ✔03 |
| HarmBench (Mazeika et al.) | ICML 2024 | Não havia avaliação padronizada de red teaming automatizado | Comportamentos e classificador padrão | ✔03 |
| SORRY-Bench (Xie et al.) | ICLR 2025 | Bancos de recusa são desbalanceados e caros de julgar | 44 categorias; juiz 7B local | ✔ (OpenAlex) / ✔03 |
| XSTest (Röttger et al.) | NAACL 2024 | Modelos recusam pedidos seguros parecidos com nocivos | Mede **recusa excessiva** (FPR do lado do usuário) | ✔02 |
| OR-Bench (Cui et al.) | arXiv 2024 (ICML 2025, a verificar) | Recusa excessiva em escala | 80 mil prompts "aparentemente nocivos" | ✔ (OpenAlex, só arXiv) |
| JailbreakBench (Chao et al.) | NeurIPS 2024 D&B | Avaliações de *jailbreak* não são reprodutíveis | Artefatos e juiz fixos | ✔03 |
| Eiras et al., *Know Thy Judge* | ICLR 2025 WS (ICBINB) | Juízes de segurança não são robustos | Estilo da saída muda o FNR em até 0,24; ataques fazem juízes rotularem 100% do nocivo como seguro | ✔ |
| Nasr, Carlini, Tramèr et al., *The Attacker Moves Second* | Preprint 2025 | Defesas avaliadas com ataques estáticos parecem robustas e não são | 12 defesas quebradas com ataques adaptativos (ASR > 90% na maioria) | ✔ (metadados) / ✔03 |
| Qi et al. 2025a (durabilidade) | ver §2.2 | Idem para defesas nos pesos | Protocolo: pior caso sobre configurações | ✔ |
| Needham et al., *LLMs Often Know When They Are Being Evaluated* | Preprint 2025 | Modelos se comportam diferente quando percebem avaliação | Bateria parcialmente secreta e realista | ✔02 |
| Miller, *Adding Error Bars to Evals* | Preprint 2024 | Avaliações de LLM sem intervalo de confiança | IC e tamanho de amostra | ✔03 |

**Implicações diretas:** (i) o rótulo de verdade precisa de um juiz **diferente** do usado no portão
(Know Thy Judge; E9 B3); (ii) a FPR do portão se mede com XSTest/OR-Bench e com fine-tuning benigno;
(iii) a avaliação principal é **adaptativa** (Attacker Moves Second; Qi 2025a) e inclui CMFT.

---

## 7. Formulações candidatas do problema

Cada formulação tem: frase, propriedade, adversário/falhas, o que seria novo, quem já resolve parte
e lacuna. A E8 §9 já escolheu o molde DSN (serviço + propriedade + modelo de falhas); as
formulações abaixo variam **o que é o objeto protegido**.

### P1. Integridade de segurança na cadeia de derivados (recomendada como espinha)

- **Frase:** numa plataforma que hospeda modelos abertos e produz derivados, garantir que **nenhum
  derivado liberado tenha recusa abaixo da do pai menos δ**, mesmo com script de treino arbitrário
  e atacante que conhece o portão.
- **Propriedade:** *safety integrity* do derivado; métrica-título = taxa de **liberação silenciosa**.
- **Falhas/adversário:** F1 acidental (dados benignos), F2 dados nocivos (incl. CMFT), F3 edição de
  pesos, F4 adaptativo; usuário *white-box* dentro do container; operador confiável.
- **Novo:** o portão como ponto de controle de **supply chain** (L3 do AIMM com *admission gating*
  comportamental), e a prova de que custódia elimina a falha mais grave de Hurtado (referência
  forjada) e satisfaz as suposições de Egler (pré + pós).
- **Já resolvem parte:** Hurtado (detector), Egler (auditor), OpenAI (moderação fechada), Thinking
  Machines (proposta), CoSAI AIMM (vocabulário).
- **Lacuna:** ninguém avalia o **sistema** (custódia + portão + contenção + revogação) contra
  falhas acidentais e maliciosas juntas, com dados de campo (os > 11 mil derivados de Lin et al.
  mostram que a falha existe na cadeia aberta).

### P2. Liberação verificável por quem não confia no operador

- **Frase:** permitir que o dono do modelo e terceiros **verifiquem** que todo derivado liberado
  passou pelo portão certo contra a referência certa, sem ver pesos nem bateria secreta.
- **Propriedade:** verificabilidade (atestação + log de transparência) da decisão de liberação.
- **Adversário:** operador ou usuário que tenta liberar derivado sem portão, trocar a referência ou
  esconder tentativas reprovadas (*split view*).
- **Novo:** recibo atestado (SEV-SNP `REPORT_DATA`) ligando digest OMS do pai, digest do derivado,
  hash do portão e veredito, num log.
- **Já resolvem parte:** Attestable Audits (modelo fixo), Laminator (*property cards*), Atlas
  (proveniência), Tinfoil/Apple PCC (medição + log).
- **Lacuna:** nenhum trata **derivados** nem liberação condicionada. Risco: sozinho, é
  integração; serve como componente de P1, não como artigo.

### P3. Contenção de exportação: pesos e derivados só saem como comportamento

- **Frase:** garantir que, com script arbitrário e acesso *white-box* dentro da CVM, nenhum peso do
  base ou do derivado saia pela única saída legítima em forma recuperável.
- **Propriedade:** confidencialidade dos pesos (G2 da E6).
- **Adversário:** script que codifica pesos, LoRA ou versões quantizadas na saída; destilação por
  consultas fica declarada como limite.
- **Novo:** canários nos pesos com variação entre execuções (JUIZ §9.4) aplicados a jobs de treino.
- **Já resolvem parte:** Rinberg et al. (exfiltração por inferência, com jogo formal), ObfuscaTune e
  DistilLock (sigilo via TEE), RAND (níveis), Anthropic (destilação).
- **Lacuna:** exfiltração pela saída de **jobs de treino arbitrários**; mas a destilação limita a
  garantia e o tema puxa para segurança clássica, não para o DSN. Melhor como seção de C3.

### P4. Portão sob ataque adaptativo, com prêmio (bounty) como avaliação contínua

- **Frase:** medir e manter a taxa de escape do portão quando atacantes motivados podem tentar
  repetidamente, pagando automaticamente quem mostrar um derivado (ou entrada) que passa no portão e
  falha num oráculo secreto.
- **Propriedade:** robustez do portão ao longo do tempo; P(escape) = 1 − (1 − e)^k (E8 §9.3).
- **Adversário:** caçador com orçamento de tentativas; plataforma com registro de tentativas.
- **Novo:** bounty para **portão de modelo aberto** com verificação atestada e pagamento em contrato;
  oráculo no molde do SaTML 2024 (modelo de recompensa/juiz fixo + conjunto privado).
- **Já resolvem parte:** Rando et al. (competição de backdoor com oráculo), Constitutional
  Classifiers (red teaming humano em escala), Gray Swan (escala), bounties de laboratórios.
- **Lacuna:** nenhum dá verificação automática atestada nem alvo "portão de derivados". Sem
  participantes reais até dez/2026, só entra como **desenho + piloto interno**.

### P5. Representatividade: o injetor de falhas reproduz o campo?

- **Frase:** a população de derivados que construímos (F1–F4) reproduz a distribuição de sinais
  dos derivados sem recusa encontrados no campo (HF)?
- **Propriedade:** validade do método de avaliação de portões de segurança.
- **Novo:** a pergunta do TPU-FI (DSN'26) aplicada a segurança de LLMs, usando os obliterados
  públicos como teste cego.
- **Já resolvem parte:** Hurtado (registro com 57 abliterações públicas), Lin et al. (catálogo de
  > 11 mil sem censura).
- **Lacuna:** ninguém compara injeção × campo. É **contribuição metodológica secundária** (RQ3 da
  E8), não o problema principal.

**Recomendação de recorte:** P1 como problema, com P2 como mecanismo de confiança, P5 como RQ de
validade e P3/P4 como seções curtas (C3 e desenho do bounty). Frase-problema sugerida para a
introdução:

> *Open-weight model supply chains propagate derivatives whose refusal behaviour silently degrades,
> accidentally or adversarially; existing integrity controls (signing, lineage) attest the artifact
> but not its safety, and existing detectors assume an authentic reference and pre-release access
> that only a custodian can provide.*

---

## 8. Lacunas deste levantamento

- **Venues a confirmar:** Qi 2025a (ICLR 2025?), Attestable Audits (ano do workshop), DistilLock
  (sem venue no arXiv; a E6 dizia NeurIPS 2025), Casper et al. (TMLR), OR-Bench (ICML 2025?),
  SaTML CTF (NeurIPS D&B?), Tensor Trust, Consiglieres (cs.CR, sem venue).
- **Não aberto:** documentação oficial da moderação de fine-tuning da OpenAI; texto completo do
  RAND; regras e verificação do HackAPrompt 2.0 e da Gray Swan Arena (página 404/429); número de
  participantes e prêmios do desafio dos Constitutional Classifiers (o HTML não pôde ser lido nesta
  rodada).
- **Não buscado a fundo:** SoK de cadeia de suprimentos de modelos em S&P/USENIX/CCS (busca não
  achou; vale procurar nos programas de 2025–26); trabalhos 2026 sobre "certificação" de
  derivados (busca não achou além de Hurtado); Sophon contra ataque adaptativo; Virus (moderação
  contornada) e SafeGene (vetores de segurança, 2026) **a verificar**.
- **Novidade:** nada aqui prova novidade; só registra que não achamos o vizinho que junta custódia +
  portão de derivados + verificabilidade + avaliação adaptativa.

---

## Fontes abertas nesta rodada

- [arXiv 2607.01854 Hurtado](https://arxiv.org/abs/2607.01854) · [arXiv 2510.16255 Egler et al.](https://arxiv.org/abs/2510.16255)
- [arXiv 2508.12622 Lin et al.](https://arxiv.org/abs/2508.12622) · [arXiv 2405.18432 Horwitz et al.](https://arxiv.org/abs/2405.18432)
- [NDSS 2025 Gong et al.](https://www.ndss-symposium.org/ndss-paper/safety-misalignment-against-large-language-models/) · [Sophon DOI](https://doi.org/10.1109/sp54263.2024.00234)
- [arXiv 2412.07097 Qi et al.](https://arxiv.org/abs/2412.07097) · [arXiv 2406.20053 Halawi et al.](https://arxiv.org/abs/2406.20053) · [arXiv 2312.14302 Pelrine et al.](https://arxiv.org/abs/2312.14302)
- [arXiv 2402.01109 Vaccine](https://arxiv.org/abs/2402.01109) · [arXiv 2408.09600 Antidote](https://arxiv.org/abs/2408.09600) · [arXiv 2408.00761 TAR](https://arxiv.org/abs/2408.00761) · [RepNoise DOI](https://doi.org/10.52202/079017-0402) · [Booster arXiv 2409.01586](https://arxiv.org/abs/2409.01586)
- [arXiv 2506.23706 Attestable Audits](https://arxiv.org/abs/2506.23706) · [arXiv 2407.02960 ObfuscaTune](https://arxiv.org/abs/2407.02960) · [arXiv 2510.16716 DistilLock](https://arxiv.org/abs/2510.16716) · [arXiv 2511.02620 Rinberg et al.](https://arxiv.org/abs/2511.02620) · [RAND DOI](https://doi.org/10.7249/rra2849-1)
- [arXiv 2404.14461 Rando et al.](https://arxiv.org/html/2404.14461v2) · [arXiv 2507.20526 Zou et al.](https://arxiv.org/abs/2507.20526) · [arXiv 2501.18837 Sharma et al.](https://arxiv.org/abs/2501.18837) · [HackAPrompt DOI](https://doi.org/10.18653/v1/2023.emnlp-main.302) · [arXiv 2406.07954 SaTML CTF](https://arxiv.org/abs/2406.07954)
- [arXiv 2503.04474 Know Thy Judge](https://arxiv.org/abs/2503.04474) · [arXiv 2510.09023 Attacker Moves Second](https://arxiv.org/abs/2510.09023) · [OR-Bench arXiv 2405.20947](https://arxiv.org/abs/2405.20947) · [NeurIPS 2025 WS Agnihotri et al.](https://neurips.cc/virtual/2025/128593)
