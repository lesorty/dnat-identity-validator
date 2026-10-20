# Confiabilidade de LLMs e de aplicações com LLM: arcabouço de leitura

**Data:** 2026-10-20 · **Formato:** um paper por linha, com a contribuição em uma frase. ✔ quer
dizer que a referência foi conferida na página primária. [$] marca o que dá para aplicar barato,
sem GPU nem treino. Os detalhes que interessam ao Juiz e à linha de LLMs estão em
[01](01_juiz_seguranca_apps.md) e [02](02_transparencia_execucao_llm.md).

**Restrição do projeto:** não há orçamento para VM cara, GPU confidencial nem fine-tuning. O §8
reúne o caminho barato.

**Leitura mínima: comece por estes 10**
1. Avizienis et al., *Dependable and Secure Computing* (TDSC 2004): o vocabulário do DSN.
2. Wang et al., *DecodingTrust* (NeurIPS 2023), e Huang et al., *TrustLLM* (ICML 2024): o que é um
   LLM confiável.
3. Rabanser et al., *Towards a Science of AI Agent Reliability* (ICML 2026): métricas de
   confiabilidade além da acurácia.
4. Zheng et al., *Judging LLM-as-a-Judge* (NeurIPS 2023), e Jung et al., *Trust or Escalate*
   (ICLR 2025): quando confiar no LLM como juiz.
5. Greenblatt et al., *AI Control* (ICML 2024), e Nasr et al., *The Attacker Moves Second* (2025):
   como avaliar uma defesa.
6. Huang et al., *LLMs Cannot Self-Correct Reasoning Yet* (ICLR 2024), e Gou et al., *CRITIC*
   (ICLR 2024): por que o veredito precisa de evidência externa.
7. Miller, *Adding Error Bars to Evals* (2024): rigor estatístico barato.
8. Arditi et al., *Refusal Is Mediated by a Single Direction* (NeurIPS 2024), e Hurtado, *Has This
   Checkpoint Been Abliterated?* (2026): detectar obliteração sem treinar.
9. Schnabl et al., *Attestable Audits* (2025): avaliação atestada em TEE de CPU.
10. OWASP Top 10 for LLM 2025 e NIST AI 600-1: as referências não acadêmicas que todo mundo cita.

---

## 1. Fundamentos, surveys e dependabilidade

**Surveys e taxonomias de LLMs confiáveis**
- **TrustLLM** (Huang et al., ICML 2024) ✔: princípios em 8 dimensões de confiabilidade e benchmark com 16 LLMs, com *toolkit* aberto. [$]
- **DecodingTrust** (Wang et al., NeurIPS 2023 D&B, Outstanding Paper) ✔: 8 perspectivas de confiabilidade (toxicidade, viés, robustez, privacidade…) testadas no GPT-3.5 e no GPT-4. [$]
- **HELM** (Liang et al., TMLR 2023) ✔: avaliação holística com várias métricas por cenário; padrão de transparência em avaliação. [$]
- **Trustworthy LLMs: Survey and Guideline** (Liu et al., 2023) ✔: 7 categorias e 29 subcategorias de alinhamento e confiabilidade.
- **TrustGen** (Huang et al., 2025) ✔: diretrizes e benchmark dinâmico de confiabilidade para modelos generativos. [$]
- **TrustAgent survey** (Yu et al., KDD 2025) ✔: confiabilidade de agentes dividida em intrínseca (memória, ferramentas) e extrínseca (usuário, ambiente).

**Dependabilidade clássica aplicada a LLMs**
- **Basic Concepts and Taxonomy of Dependable and Secure Computing** (Avizienis, Laprie, Randell, Landwehr, IEEE TDSC 2004) ✔: cadeia falta → erro → falha, atributos e meios (prevenção, tolerância, remoção e previsão de faltas). **É a linguagem que o DSN espera.**
- **LLMGuard** (Zhong et al., **DSN 2026**) ✔: diagnóstico multiagente de falhas para LLM oferecido como serviço.
- **Are More LLM Calls All You Need?** (Chen et al., NeurIPS 2024) ✔: na votação majoritária, a acurácia pode subir e depois cair com mais chamadas. [$]
- **Failure Independence in LLM-Generated Code** (Nogueira et al., 2026) ✔ e **Knight–Leveson revisitado com agentes** (Ron, Baudry, Monperrus, 2026) ✔: *ensembles* de 3–5 versões rendem só ~43% do ganho esperado sob independência; **a diversidade entre LLMs é limitada**. [$]

**Falhas e confiabilidade de agentes**
- **MAST: Why Do Multi-Agent LLM Systems Fail?** (Cemri et al., NeurIPS 2025) ✔: 14 modos de falha em 3 categorias, com anotador LLM aberto. [$]
- **Who&When** (Zhang et al., ICML 2025) ✔: atribuir a falha ao agente certo acerta 53,5%; ao passo certo, só 14,2%. [$]
- **τ-bench** (Yao et al., ICLR 2025) ✔: cria a métrica **pass^k** (acertar as k tentativas); o gpt-4o fica abaixo de 25% em pass^8 no varejo. [$]
- **AI Agents That Matter** (Kapoor et al., TMLR 2025) ✔: avaliar agentes pela **fronteira custo × acurácia**, com *holdout*. [$]
- **Towards a Science of AI Agent Reliability** (Rabanser et al., ICML 2026) ✔: 12 métricas em 4 dimensões (consistência, robustez, previsibilidade, segurança); **ganhos de capacidade trouxeram pouca confiabilidade**. [$]
- **HAL: Holistic Agent Leaderboard** (Kapoor et al., ICLR 2026) ✔: *harness* padronizado com o custo como métrica principal.
- **Characterizing Faults in Agentic AI** (Shah et al., 2026) ✔: 34 tipos de falta em 4 dimensões, validados com 145 praticantes. [$]
- **When Errors Become Narratives** (Wu, 2026) ✔: classe *fail-plausible*, em que o LLM transforma o erro numa explicação convincente. [$]

**Não-determinismo e reprodutibilidade**
- **Non-Determinism of "Deterministic" LLM Settings** (Atil et al., 2024–25) ✔: a temperatura 0, a acurácia varia até 15% em 10 execuções. [$]
- **Numerical Sources of Nondeterminism** (Yuan et al., NeurIPS 2025) ✔: em BF16, até 9% de variação entre GPUs e *batches*; LayerCast reduz isso. [$]
- **The Good, the Bad, and the Greedy** (Song et al., NAACL 2025) ✔: avaliações devem reportar variância; decodificação gulosa costuma ser melhor. [$]
- **Non-determinism of ChatGPT in Code Generation** (Ouyang et al., TOSEM) ✔: temperatura 0 reduz, mas não elimina, o não-determinismo. [$]

**Vizinhos no próprio DSN 2026** (lista de aceitos ✔, interessam ao posicionamento)
- **Bypassing Safety Alignment via API Design: Response Prefill** (Research): o *prefill* exposto pela API remove o alinhamento; relevante para a linha de LLMs.
- **RO: Reliable Orchestration of LLM Programs via Deterministic-Generative Separation** (Disrupt): separar a parte determinística da gerativa, mesma ideia do Juiz em camadas.
- **FGF: Fact-Graph Feedback Loop for Verifiable LLM-based Decision Making** (pôster).
- **Does the Knight and Leveson Hypothesis Hold for LLM-Based Code Generation?** (pôster).
- **Memory-Bandwidth Side Channels for Input Recovery in Edge-Deployed LLM Inference** (pôster).

## 2. O LLM como juiz: vieses, incerteza e alucinação

**LLM-as-a-judge**
- **Judging LLM-as-a-Judge (MT-Bench)** (Zheng et al., NeurIPS 2023 D&B) ✔: o GPT-4 concorda com humanos em mais de 80% dos casos; documenta os vieses de posição, verbosidade e autopromoção.
- **A Survey on LLM-as-a-Judge** (Gu et al., 2024–25) ✔: taxonomia de como tornar juízes confiáveis (consistência, mitigação de viés).
- **Justice or Prejudice? (CALM)** (Ye et al., ICLR 2025) ✔: mede 12 vieses de juízes com perturbações automáticas. [$]
- **Judging the Judges** (Thakur et al., GEM@ACL 2025) ✔: só os maiores juízes se aproximam dos humanos, e ainda abaixo do acordo entre humanos.
- **JudgeBench** (Tan et al., ICLR 2025) ✔: em pares difíceis de correção, o GPT-4o fica pouco acima do acaso.
- **CodeJudgeBench** (Jiang et al., ACL 2026) ✔: 26 juízes de código; o Qwen3-8B supera modelos de 70B; juízes são sensíveis à ordem, a nomes e a **comentários enganosos**. [$]
- **Rating Roulette** (Haldar, Hockenmaier, Findings EMNLP 2025) ✔: a mesma entrada recebe notas diferentes, então uma execução só engana. [$]
- **Prometheus 2** (Kim et al., EMNLP 2024) ✔: juiz aberto de 7B (Apache-2.0) que avalia por rubrica e fica perto do GPT-4. [$]
- **Trust or Escalate** (Jung et al., ICLR 2025 oral) ✔: avaliação em cascata com **garantia comprovável** de concordância humana; o caso incerto escala para um juiz maior. [$]
- **LLMs are not Fair Evaluators** (Wang et al., ACL 2024) ✔ e **LLM Evaluators Favor Their Own Generations** (Panickssery et al., NeurIPS 2024) ✔: viés de posição e autopreferência.

**Incerteza e calibração**
- **Language Models (Mostly) Know What They Know** (Kadavath et al., 2022) ✔: modelos grandes são razoavelmente calibrados e conseguem avaliar a própria resposta (P(True)).
- **Semantic Entropy** (Farquhar et al., *Nature* 2024) ✔: entropia sobre o significado de várias amostras detecta confabulação sem rótulos nem treino. [$]
- **Uncertainty Quantification for LLMs: survey** (Shorinwa et al., ACM CSUR 2025) ✔: taxonomia de métodos de caixa-branca e caixa-preta.
- **Can LLMs Express Their Uncertainty?** (Xiong et al., ICLR 2024) ✔: a confiança verbalizada é superconfiante. [$]
- **Conformal Language Modeling** (Quach et al., ICLR 2024) ✔: amostra até que o conjunto contenha uma resposta aceitável com probabilidade garantida. [$]
- **Conformal Factuality Guarantees** (Mohri, Hashimoto, ICML 2024) ✔: remove afirmações incertas para garantir 80–90% de correção. [$]
- **API Is Enough: Conformal Prediction without Logits** (Su et al., Findings EMNLP 2024) ✔: conformal só com acesso por API. [$]
- **Uncertainty of LLM-as-a-Judge via Conformal** (Sheng et al., EMNLP 2025) ✔: intervalo com cobertura garantida para a nota do juiz. [$]

**Alucinação e factualidade**
- **SelfCheckGPT** (Manakul et al., EMNLP 2023) ✔: inconsistência entre amostras indica alucinação, em caixa-preta. [$]
- **FActScore** (Min et al., EMNLP 2023) ✔: quebra o texto em fatos atômicos e confere cada um contra uma fonte.
- **MiniCheck** (Tang et al., EMNLP 2024) ✔: verificador de fatos de 770M com acurácia de GPT-4. [$]
- **Hallucination Survey** (Huang et al., ACM TOIS 2025) ✔: causas, detecção, benchmarks e mitigação.
- **Why Language Models Hallucinate** (Kalai et al., OpenAI 2025) ✔: avaliação binária premia o chute confiante; propõe pontuar a abstenção.

**Autoconsistência e verificação**
- **Self-Consistency** (Wang et al., ICLR 2023) ✔: votar entre vários raciocínios amostrados (+17,9% no GSM8K). [$]
- **LLMs Cannot Self-Correct Reasoning Yet** (Huang et al., ICLR 2024) ✔: sem *feedback* externo, a autocorreção não ajuda e pode piorar.
- **CRITIC** (Gou et al., ICLR 2024) ✔: o modelo verifica o próprio rascunho com ferramentas externas; **o *feedback* externo é o que funciona**. [$]
- **Replacing Judges with Juries (PoLL)** (Verga et al., 2024) ✔: um painel de modelos pequenos e diversos supera um juiz grande, com custo mais de 7× menor. [$]
- **Are More LLM Calls All You Need?** (Chen et al., NeurIPS 2024, venue só por resultado de busca): votar mais nem sempre melhora; o ganho é não monotônico.
- **Great Models Think Alike** (Goel et al., ICML 2025) ✔: os erros dos LLMs estão cada vez mais correlacionados, então *ensembles* falham juntos.

## 3. Segurança de aplicações com LLM

**Prompt injection**
- **Not What You've Signed Up For** (Greshake et al., AISec 2023) ✔: trabalho fundador da injeção indireta; conteúdo recuperado vira instrução.
- **Ignore Previous Prompt** (Perez, Ribeiro, NeurIPS 2022 WS) ✔: injeção direta, sequestro de objetivo e vazamento de *prompt*.
- **Formalizing and Benchmarking Prompt Injection** (Liu et al., USENIX Sec 2024) ✔: formaliza os ataques e avalia ataques × defesas de forma sistemática.
- **BIPIA** (Yi et al., KDD 2025) ✔: benchmark de injeção indireta, com defesas de caixa-preta que dispensam treino. [$]
- **Spotlighting** (Hines et al., Microsoft, 2024) ✔: só *prompt*: delimitar, marcar e codificar o dado não confiável. [$]
- **StruQ / SecAlign** (Chen et al., USENIX Sec 2025 / CCS 2025) ✔: separam instrução de dado e reforçam com fine-tuning.
- **Instruction Hierarchy** (Wallace et al., OpenAI, 2024) ✔: treina o modelo a priorizar system > usuário > ferramenta.
- **AgentDojo** (Debenedetti et al., NeurIPS 2024 D&B) ✔ e **CaMeL** (Debenedetti et al., 2025) ✔: benchmark de agentes sob injeção, e defesa por construção com fluxo de informação.

**Jailbreak e robustez**
- **GCG** (Zou et al., 2023) ✔: sufixos adversariais otimizados, universais e transferíveis.
- **Jailbroken** (Wei et al., NeurIPS 2023 oral) ✔: o treino de segurança falha por objetivos concorrentes e generalização incompatível.
- **Many-shot Jailbreaking** (Anil et al., NeurIPS 2024) ✔: centenas de exemplos no contexto longo quebram o alinhamento, seguindo uma lei de potência.
- **HarmBench / JailbreakBench** (Mazeika et al., ICML 2024 / Chao et al., NeurIPS 2024 D&B) ✔: *red teaming* padronizado com artefatos reutilizáveis. [$]
- **The Attacker Moves Second** (Nasr, Carlini, Tramèr et al., 2025) ✔: ataques adaptativos quebram 12 defesas com ASR > 90%; **avaliar defesa só com ataque estático engana**.

**Guardrails pequenos (rodam em CPU)**
- **Llama Guard / Llama Guard 3-1B-INT4** (Inan et al. 2023 / Fedorov et al. 2024) ✔: classificador de entrada e saída; a versão de 440 MB roda em CPU. [$]
- **Llama Prompt Guard 2 (22M/86M)** (Meta, 2025) ✔: detector de injeção e jailbreak; o 22M tem recall de 88,7% com 1% de falso positivo. [$]
- **PIGuard** (Li, Liu, ACL 2025) ✔: mede a sobre-defesa (guards caem a ~60% em entradas benignas) e oferece um guard que a reduz. [$]
- **Qwen3Guard** (Qwen, 2025) ✔: guard de 0,6B a 8B, 119 idiomas, inclusive moderação em *streaming* (Apache-2.0). [$]
- **NeMo Guardrails** (Rebedea et al., EMNLP 2023 Demo) ✔: *rails* programáveis sem treino. [$]
- **Constitutional Classifiers** (Sharma et al., Anthropic, 2025) ✔: classificadores treinados a partir de uma constituição; resistiram a mais de 3.000 h de *red teaming*.
- **SoK: Evaluating Jailbreak Guardrails** (Wang et al., IEEE S&P 2026) ✔: taxonomia e avaliação de guardrails por segurança, eficiência e utilidade.
- **Bypassing Prompt Injection and Jailbreak Detection in LLM Guardrails** (Hackett et al., LLMSec 2025) ✔: guards pequenos são evadidos, em alguns casos 100%.

**Privacidade e vazamento**
- **Extracting Training Data from LLMs** (Carlini et al., USENIX Sec 2021) ✔ e **Scalable Extraction** (Nasr et al., ICLR 2025) ✔: modelos memorizam e devolvem dados de treino, e o alinhamento não remove isso.
- **Do Membership Inference Attacks Work on LLMs?** (Duan et al., COLM 2024) ✔ e **SoK MIAs** (Meeus et al., SaTML 2025) ✔: MIAs ficam perto do acaso; sucessos aparentes vêm de diferença de distribuição.
- **Analyzing Leakage of PII in LMs** (Lukas et al., IEEE S&P 2023) ✔: jogos formais de extração de PII; DP por sentença ainda vaza ~3%.
- **Effective Prompt Extraction** (Zhang, Carlini, Ippolito, COLM 2024) ✔: ataques simples recuperam o *system prompt* com alta probabilidade. [$]

**Segurança de agentes**
- **AI Agents Under Threat** (Deng et al., ACM CSUR 2025) ✔: survey de ameaças a agentes em quatro lacunas.
- **IsolateGPT** (Wu et al., NDSS 2025) ✔: isola a execução de apps de terceiros em sistemas com LLM.
- **Progent** (Shi et al., 2025) ✔: menor privilégio por políticas determinísticas sobre chamadas de ferramenta. [$]
- **AirGapAgent** (Bagdasarian et al., CCS 2024) ✔: o agente só vê os dados necessários à tarefa (integridade contextual). [$]
- **Design Patterns for Securing LLM Agents** (Beurer-Kellner et al., 2025) ✔: padrões arquiteturais com resistência demonstrável a injeção. [$]

## 4. Transparência, auditoria e verificabilidade

**Documentação e *accountability***
- **Model Cards for Model Reporting** (Mitchell et al., FAT* 2019) ✔: ficha padronizada de uso pretendido, avaliação desagregada e limitações. [$]
- **Datasheets for Datasets** (Gebru et al., CACM 2021) ✔: questionário de proveniência, composição e uso dos dados. [$]
- **Closing the AI Accountability Gap** (Raji et al., FAT* 2020) ✔: auditoria interna de ponta a ponta (SMACTR), com artefatos documentais em cada etapa. [$]
- **Auditing LLMs: A Three-Layered Approach** (Mökander et al., *AI and Ethics* 2023) ✔: auditoria em três camadas, de governança, de modelo e de aplicação.
- **Foundation Model Transparency Index** (Bommasani et al. 2023/2024; Wan et al. 2025) ✔: a nota média foi 37 → 58 → 40 em 100; **a transparência voluntária regrediu**, o que reforça a verificação técnica.
- **System Cards for AI-Based Decision-Making** (Gursoy, Kakadiaris, 2022) ✔: 56 critérios como *scorecard* de auditoria.

**Auditoria externa**
- **Structured Access** (Shevlane, 2022) ✔: acesso controlado e remoto no lugar da liberação aberta dos pesos.
- **A Safe Harbor for AI Evaluation and Red Teaming** (Longpre et al., ICML 2024 position) ✔: proteção legal e técnica para avaliação de boa-fé por terceiros.
- **In-House Evaluation Is Not Enough** (Longpre et al., 2025) ✔: relatório padronizado de falhas e programas de divulgação.
- **Black-Box Access is Insufficient for Rigorous AI Audits** (Casper et al., FAccT 2024) ✔: auditorias de caixa-branca permitem muito mais escrutínio.
- **Auditing Model Substitution in LLM APIs** (Cai et al., 2025) ✔: testes de caixa-preta não pegam troca sutil de modelo; os autores propõem TEE.
- **Attestable Audits** (Schnabl et al., ICML 2025 WS) ✔: benchmarks de segurança rodam em TEE de CPU e o resultado sai atestado. [$]
- **Laminator** (Duddu et al., CODASPY 2025) ✔: TEE de CPU atesta o "cartão de propriedades" do modelo. [$]

**Execução confiável barata (TEE de CPU, sem GPU)**
- **Confidential LLM Inference: CPU vs GPU TEEs** (Chrapek et al., 2025) ✔: TDX e SGX custam < 10% de vazão no Llama2-7B; em lotes pequenos, a GPU confidencial sai até 100% mais cara. [$]
- **CELLM: Lightweight LLM Inference in TEEs** (Feng et al., ISQED 2026) ✔: modelos de até 7B em TDX; INT4 dá até 3× a vazão do FP16. [$]
- **Numerical Sources of Nondeterminism in LLM Inference** (Yuan et al., 2025) ✔: em BF16 *greedy*, a acurácia varia até 9% entre configurações; LayerCast reduz o problema. [$]
- **Defeating Nondeterminism in LLM Inference** (He, Thinking Machines, 2025) ✔: com *kernels* invariantes ao *batch*, 1.000 de 1.000 saídas idênticas, ~1,6× mais lento. [$]
- **opML** (Conway et al., 2024) ✔: verificação otimista, em que o resultado é aceito e pode ser contestado com prova de fraude. [$]
- **Preço** (Azure Retail Prices API, East US, Linux) ✔: **DC4as_v5, com SEV-SNP, 4 vCPU e sem GPU, sai a US$ 0,172/h sob demanda e US$ 0,036/h em *spot***. A NCC H100 confidencial custa ~40× mais.

**Avaliar guardrails sem treinar nada**
- **HarmBench** (Mazeika et al., ICML 2024) ✔: framework padronizado de *red teaming* e recusa robusta.
- **StrongREJECT** (Souly et al., NeurIPS 2024 D&B) ✔: benchmark de recusa com juiz pequeno (Gemma-2B). [$]
- **SORRY-Bench** (Xie et al., ICLR 2025) ✔: 440 instruções em 44 tópicos; um juiz de 7B fica perto do GPT-4. [$]
- **Llama Guard 3-1B-INT4** (Fedorov et al., 2024) ✔: classificador de segurança de 440 MB que roda a ≥ 30 tok/s em CPU de celular. [$]
- **Refusal Is Mediated by a Single Direction** (Arditi et al., NeurIPS 2024) ✔: a recusa é uma direção no espaço de ativações; é a base da abliteração e serve para medi-la. [$]
- **Has This Checkpoint Been Abliterated?** (Hurtado, 2026) ✔: combina o gap de recusa nas ativações com o *diff* de pesos; **AUROC 0,95 em 273 checkpoints**. Pressupõe uma referência atestada, e uma referência forjada o engana. [$]
- **Detecting Safety Training Modification (AMS)** (Messenger, IEEE Access 2026) ✔: a geometria das ativações detecta abliteração, mas um fine-tuning puramente comportamental escapa. [$]
- **REEF** (Zhang et al., ICLR 2025 oral) ✔: *fingerprint* sem treino por similaridade de representações; resiste a fine-tuning, poda e *merge*. [$]

## 5. Engenharia e testes de aplicações com LLM

**Testes**
- **Software Testing with LLMs: Survey, Landscape, and Vision** (Wang et al., TSE 2024) ✔: mapa do uso de LLM em geração de testes, oráculos e reparo.
- **LLM-Based Agents for Software Engineering: A Survey** (Liu et al., TOSEM 2025) ✔: taxonomia de agentes para SE e das tarefas que eles fazem.
- **METAL** (Hyun et al., ICST 2024) ✔: relações metamórficas geradas por *template* testam robustez de LLMs sem oráculo. [$]
- **Drowzee** (Li et al., OOPSLA 2024) ✔: casos metamórficos por programação lógica; achou 24,7–59,8% de alucinação factual em seis LLMs. [$]
- **Differential Prompting** (Li et al., ASE 2023) ✔: o LLM sintetiza uma versão de referência do programa e roda teste diferencial (acerto de 28,8% para 77,8%). [$]
- **EvalPlus** (Liu et al., NeurIPS 2023) ✔: amplia os testes do HumanEval e mostra que os benchmarks originais superestimam a correção. [$]

**Falhas e bugs em aplicações com LLM**
- **Challenges for LLM Application Developers** (Chen et al., TOSEM 2025) ✔: taxonomia de desafios a partir de 29 mil perguntas no fórum da OpenAI.
- **Prompts Are Programs Too!** (Liang et al., FSE 2025) ✔: programar *prompts* é diferente da engenharia de software tradicional.
- **Bugs in LLM Agent Orchestration Frameworks** (Xue et al., ASE 2025 Industry) ✔: 1.026 bugs de LangChain, LlamaIndex e Haystack em 9 causas-raiz.
- **Why Do Multi-Agent LLM Systems Fail? (MAST)** (Cemri et al., NeurIPS 2025 D&B) ✔: 14 modos de falha extraídos de mais de 1.600 *traces*.
- **Outages and Incidents in Public LLM Services** (Chu et al., ICPE 2025) ✔: frequência e tempo de recuperação de falhas em 8 serviços públicos de LLM.
- **PromptDebt** (Aljohani et al., EASE 2025) ✔: dívida técnica em projetos com LLM (atualiza o *Hidden Technical Debt* de Sculley, NIPS 2015); o *prompt* é a maior fonte.

**Avaliação na prática**
- **Adding Error Bars to Evals** (Miller, Anthropic, 2024) ✔: intervalos de confiança, comparação pareada e poder estatístico para avaliações. [$]
- **Lessons from the Trenches on Reproducible Evaluation** (Biderman et al., 2024) ✔: armadilhas de reprodutibilidade aprendidas com o lm-evaluation-harness. [$]
- **Who Validates the Validators? (EvalGen)** (Shankar et al., UIST 2024) ✔: alinha o avaliador LLM a notas humanas e descreve o *criteria drift* (o critério muda enquanto se avalia). [$]
- **Benchmarking LLMs Under Data Contamination** (Chen et al., EMNLP 2025) ✔: limites dos benchmarks estáticos e princípios para benchmarks dinâmicos. [$]

**Guardrails, monitoramento e arquitetura**
- **Building Guardrails for LLMs** (Dong et al., ICML 2024 position) ✔: requisitos para guardrails e defesa de abordagem neurossimbólica com verificação rigorosa.
- **Swiss Cheese Model for FM Agents** (Shamsujjoha et al., ICSA 2025) ✔: guardrails em camadas, cada uma imperfeita e o conjunto robusto. [$]
- **Agent Design Pattern Catalogue** (Liu et al., JSS 2025) ✔: 18 padrões arquiteturais para agentes, com *trade-offs*. [$]
- **AgentSpec** (Wang et al., ICSE 2026) ✔: regras aplicadas em *runtime* bloqueiam mais de 90% das execuções inseguras com *overhead* de milissegundos. [$]
- **SPADE** (Shankar et al., PVLDB 2024) ✔: sintetiza asserções sobre as saídas de pipelines com LLM. [$]

**Verificação formal com LLM**
- **Clover** (Sun et al., SAIV 2024) ✔: checa a consistência entre código, docstring e anotações Dafny e rejeita código incorreto. [$]
- **Lemur** (Wu et al., ICLR 2024) ✔: o LLM propõe invariantes e o verificador formal decide, preservando a solidez.

## 6. Normas, frameworks e práticas (não são papers)

[grátis] marca uso ou acesso gratuito. Estado conferido em 2026-10-20.

**Gestão de risco**
- **NIST AI RMF 1.0** (2023, "em revisão" em 2026) ✔: organiza o risco em Govern, Map, Measure e Manage; é o vocabulário para descrever o Juiz. [grátis]
- **NIST AI 600-1, Generative AI Profile** (2024) ✔: riscos e ações para IA generativa; serve de *checklist* para apps com LLM. [grátis]
- **NIST AI 100-2 E2025** (2025) ✔: taxonomia oficial de ataques adversariais a IA; terminologia para o modelo de ameaça. [grátis]
- **ISO/IEC 42001, 23894, 22989 e 42005** ✔: sistema de gestão de IA certificável, gestão de risco, terminologia e avaliação de impacto (pagas).
- **IEEE 7000-2021** ✔: processo para levar valores éticos, como privacidade, ao projeto do sistema.
- **ENISA, Multilayer Framework for AI** (2023) ✔: boas práticas de cibersegurança para IA em três camadas. [grátis]

**Catálogos de ameaças e controles**
- **OWASP Top 10 for LLM Applications 2025** ✔: entre outros, LLM01 prompt injection, LLM02 vazamento de informação sensível e LLM07 vazamento de *system prompt*; servem de critérios para o Juiz. [grátis]
- **OWASP Top 10 for Agentic Applications 2026** (dez/2025) ✔: riscos ASI01–ASI10, como sequestro de objetivo, uso indevido de ferramentas e envenenamento de memória. [grátis]
- **MITRE ATLAS** (dados v2026.05) ✔: matriz de táticas e técnicas contra IA no estilo ATT&CK, com estudos de caso. [grátis]
- **Google SAIF** ✔: 15 riscos com controles e um questionário de risco para agentes. [grátis]
- **CSA AI Controls Matrix** (2025) ✔: 243 controles mapeados para ISO 42001, NIST e EU AI Act. [grátis]
- **CoSAI** (OASIS) ✔: trabalho aberto sobre cadeia de suprimentos de IA e agentes seguros. [grátis]
- **NCSC, Guidelines for Secure AI System Development** (2023) ✔: *checklist* curto de projeto, desenvolvimento, implantação e operação seguros. [grátis]

**Regulação**
- **EU AI Act + Digital Omnibus** (fontes secundárias, a verificar no EUR-Lex): obrigações de modelos de propósito geral (GPAI) desde ago/2025; alto risco adiado para 2027–2028. [grátis]
- **GPAI Code of Practice** (Comissão Europeia, jul/2025) ✔: transparência, *copyright*, segurança; modelo de documentação de modelos. [grátis]
- **PL 2338/2023** (Câmara) ✔: **em tramitação**, aguardando parecer na Comissão Especial (última ação em 02/09/2026); não está vigente.
- **ANPD: Sandbox Regulatório de IA** (2º relatório em out/2026) ✔: metodologia de testes de transparência, explicabilidade e proteção de dados sob a LGPD; aproveitável como critério do Juiz. [grátis]
- **EUA: EO 14365 e EO 14409** ✔: política federal de IA e acesso voluntário do governo a modelos de fronteira antes do lançamento.

**Ferramentas abertas de avaliação**
- **Inspect + Inspect Evals** (UK AISI, MIT) ✔: avaliação em *sandbox* Docker, com mais de 200 avaliações prontas; base natural para avaliar o Juiz. [grátis]
- **garak** (NVIDIA, Apache-2.0) ✔: scanner de vulnerabilidades de LLM pela linha de comando (injeção, jailbreak, vazamento de dados de treino). [grátis]
- **PyRIT** (Microsoft, MIT) ✔: *red teaming* automatizado de IA generativa. [grátis]
- **promptfoo** (MIT, hoje parte da OpenAI) ✔: testes e *red teaming* de *prompts* em CI/CD. [grátis]
- **lm-evaluation-harness** (EleutherAI, MIT) ✔: padrão de fato para mais de 60 benchmarks; checa se um fine-tuning degradou capacidades. [grátis]
- **MLCommons AILuminate** ✔: benchmark padronizado de segurança; demo aberta com 1.200 *prompts* (CC BY 4.0). [grátis]
- **HELM** (Stanford CRFM) ✔: avaliação holística; em modo de manutenção desde jun/2026, então vale como método, não como dependência. [grátis]

**Práticas de laboratórios e institutos**
- **Frontier safety frameworks**: Anthropic RSP v3.4 (jul/2026) ✔, OpenAI Preparedness v2 (abr/2025; versão vigente a verificar) e Google DeepMind FSF v3.1 (abr/2026) ✔; limiares de capacidade com salvaguardas correspondentes. [grátis]
- **METR** ✔: avaliação independente de capacidades autônomas, com plataforma aberta sobre o Inspect. [grátis]
- **International AI Safety Report 2026** (Bengio et al.) ✔: síntese científica de consenso, boa citação de autoridade. [grátis]
- **AI Incident Database** ✔: base pública de incidentes reais, fonte de casos para motivar o artigo. [grátis]
- **International Network for Advanced AI Measurement** (antiga rede de AISIs, dez/2025) ✔: boas práticas de avaliação entre 10 países (o Brasil não está). [grátis]

## 7. O que isso dá ao DNAT

- **Falar a língua do DSN.** Descrever o Juiz com a taxonomia de Avizienis:
  - um falso negativo é uma falha de confidencialidade;
  - os testes mecânicos são remoção de faltas;
  - a diversidade de mecanismos é tolerância a faltas.

  No DSN 2024–2026, LLMs aparecem quase sempre como ferramenta. A dependabilidade do próprio
  LLM que decide é pouco tratada (LLMGuard é exceção), e esse é o nosso espaço.
- **Nunca reportar uma execução só.** Usar pass^k, taxa de concordância entre execuções e
  intervalos de confiança (τ-bench, Rating Roulette, Miller), além da fronteira custo × acurácia
  (Kapoor, Rabanser).
- **Diversidade de natureza, não só de modelo.** Votar entre LLMs rende pouco porque os erros são
  correlacionados (Goel, Nogueira, Chen). O ganho vem de combinar testes mecânicos com LLM.
- **Abster-se com garantia.** Calibrar um limiar de abstenção num conjunto pequeno rotulado
  (conformal, Trust or Escalate); o caso incerto vira "inconclusivo".
- **Ancorar o veredito em *feedback* externo.** A autocorreção sem ferramenta não funciona
  (Huang); o que funciona é verificar com execução (CRITIC). Isso é a L2.
- **Avaliar defesas com ataque adaptativo.** Tanto guards quanto o Juiz (Nasr, Hackett). Medir
  também a sobre-defesa (PIGuard).
- **Adotar já, de graça:**
  - OWASP LLM Top 10 2025 e Agentic Top 10 2026 como taxonomia de ameaças;
  - NIST AI RMF com o AI 600-1 como estrutura de risco;
  - MITRE ATLAS para rotular ataques;
  - Inspect como *harness* de avaliação;
  - garak ou promptfoo para *red teaming* em CI;
  - no Brasil, a metodologia do sandbox da ANPD, citando o PL 2338 só como "em tramitação".

## 8. Caminho barato para a linha de LLMs

**Sem GPU e sem treino.** O caminho reaproveita a CVM de uso único que o DNAT já usa:

1. **Ambiente:** CVM SEV-SNP **DC4as_v5** (4 vCPU, US$ 0,172/h sob demanda e US$ 0,036/h em
   *spot*) ✔. Custa ~40× menos que a GPU confidencial.
2. **Modelo:** LLM aberto pequeno (1–3B) em GGUF quantizado no llama.cpp. Rodar com *batch* = 1 e
   *threads* fixas para buscar saída reproduzível (He; Yuan). O hash dos pesos vai dentro da imagem
   OCI atestada.
3. **"Fine-tuning" barato:** sem treinar na plataforma. Tratar o derivado como **um checkpoint
   enviado pelo usuário** (por exemplo, um LoRA pequeno feito fora) e **julgar o resultado**, não o
   processo. É o caso que dá para avaliar em CPU.
4. **Juiz do derivado, sem treino:**
   - um subconjunto de StrongREJECT ou SORRY-Bench com juiz pequeno (≤ 2B) ou Llama Guard 3-1B-INT4;
   - XSTest para *over-refusal*;
   - **detector de abliteração por ativações e *diff* de pesos contra o base atestado** (Arditi;
     Hurtado, AUROC 0,95);
   - REEF para confirmar a linhagem.
5. **Saída:** relatório assinado pela CVM, no estilo Attestable Audits e Laminator. O base e o
   derivado são identificados pelo digest OMS.

**Limites a declarar.** Fine-tuning puramente comportamental escapa à análise de ativações (AMS).
Uma referência forjada engana o detector, por isso ela tem de ser atestada. Backdoors com gatilho
passam por qualquer bateria finita.

**Trabalho futuro:** GPU confidencial, fine-tuning dentro da plataforma, ZK.

**Contribuição possível e barata:** medir tokens/s de modelos de 1–8B no llama.cpp dentro de
SEV-SNP e checar a reprodutibilidade bit a bit em CPU. Não achamos número publicado para isso.
