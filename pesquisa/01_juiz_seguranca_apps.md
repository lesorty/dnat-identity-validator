# Juiz de segurança de aplicações: levantamento de literatura

**Data:** 2026-10-20 · **Natureza:** agregação de dados para decidir depois. **Nada aqui é decisão**:
as decisões continuam em [DSN2027/DECISOES.md](../DSN2027/DECISOES.md) e o desenho do Juiz em
[DSN2027/JUIZ_IA.md](../DSN2027/JUIZ_IA.md).

**Método.** Primeiro li o repositório: JUIZ_IA, D1–D4, E2/E2b/E2c, o rascunho do artigo e o
brainstorm 03 (que hoje só existe na tag `ladc-2026`). Depois fiz três levantamentos em paralelo:

- (a) AI control e monitores LLM;
- (b) detecção mecânica de vazamento e portão de saída;
- (c) benchmarks, código adversarial, esteganografia e recusa.

Cada referência foi aberta na fonte durante o levantamento. As que mais pesam nas decisões foram
conferidas de novo na página primária e levam ✔. O orçamento de buscas web acabou no meio do
trabalho; o que ficou sem cobertura está listado no §8.

**Convenções.**
- **Tier:** **topo** (S&P, USENIX Sec, CCS, NDSS, ICML, NeurIPS, ICLR, ACL/EMNLP, ICSE…), **PR** (outro peer-reviewed), **WS** (workshop), **Pre** (preprint), **Rel** (relatório, blog, documentação).
- **(a verificar)**: não confirmado na fonte.

---

## 1. Onde estamos (o que o repositório já tem)

### 1.1 O problema, como o formulamos

- **Pergunta:** antes de liberar um ativo, decidir se a app pode rodar sobre ele sem violar o que
  o dono permite.
- **Reformulação decisiva (JUIZ §7, E2c).** O container roda sem rede (D4), então o único canal de
  vazamento é a **saída legítima**. Ficam de fora os canais laterais declarados (E2c §4): logs,
  código de saída, tempo, tamanho e várias execuções. O problema vira **fluxo de informação
  dataset → saída, limitado pelo que as tags liberam**.
- **Caso que justifica o Juiz:** código conhecido e dados privados. O código é verificável, mas
  verificar custa caro demais para o dono do dataset.

### 1.2 Soluções que já encontramos

| Solução | Onde | Status |
|---|---|---|
| Juiz é uma **app do sistema**, na whitelist; recebe a app-alvo e devolve aprovado · aprovado com portão · reprovado · inconclusivo | D2, JUIZ §1, §9.5 | decidido |
| Cache do veredito por `(hash da fonte, tags, versão do Juiz)` | JUIZ A7, §9.5 | decidido |
| **Tags do dono** em catálogo fechado; o artigo usa 3 (`agregado:k`, `transformacao`, `sem-identificadores`) | JUIZ §3, artigo §5 | catálogo ainda em avaliação |
| **Camadas do barato ao caro**: L0 contrato, L1 estática, L2 dinâmica, L3 LLM com evidências, L4 portão | JUIZ §8 | desenho base |
| **L2 como núcleo mecânico**: canário direto, diferencial D/D′, variação do segredo (kNN à la F-BLEAU), seccomp em log e *sinkhole* para tentativa de rede | JUIZ §9.4, E2c §6 | MVP |
| L2 roda **na plataforma**, não dentro do Juiz | JUIZ §8 | decidido |
| **L4 obrigatória**: cobre gatilho por dado real; orçamento contra ataques de diferença | JUIZ §8 | MVP |
| **Não remover comentários**; L1 marca texto oculto, L2 dá fatos que a injeção não muda | JUIZ P3, §7 | decidido (Thornton) |
| Tentativa de rede sem tag de rede ⇒ **reprovado** | D2, E2c §6 | decidido |
| Sempre há **fonte** para julgar (todo build é atestado; imagem pronta rejeitada) | D4, E2b.7 | decidido |
| **Batalha** atacante caro × defensor barato, com e sem relatório de L2; API ≤ US$ 100 | JUIZ §6.1, §9.6, D2 | decidido |
| **Verdade de referência CTF**: o atacante entrega app + decodificador | JUIZ §9.2 | decidido |
| **Benchmark**: agregação, transformação e ML; ~10 tarefas por família; vazamentos V1–V6 | JUIZ §9.1, §9.3 | decidido |
| Guardrails do atacante: enquadrar como CTF, sementes nossas + mutação, modelos abertos, taxa de recusa como resultado | JUIZ §6.2 | plano |
| Ideias herdadas: Juiz na CVM com modelo aberto (sigilo do código), veredito vinculado à fonte + digest, diversidade de modelos (G2) | JUIZ §1, brainstorm 03 | em aberto |

### 1.3 Consensos que já tínhamos (JUIZ §7, 2026-10-17)

1. LLM sozinho é um juiz fraco de vulnerabilidade (PrimeVul).
2. A combinação neuro-simbólica supera o LLM puro (IRIS, LLMDFA).
3. A batalha **é** uma *control evaluation* (Greenblatt, ICML'24). Um monitor fraco funciona se
   puder reamostrar ou pedir evidência (Ctrl-Z).
4. Remover comentários piora modelos fracos; cruzar com SAST ajuda (Thornton).
5. A checagem de saída é prática consolidada (OpenSAFELY, ACRO), mas não cobre ataques de
   diferença. Clean rooms combinam revisão com N mínimo (AWS).
6. O teste diferencial tem base formal (SME), e o vazamento pode ser medido em bits (F-BLEAU).
7. Não existe benchmark de vazamento escondido em código (lacuna apontada por Zolkowski).

### 1.4 Perguntas que estavam abertas

- Do JUIZ §10:
  - As tags entram no artigo?
  - U1 é caso principal ou extensão?
  - O Juiz roda com modelo aberto na CVM ou por API?
  - Analisa só a fonte ou também a imagem?
  - O portão é parte do Juiz?
- Do PLANO §5: a lista exata de modelos da batalha.

---

## 2. O que a literatura recente diz

### 2.1 AI control: monitores contra atacantes que conhecem o monitor

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [Adaptive Attacks on Trusted Monitors Subvert AI Control Protocols](https://arxiv.org/abs/2510.09462) (Terekhov et al.) ✔ | **ICLR 2026** pôster ✔ (o arXiv não lista venue) · topo | O atacante conhece o protocolo e o monitor e embute *prompt injection* na própria saída. Monitores de fronteira são evadidos de forma consistente. O **Defer-to-Resample piora o quadro**, porque vira best-of-n. **Com injeção, o GPT-4.1 (que era o monitor mais forte sem ataque) deu nota 0 a todos os 375 backdoors do GPT-5 no APPS** ✔ (Fig. 2, §4.1) | O Juiz é whitelisted e público: **o atacante tem o Juiz por construção**, e esse modelo de ameaça vale para nós |
| [Evaluating Control Protocols for Untrusted AI Agents](https://arxiv.org/abs/2511.02997) (Kutasov et al.) | 2025 · Pre | Reamostrar para incriminar e deferir nas ações críticas leva a segurança de 50% para 96% no SHADE-Arena. Se o atacante sabe quando há reamostragem, ela cai para 17%. O que resiste é o que o atacante **não vê** | Manter segredos do protocolo: canários e sementes de D′ gerados na hora |
| [Strengthening Red Teams](https://alignment.anthropic.com/2025/strengthening-red-teams/) (Loughridge et al., Anthropic); paper [2511.02823](https://arxiv.org/abs/2511.02823) | nov/2025 · Rel/Pre | Um *scaffold* de ataque otimizado derruba a segurança de 0,87 para 0,41. A alavanca mais forte é o atacante ter um **simulador do monitor** | O "atacante caro" da batalha precisa simular o Juiz, senão a segurança sai superestimada |
| [How to evaluate control measures for LLM agents?](https://arxiv.org/abs/2504.05259) (Korbak et al., UK AISI) | 2025 · Pre | Define 5 níveis de controle. As permissões do red team devem acompanhar a capacidade do modelo | Régua para fixar o que o atacante sabe e pode na batalha |
| [A sketch of an AI control safety case](https://arxiv.org/abs/2501.17315) (Korbak et al.) | 2025 · Pre | *Safety case* de controle **para exfiltração de dados**, com três afirmações: elicitação adequada, avaliação representativa e extrapolação conservadora | O argumento mais próximo do que o artigo precisa montar |
| [SHADE-Arena](https://arxiv.org/abs/2506.15740) (Kutasov et al., Anthropic) | 2025 · Pre | Os melhores sabotadores têm 27% de sucesso (Claude 3.7) e 15% (Gemini 2.5 Pro); o melhor monitor chega a AUC 0,87. Inclui exfiltração de chave de API por e-mail legítimo | Métrica de "sucesso não detectado" |
| [BashArena](https://arxiv.org/abs/2512.15688) (Kaufman et al.) | 2025 · Pre | 637 tarefas, uma delas **exfiltrar segredos**. Sonnet 4.5 escapa do GPT-4.1-mini em 26% com 4% de FPR | Linha de base de defensor barato **sem** evidência mecânica |
| [LinuxArena](https://arxiv.org/abs/2604.15384) (Tracy et al.) | 2026 · Pre | 1.671 tarefas e 184 tarefas laterais. Opus 4.6 sabota sem ser pego em ~23% contra GPT-5-nano (1% de FPR). Ataques **feitos por humanos** (LaStraj) escapam bem mais | Ataques gerados só por modelo não saturam o benchmark: considerar um red team humano |
| [CTRL-ALT-DECEIT](https://arxiv.org/abs/2511.09904) (Ward et al.) | NeurIPS 2025 spotlight · topo | Monitores pegam bem backdoor de código e mal *sandbagging*. Agregar monitores ajuda; pode não bastar em alto risco | Família "ML": vazar pelo desempenho se parece com *sandbagging* |
| [Async Control](https://arxiv.org/abs/2512.13526) (Cooper Stickland et al., UK AISI) | 2025 · Pre | Um *ensemble* chega a 6% de FNR com 1% de FPR num ambiente *held-out* e extrapola o risco para o deployment | O Juiz é assíncrono (julga antes de rodar): modelo de métrica e de extrapolação |
| [Combining Cost-Constrained Runtime Monitors](https://arxiv.org/abs/2507.15886) (Hua et al.) | NeurIPS 2025 · topo | Escolhe quais monitores chamar sob orçamento, com limiares Neyman-Pearson. Em revisão de código, o recall **mais que dobra**; dois monitores combinados dominam cada um sozinho | Formalismo pronto para a cascata L1→L2→L3 com orçamento |
| [Ensemble Monitoring for AI Control](https://arxiv.org/abs/2605.15377) (Koran et al.) | 2026 · Pre | 3 monitores **diversos** valem 2,4× mais que 3 idênticos | Os sinais de L1/L2 são justamente sinais diversos e pouco correlacionados |
| [Calibration-Family Overfit](https://arxiv.org/abs/2607.06596) (Pinto) | COLM 2026 WS · WS | Um monitor calibrado na família do atacante pega 41%; calibrado em outra família, 19% | Se calibrarmos L3, o corpus precisa de atacantes de várias famílias; reportar a matriz de transferência |
| [Factor(T,U)](https://arxiv.org/abs/2512.02157) (Sandoval, Rushing) | 2025 · Pre | Decompor a tarefa leva o *trusted monitoring* de 41% para 63% no APPS | Julgar fluxos e funções isolados, guiados pelo taint de L1 |
| [CoT Red-Handed](https://arxiv.org/abs/2505.23575) (Arnav et al.) | NeurIPS 2025 · topo | Cria o BigCodeBench-Sabotage. Racionalizações enganosas no CoT enganam o monitor; o monitor híbrido tem detecção 2× maior nos casos sutis | Comentários e docstrings do atacante funcionam como "CoT racionalizadora" |
| [How does information access affect LLM monitors…](https://arxiv.org/abs/2601.21112) (Arike et al.) | 2026 · Pre | **"Menos é mais"**: monitores muitas vezes acertam mais vendo menos. *Extract-and-Evaluate* dá +16,8 pp de TPR@1%FPR | A evidência deve ser **extraída e estruturada** por ferramentas confiáveis, não despejada |
| [Reliable Weak-to-Strong Monitoring](https://arxiv.org/abs/2508.19461) (Kale et al., Scale) | ICLR 2026 oral · topo | Agentes que sabem que são monitorados degradam a detecção. Um *scaffold* hierárquico permite *weak-to-strong*; escalar só os casos sinalizados para humanos dá +15% de TPR | Defensor barato com *scaffold* + escalonamento seletivo |
| [Scaling Laws for Scalable Oversight](https://arxiv.org/abs/2504.18530) (Engels et al.) | NeurIPS 2025 spotlight · topo | No jogo "Backdoor Code", com gap de 400 Elo, a supervisão tem só **10%** de sucesso | Um LLM barato sozinho escala mal; a tese tem de se apoiar na evidência mecânica |
| [Code Monitor Red Teaming for Public-Test-Passing Code](https://arxiv.org/abs/2607.20852) (Liao et al.) ✔ | 2026 · Pre | 43.677 candidatos passam nos testes públicos e 23.081 deles falham nos ocultos. Verificadores fracos melhoram com *scaffold*, mas perdem a maioria dos bugs com 5% de FPR. **AUROC conferido no corpo (Tab. 3)** ✔: análise estática 0,52–0,57 · Qwen-7B em passada única 0,601 (Hybrid; o Direct dá 0,536, "perto do acaso") · **testes gerados e direcionados ao candidato (k=5) 0,765** (0,785 com k=10) · GLM-5.1 em passada única 0,833, mas só sobre código de geradores fechados (média geral 0,798). Sob pressão adversarial, todos caem (testes k=5: 0,695) | **O mais próximo da nossa hipótese**: execução ajuda o fraco, mas a combinação com LLM não foi testada |
| [Distributed Attacks in Persistent-State AI Control](https://arxiv.org/abs/2607.02514) (Hills et al.) e [Multi-Agent AI Control](https://arxiv.org/abs/2607.07368) (Makins et al.) | 2026 · Pre | Ataques graduais em vários PRs evadem ≥ 65%; um rastreador de estado reduz a evasão de 93% para 47% | Vazamento repartido entre versões ou execuções de uma app |
| [Coding with "Enemy"](https://arxiv.org/abs/2606.05647) (Ye et al.) | NeurIPS 2026 segundo o arXiv · topo | 94% dos desenvolvedores não detectaram sabotagem; com alerta correto do monitor, ela ainda passou em 9 de 16 sessões | Argumento para um veredito **vinculante**, não consultivo |

### 2.2 Ataques ao revisor LLM: injeção, iscas, comentários e recusa

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [Can Adversarial Code Comments Fool AI Security Reviewers…](https://arxiv.org/abs/2602.16741) (Thornton) ✔ | 2026 · Pre | Em 9.366 tentativas, comentários adversariais **com templates fixos** têm efeito pequeno e não significativo. Cruzar com análise estática chega a 96,9%. Remover comentários piora modelos fracos | Base da nossa decisão; **título correto no §7** |
| [ALIBI](https://arxiv.org/abs/2607.24964) (Wu, Nita-Rotaru) | 2026 · Pre | Comentários adversariais gerados **adaptativamente por um agente** passam de 90% de sucesso contra 4 detectores LLM | **Contradiz Thornton quando o atacante é adaptativo** |
| [Flashboom: Blinding LLM-Based Code Auditors](https://doi.org/10.1109/SP61157.2025.00125) (X. Li et al.) | IEEE S&P 2025 · topo | Código-isca chamativo desvia a atenção do auditor da falha real. "Taxa de cegamento" (o auditor detectava e deixa de detectar) de 96,3% no CodeLlama e 83,05% no Gemma ✔ (CSVs do [repositório](https://github.com/oxygen-hunter/Flashboom/tree/main/results/RQs)). **Ressalvas:** os números são de contratos Solidity (SmartBugs), o denominador do CodeLlama é 27, e um controle com **comentários benignos** dá o mesmo 0,963 no CodeLlama. A isca precisa de acesso à atenção (caixa-branca), então no GPT-4o não se aplica | Ataque **sem comentários**: o taint de L1 ancora a atenção de L3 no fluxo real |
| [Agent-as-a-Proxy Attacks](https://arxiv.org/abs/2602.05066) (Isbarov, Kantarcioglu) | 2026 · Pre | Injeção passa até por monitores *Extract-and-Evaluate* | Strings da app que L1/L2 copiam para o relatório viram vetor de injeção em L3 |
| [JudgeDeceiver](https://arxiv.org/abs/2403.17710) (Shi et al.) | CCS 2024 · topo | Injeção otimizada por gradiente; detecção por perplexidade não basta | Incluir injeção **otimizada**, não só textual |
| [RobustJudge](https://arxiv.org/abs/2506.09443) (S. Li et al.) | 2025/26 · Pre | 15 ataques, 8 defesas, 13 modelos; **nenhuma defesa domina**; a robustez depende muito do *template* | Avaliar o prompt de L3 sob ataque |
| [BadJudge](https://arxiv.org/abs/2503.00596) (Tong et al.) | ICLR 2025 · topo | Envenenar 1% do treino do juiz com gatilho de 1 token triplica a nota | Se L3 for *fine-tunado*, os dados e pesos do Juiz entram no TCB |
| [One Token to Fool LLM-as-a-Judge](https://arxiv.org/abs/2507.08794) (Zhao et al.) | 2025 · Pre/WS | "Chaves-mestras" como ":" geram falsos positivos até em modelos de fronteira | Normalizar a entrada do juiz |
| [Great Models Think Alike…](https://proceedings.mlr.press/v267/goel25b.html) (Goel et al.) | ICML 2025 spotlight · topo | Os erros dos modelos de fronteira estão **cada vez mais correlacionados**; juízes favorecem modelos parecidos | A diversidade precisa vir também de **fora** dos LLMs |
| [LLM Evaluators Recognize and Favor Their Own Generations](https://papers.nips.cc/paper_files/paper/2024/hash/7f1f0218e45f5414c79c0679633e47bc-Abstract-Conference.html) (Panickssery et al.) | NeurIPS 2024 · topo | O autorreconhecimento correlaciona com a autopreferência | Viés de família na batalha |
| [Rating Roulette](https://aclanthology.org/2025.findings-emnlp.1361/) (Haldar, Hockenmaier) | Findings EMNLP 2025 · PR | Juízes LLM são inconsistentes entre execuções | k amostras + variância + seed fixa |
| [LLMs Cannot Reliably Identify… Vulnerabilities (Yet?)](https://arxiv.org/abs/2312.12575) (Ullah et al.) | IEEE S&P 2024 · topo | Renomear variáveis muda o veredito em 26% dos casos | Mutação barata já engana o juiz |
| [CASHEWS](https://arxiv.org/abs/2609.18862) (Noirot Ferrand et al.) | 2026 · Pre | Inchar e empacotar o código esgota o contexto do LLM; pré-processar leva a cobertura de 69–86% para 99–100% | Ataque "estourar o contexto"; defesa por fatiamento até o *sink* (a saída) |
| Campanha "Hades"/Mini Shai-Hulud (Socket, jun/2026) | Rel, só por fonte secundária **(a verificar)** | Pacotes maliciosos abrem com texto QBRN fabricado para **o scanner LLM recusar** antes de chegar ao payload | Nova categoria: **recusa como evasão** do Juiz |

### 2.3 Detecção mecânica de vazamento (L1, L2)

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [Estimating g-Leakage via ML](https://arxiv.org/abs/2005.04399) (Romanelli et al.) | CCS 2020 · topo | Estima vulnerabilidade com função de ganho arbitrária via kNN e redes; consistente, mas **sem taxa finita de amostras** | Ganho com tolerância ("acertar o canário ± δ") para segredos numéricos |
| [Bayes Security](https://arxiv.org/abs/2011.03396) (Chatzikokolakis et al.) | CSF 2023 · topo | Métrica estilo vantagem criptográfica, estimável em caixa-preta | Candidata a métrica do veredito |
| [Eureka: black-box DP estimators](https://eprint.iacr.org/2022/1250) (Lu et al.) | IEEE S&P 2024 · topo | **Estimar DP com domínio irrestrito é impossível**; propõe *relative DP* sobre um conjunto finito T | Fixar um conjunto **finito** de valores de canário |
| [Sequentially Auditing DP](https://papers.neurips.cc/paper_files/paper/2025/hash/d41ddb5e702f647f6e92db1f8dbf86ec-Abstract-Conference.html) (González Lara et al.) | NeurIPS 2025 · topo | Teste sequencial *anytime-valid*: amostras de "50K para algumas centenas", com erro tipo I controlado | Parada antecipada em L2 no lugar de n fixo |
| [NIFuzz](https://arxiv.org/abs/2501.14500) (Blackwell et al.) | 2025 · Pre | Estima o fluxo quantificado com um *fuzzer*; achou todos os vazamentos em 14 programas, mas num exemplo usou ~750 milhões de entradas em 3 h | Contraste de custo com os nossos n≈20–50 |
| [Hyperfuzzing / LeakFuzzer](https://arxiv.org/abs/2308.09081) (Blackwell et al.) | EMSE 2024 · PR | AFL++ com oráculo de não interferência achou 100% dos vazamentos (inclui Heartbleed); CBMC achou ≤ 40% | *Self-composition* como oráculo de L2 |
| [Hypertesting of Programs](https://conf.researchr.org/details/icse-2024/icse-2024-research-track/234/Hypertesting-of-Programs-Theoretical-Foundation-and-Automated-Test-Generation) (Pasqua et al.) | ICSE 2024 · topo | Critério de hipercobertura; **sem alarme falso por construção**; só Java | Critério para escolher pares D/D′ |
| [QFuzz](https://arxiv.org/abs/2106.03346) (Noller, Tizpaz-Niari) | ISSTA 2021 · topo | *Fuzzing* quantitativo com min-entropia | Base de L2 |
| [RepoAudit](https://proceedings.mlr.press/v267/guo25n.html) (Guo et al.) | ICML 2025 · topo | Agente LLM com validador de caminhos: 40 bugs reais, 78% de precisão, ~US$ 2,54 por projeto | Padrão "LLM propõe, validador mecânico confirma" |
| [SemTaint](https://arxiv.org/abs/2601.10865) (Ghebremichael et al.) | 2026 · Pre | Critica o IRIS (LLM sem estado, arestas não resolvidas); agentes inferem *specs* e o CodeQL acha 106 de 162 vulnerabilidades antes perdidas | *Specs* de fonte e sumidouro para pandas etc. no Pysa/CodeQL |
| [Vamsa](https://www.microsoft.com/en-us/research/publication/vamsa-automated-provenance-tracking-in-data-science-scripts/) (Namaki et al.) | KDD 2020 · topo | Infere estaticamente quais colunas derivam *features* em scripts Python; 90–99% de precisão e recall | Checar a tag `transformacao` (colunas permitidas) |
| [SocketAI](https://arxiv.org/abs/2403.12196) (Zahan et al.) | ICSE 2025 · topo | GPT-4 detecta pacotes npm maliciosos com 99% de precisão; um pré-filtro estático corta 78% dos arquivos | L1 → L3 em cascata |
| [MalGuard](https://www.usenix.org/conference/usenixsecurity25/presentation/gao-xingan) (Gao et al.) | USENIX Sec 2025 · topo | ML clássico sobre APIs sensíveis, LLM só para refinar; 73 pacotes removidos do PyPI | Classificador barato antes do LLM |
| [LLMs for Malicious Python Packages](https://arxiv.org/abs/2602.16304) (Ryan et al.) | 2026 · Pre | F1 por pacote até 0,99, mas **0,48 por indicador (linha)**; muitos falsos positivos | LLMs triam bem e localizam mal |
| [Taint-Based Code Slicing for LLM npm detection](https://arxiv.org/abs/2512.12313) (Nguyen et al.) | 2025 · Pre | Fatias de taint cortam 99,75% dos tokens e levam a acurácia de 75,4% para 87,0%; ofuscação gera fatias vazias | Evidência extraída para L3 |
| [ML Models that Remember Too Much](https://arxiv.org/abs/1709.07886) (Song, Ristenpart, Shmatikov) | CCS 2017 · topo (precursor) | Código de treino malicioso esconde dados no modelo (LSB, sinal, correlação); vaza ~70% de um corpus sem perder acurácia | **Modelo de ameaça quase idêntico ao nosso** para a família ML; semente de esteganografia numérica |

### 2.4 Portão de saída e estatísticas agregadas (L4)

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [Reconstruction attack on the 2010 U.S. Census](https://arxiv.org/abs/2312.11283) (Abowd et al.) | HDSR 2025 · PR | 34 tabelas publicadas reconstruíram ~97 milhões de registros e reidentificaram 3,4 milhões; o Censo migrou para DP | "Agregar basta" é falso |
| [Linear Program Reconstruction in Practice](https://arxiv.org/abs/1810.05692) (Cohen, Nissim) | 2018 · Pre (a verificar JPC) | Reconstrução Dinur–Nissim contra um sistema de consultas em produção | Respostas demais e precisas demais permitem reconstruir o dataset |
| [Exploiting Diffix's Sticky Noise](https://www.usenix.org/conference/usenixsecurity19/presentation/gadotti) (Gadotti et al.) | USENIX Sec 2019 · topo | Ruído determinístico sem DP foi quebrado (89% de acurácia) | Não inventar ruído *ad hoc* |
| [QueryCheetah](https://arxiv.org/abs/2409.01992) (Stevanoski et al.) | CCS 2024 · topo | Busca automática de ataques contra sistemas de consulta, 18× mais rápida que o estado da arte | Red team automático do portão |
| [Attacks on Deidentification's Defenses](https://www.usenix.org/conference/usenixsecurity22/presentation/cohen) (A. Cohen) | USENIX Sec 2022 · topo | **Downcoding**: k-anonimato, l-diversidade e t-closeness minimais vazam pela própria minimalidade | A supressão "exata" de grupos < k vaza |
| [Inadequacy of Similarity-based Privacy Metrics](https://arxiv.org/abs/2312.05114) (Ganev, De Cristofaro) | IEEE S&P 2025 · topo | Passar em testes de similaridade não impede recuperar 78–100% dos *outliers*; **a métrica vira oráculo** | O portão de similaridade não pode ser um oráculo consultável |
| Documentação de clean rooms: [AWS](https://docs.aws.amazon.com/clean-rooms/latest/userguide/custom-considerations.html), [Google ADH](https://developers.google.com/ads-data-hub/guides/privacy-checks), [Snowflake](https://docs.snowflake.com/en/user-guide/aggregation-policies) | 2025–26 · Rel | AWS: o limiar mínimo **"não trata" ataques de diferença** e recomenda DP. Google: *difference checks* viraram **legado**, substituídos por ruído. Snowflake: a política só serve para parceiros já confiáveis | Os fornecedores admitem o limite do k mínimo |
| [SACRO](https://zenodo.org/records/10055365) (Smith et al.) | 2023 · Rel | Automação como "par extra de olhos" do checador humano | Prática de TRE (ambiente de pesquisa confiável) não supõe código adversário |
| [Privacy Auditing of LLMs](https://arxiv.org/abs/2503.06808) (Panda et al.) | ICLR 2025 · topo | Canários projetados chegam a 49,6% de TPR com 1% de FPR, contra 4,2% antes | Família ML: canários fortes |
| [The Canary's Echo](https://proceedings.mlr.press/v267/meeus25a.html) (Meeus et al.) | ICML 2025 · topo | Canários fora da distribuição **quase não ecoam** quando só a saída sai; funciona melhor um prefixo plausível com sufixo de alta entropia | Desenhar os canários para o canal de saída |
| [Auditing f-DP in One Run](https://proceedings.mlr.press/v267/mahloujifar25a.html) (Mahloujifar et al.) | ICML 2025 · topo | Auditoria com uma única execução de treino | Família ML |
| [REDACT](https://arxiv.org/abs/2606.19881) (Vats et al.) | 2026 · Pre | Detector de PII por regras tem **recall 0,07** na faixa de alta sensibilidade | PII só por regras não basta |
| [A False Sense of Privacy](https://arxiv.org/abs/2504.21035) (Xin et al.) | 2025/26 · Pre | Remover PII deixa 74% da informação inferível | `sem-identificadores` ≠ anonimato |
| [Tese de Desfontaines](https://desfontain.es/thesis/) | ETH 2020 · tese | Agregação sem ruído pode ser privada **sob conhecimento parcial** do atacante | A voz mais favorável ao k mínimo, mas exige modelo de ameaça explícito |

### 2.5 Benchmarks vizinhos e a lacuna C3

**Veredito.** Até 2026-10-20, dentro do que foi buscado, **não há benchmark de programas de
processamento de dados que vazem dados privados escondidos na saída legítima, com verdade de
referência por decodificador**. A lacuna C3 continua de pé. No artigo, escrever "até onde
sabemos" e citar os vizinhos.

| Vizinho | Venue · tier | O que tem | Por que não é o C3 |
|---|---|---|---|
| [CoT Red-Handed / BigCodeBench-Sabotage](https://arxiv.org/abs/2505.23575) | NeurIPS 2025 · topo | 1.140 pares de tarefa e 11 tarefas laterais, entre elas `ioexfil` e `logio`. Monitor só de ações pega < 20% da sabotagem sutil com 1% de FPR | A exfiltração é por rede ou arquivo, e eles a classificam como "não sutil" |
| [SHADE-Arena](https://arxiv.org/abs/2506.15740) | 2025 · Pre | Exfiltra uma chave de API por um e-mail legítimo | Trajetórias de agente, não programas de dados |
| [SLEIGHT-Bench](https://arxiv.org/abs/2605.16626) (Najt et al.) | 2026 · Pre | 40 ataques de evasão contra monitores em 11 categorias; captura geral de 32% | Catálogo de evasão reutilizável, não de vazamento |
| [ResearchArena](https://arxiv.org/abs/2607.19321) (Libon et al.) | 2026 · Pre | Sabotagem **nos dados de treino** detectada em < 50% das vezes (44% GPT-5.4, 19% Sonnet 4.6) | Sabotagem de P&D, não vazamento |
| [AgentLeak](https://arxiv.org/abs/2602.11510) (El Yagoubi et al.) | 2026 · Pre | Auditar só a saída perde 41,7% das violações em multiagente | Vazamento por privacidade, sem código malicioso |
| [AgentDojo](https://arxiv.org/abs/2406.13352), [InjecAgent](https://arxiv.org/abs/2403.02691), [ASB](https://arxiv.org/abs/2410.02644) | NeurIPS'24 D&B · ACL Findings'24 · ICLR'25 | Exfiltração induzida por injeção | O agente é a vítima, não o autor |
| [RedCode](https://arxiv.org/abs/2411.07781), [MalwareBench](https://aclanthology.org/2025.acl-long.1350), [CyberSecEval 2](https://arxiv.org/abs/2404.13161), [BaxBench](https://proceedings.mlr.press/v267/vero25a.html) | NeurIPS'24 · ACL'25 · Pre · ICML'25 | Código inseguro ou malicioso convencional; BaxBench verifica correção **e** segurança por *exploit* | O BaxBench é o modelo de verdade de referência mecânica mais próximo |
| [Song et al. CCS'17](https://arxiv.org/abs/1709.07886) | topo | Código de treino que codifica dados no modelo | Modelo de ameaça igual ao nosso, mas não é benchmark nem usa LLM |

**O que nos diferencia:**
- O único canal é a saída. As tarefas laterais de rede e arquivo dos outros benchmarks deixam de
  existir aqui.
- Tarefas tabulares com pares benigno/vazante.
- Ataque verificado por **decodificador**, o que permite medir capacidade em bits. É uma
  generalização da "entrada de exploit" do cenário APPS backdoor.

### 2.6 Esteganografia e conluio (quanto o atacante consegue esconder)

| Referência | Venue · tier | Achado |
|---|---|---|
| [Secret Collusion among AI Agents](https://arxiv.org/abs/2402.07510) (Motwani et al.) | NeurIPS 2024 · topo | Capacidade ainda limitada, com salto no GPT-4; paráfrase e monitoramento têm limites |
| [Hidden in Plain Text](https://arxiv.org/abs/2410.03768) (Mathew et al.) | IJCNLP-AACL 2025 · PR | Esteganografia emerge sob otimização (RL) e **resiste à paráfrase** e à esteganálise passiva |
| [Preventing LMs From Hiding Their Reasoning](https://arxiv.org/abs/2310.18512) (Roger, Greenblatt) | 2023 · Pre | Paráfrase limita o canal a ~3 bits/KB |
| [Steganographic CoT under process supervision](https://arxiv.org/abs/2506.01926) (Skaf et al.) | 2025 · Pre | Penalizar strings leva o modelo a trocá-las e a generalizar o esquema de codificação |
| [Steganographic Potentials of LMs](https://arxiv.org/abs/2505.03439) (Karpov et al.) | ICLR 2025 WS · WS | Dar o algoritmo de codificação ao modelo **aumenta muito** a capacidade |
| [When CoT is Necessary, LMs Struggle to Evade Monitors](https://arxiv.org/abs/2507.05246) (Emmons et al.) | 2025 · Pre | Ofuscar exige muita ajuda |

**Implicação:** sem ajuda, os modelos de fronteira ainda escondem pouco. As nossas **sementes
dão o esquema ao atacante**, o que aumenta muito a capacidade dele. Paráfrase e juiz LLM não
fecham o canal na saída; o estimador de L2 é a vantagem que temos.

### 2.7 Recusa dos atacantes e acesso para pesquisa

- **Em enquadramento de CTF ou de controle, a recusa é rara.**
  - [Cybench](https://arxiv.org/abs/2408.08926) (ICLR 2025 oral): recusas raras, resolvidas com
    um *system prompt* de "CTF autorizado".
  - [NYU CTF Bench](https://arxiv.org/abs/2406.05590): nenhuma recusa ética em 200 desafios
    (venue a verificar).
  - ResearchArena: só o Claude Opus recusou, em 15 tarefas laterais.
- **Em pedido explícito de malware, a recusa é alta.**
  [MalwareBench](https://aclanthology.org/2025.acl-long.1350) (ACL 2025) mede ~61% de recusa,
  que cai para ~40% com jailbreak. [RedCode](https://arxiv.org/abs/2411.07781): agentes recusam
  menos quando o pedido vem em linguagem natural.
- **Métrica:** *False Refusal Rate* do [CyberSecEval 2](https://arxiv.org/abs/2404.13161).
- **Acesso:** o **Cyber Verification Program da Anthropic foi ampliado em 06/out/2026**, com três
  níveis e "reduced blocking classifiers" para profissionais qualificados
  ([anthropic.com/glasswing](https://www.anthropic.com/glasswing)) ✔.
- **OpenAI (segunda rodada):** o *Trusted Access for Cyber* virou **Daybreak** em ago/2026, em
  dois níveis ([doc oficial](https://learn.chatgpt.com/docs/cyber-safety) ✔):
  - **Blue**: "reduced refusals for authorized defensive workflows", incluindo revisão de código;
  - **Red**: aprovação separada, para validação de *exploits*.

  Aceita indivíduos com documento de identidade e organizações. O Cybersecurity Grant Program tem
  US$ 10 milhões em créditos de API (imprensa).
  **Risco:** em ago/2026 houve revogações por "erro técnico" para pesquisadores fora dos EUA e da
  Europa ([TechCrunch](https://techcrunch.com/2026/08/19/researchers-complain-that-openai-revoked-their-access-to-limited-cyber-program/)).
- **Google (segunda rodada):** o [**Fairwind Program**](https://deepmind.google/fairwind-program/)
  ✔ dá:
  - o Gemini 3.8 Flash Cyber, com "more permissive set of mitigations" (02/set/2026);
  - o **Gemini 4 Argon "without cyber guardrails"** (30/set/2026) a defensores aprovados.

  Aceita explicitamente **"academic labs focused on defensive benchmarking"**. Exige checagem de
  antecedentes e proíbe redistribuir.
- **Nenhum dos programas** menciona pesquisa de controle de IA ou de evasão de monitores. Eles
  relaxam salvaguardas de *cyber*. Para a batalha: pedir **como organização**, apresentar o
  trabalho como benchmarking defensivo, e contar com revogação súbita.

### 2.8 Conteúdo invisível contra revisores de código (segunda rodada)

**Resolução.**
- **O ataque funciona e já foi explorado em produtos reais.**
  - Gemini, Claude e Grok interpretam **tags Unicode** (U+E0000–E007F) como instruções. Modelos da
    OpenAI preferem binário em *zero-width*.
  - **Seletores de variação** dão 80–100% de sucesso de jailbreak em modelos abertos.
  - Casos em produção, 2025–2026:
    - Rules File Backdoor (Copilot e Cursor);
    - GitLab Duo, que apresentou uma MR maliciosa como segura;
    - CamoLeak no Copilot Chat (CVSS 9,6): código privado vazado caractere a caractere por imagens;
    - Jules;
    - *Skills* do Claude Code. Desde 10/02/2026 o Claude Code detecta e recusa.
- **O vetor mais comum nem é Unicode.** É a diferença entre o que o humano vê e o que o modelo
  recebe: comentários HTML ou markdown, `<picture>`, texto branco, instruções dentro de imagens.
- **Defesa recomendada (UTS #55): tornar visível e sinalizar, não normalizar em silêncio.**

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [Trojan Source](https://arxiv.org/abs/2111.00169) (Boucher, Anderson) | USENIX Sec 2023 · topo | Controles *bidi* e homóglifos fazem compilador e revisor lerem lógicas diferentes | Base do detector de *bidi* e homóglifos na L1 |
| [Bad Characters](https://arxiv.org/abs/2106.09898) (Boucher et al.) | IEEE S&P 2022 · topo | Uma injeção de caractere invisível já degrada o modelo; três quebram a maioria | Caractere invisível é sinal forte |
| [UTS #55: Unicode Source Code Handling](https://www.unicode.org/reports/tr55/) | Unicode 2024 · Rel | Recomenda **mostrar** *bidi* e *default-ignorables*; NFC/NFKC só em identificadores; "não normalizar literais em silêncio" | **A L1 sinaliza, não normaliza** |
| [Rules File Backdoor](https://www.pillar.security/blog/new-vulnerability-in-github-copilot-and-cursor-how-hackers-can-weaponize-code-agents) (Pillar, mar/2025) | Rel | *Zero-width* e *bidi* num arquivo de regras levam Cursor e Copilot a injetar `<script>` e omitir isso do chat | Arquivos de configuração dentro da imagem também passam pela L1 |
| [Scary Agent Skills](https://embracethered.com/blog/posts/2026/scary-agent-skills/) (Rehberger, fev/2026) | Rel | Tags em *Skills* levam a executar Bash; o *scanner* sinaliza > 10 tags consecutivas | Heurística barata e pronta |
| [Reverse CAPTCHA](https://arxiv.org/abs/2603.00164) (Graves) | 2026 · Pre | 5 modelos, 8.308 saídas; ferramentas aumentam a obediência ao *payload* invisível; cada fornecedor prefere uma codificação | Testar L3 com *payload* invisível, com e sem ferramentas |
| [Imperceptible Jailbreaking](https://arxiv.org/abs/2510.05025) (Gao et al.) | 2025 · Pre | Seletores de variação: ASR de 80–100% em 4 modelos abertos | Filtrar também seletores de variação, não só ZW e tags |
| [What You See Is Not Always What You Get](https://arxiv.org/abs/2412.08098) (Wen et al.) | APSEC 2025 · PR | Perturbações imperceptíveis degradam a compreensão de código pelos LLMs | Degrada o juiz mesmo sem injeção |
| [GitLab Duo remote PI](https://www.legitsecurity.com/blog/remote-prompt-injection-in-gitlab-duo) · [CamoLeak](https://www.legitsecurity.com/blog/camoleak-critical-github-copilot-vulnerability-leaks-private-source-code) (Legit) | 2025 · Rel | Revisor de código enganado; vazamento por um canal de saída "legítimo" (imagens) | **CamoLeak é exatamente o modelo de ameaça da L4** |
| [Trail of Bits: exploiting Copilot](https://blog.trailofbits.com/2025/08/06/prompt-injection-engineering-for-attackers-exploiting-github-copilot/) | ago/2025 · Rel | Instrução escondida em `<picture>` faz o agente pôr *backdoor* no `uv.lock`, que ninguém revisa | L1/L3 precisam olhar *lockfiles* |
| [AWS: Unicode character smuggling](https://aws.amazon.com/blogs/security/defending-llm-applications-against-unicode-character-smuggling/) | set/2025 · Rel | Remover tags de forma recursiva, inclusive *surrogates* órfãos que podem ser remontados | Receita de implementação |
| Ghostcommit ([imprensa](https://bleepingcomputer.com/news/security/ghostcommit-hides-prompt-injection-in-images-to-fool-ai-agents-steal-secrets), jul/2026) **(a verificar; só imprensa)** | Rel | Instrução num PNG; o `.env` vaza como **lista de inteiros numa constante**, sem que os scanners de segredo detectem | Semente de vazamento codificado na saída legítima |

### 2.9 Debate e crítico para revisão de código (segunda rodada)

**Resolução.**
- **Para código e backdoor, a evidência a favor do debate é fraca ou negativa.**
  - Kenton et al. (NeurIPS 2024): o debate ganha quando há **assimetria de informação**; sem ela,
    caso de código, o resultado é misto.
  - Elasky et al. (2026) ✔: o debate só ajuda quando o **crítico classifica melhor que o juiz**, e
    **um único crítico independente recupera quase todo o ganho**. As réplicas não acrescentam
    nada.
  - Num experimento informal com backdoors no APPS, deixar o autor "se defender" **piorou** o
    recall de 70,6% para 41,2%.
- **No DNAT, a assimetria de informação vem da L2** (canários, D/D′), não de um debate.

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [On scalable oversight with weak LLMs judging strong LLMs](https://proceedings.neurips.cc/paper_files/paper/2024/hash/899511e37a8e01e1bd6f6f1d377cc250-Abstract.html) (Kenton et al.) | **NeurIPS 2024** · topo | Debate > consultoria em todas as tarefas; contra resposta direta, ganha só com assimetria de informação | A informação que o juiz não tem é a evidência da L2 |
| [Debating with More Persuasive LLMs](https://proceedings.mlr.press/v235/khan24a.html) (Khan et al.) | ICML 2024 · topo | Juízes não especialistas: 76% com debate contra 48% de base | Vale com assimetria de informação, não diretamente para código |
| [Debate Helps Weak Judges Reward Stronger Models](https://arxiv.org/abs/2605.27483) (Elasky et al.) ✔ | 2026 · Pre | CodeContests+: ganho só quando o crítico tem vantagem; nulo nos demais pares; **um crítico único basta**. Números do corpo (a verificar): +7,3 p.p. de macro-F1 no melhor par | Usar **um crítico independente** com a evidência da L2, não debate em várias rodadas |
| [Trusted Debate for AI Control](https://neurips.cc/virtual/2025/loc/mexico-city/133159) (Al Dahik et al.) | NeurIPS 2025 WS · WS | Dois agentes confiáveis debatem se o código tem backdoor; sem números na página | Desenho próximo da L3, sem evidência quantitativa |
| [When the smarter AI lies better](https://www.lesswrong.com/posts/mDmsNJ9JxHEpBYDvd/when-the-smarter-ai-lies-better-can-debate-based-oversight) (Kraak et al.) | LessWrong 2025 · Rel | Backdoors no APPS (n efetivo = 73): debate com recall de 41,2% contra 70,6% do monitoramento | Não dar voz ao autor da app diante do juiz |
| [VulTrial: mock-court](https://arxiv.org/abs/2505.10961) (Widyasari et al.) | ICSE 2026 · topo | Papéis de promotor e defensor dobram o acerto por par no PrimeVul (81 contra 40 de 435), com ~4× o custo | O patamar absoluto continua baixo |

### 2.10 Benchmarks de juízes de código, com e sem execução (segunda rodada)

**Resolução.**
- **Sem execução:** os melhores modelos de raciocínio chegam a ~80–86% de acerto pareado. Modelos
  sem raciocínio ficam abaixo de 60%, e juízes *fine-tunados* e *reward models* em 50–63%.
  **Trocar a ordem das respostas muda o acerto em até 14 p.p.**
- **Com execução, o ganho depende de como ela entra.**
  - Com andaime agêntico, o ganho é grande no APPS.
  - Uma *sandbox* crua é **neutra ou negativa** sem treino específico.
  - Funciona com RL (TIR-Judge) ou com busca (MCTS-Judge).
- **Lacuna:** todos medem **correção funcional**. Não há benchmark de juiz para backdoor ou
  exfiltração com execução, que é o que a nossa batalha mede.

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [CodeJudgeBench](https://arxiv.org/abs/2507.10535) (Jiang et al.) | 2025 · Pre | 5.352 pares, 26 juízes; Gemini-2.5-Pro ~82%; juízes treinados 53–63%; **viés de posição de até 14%** | L3 com modelo de raciocínio, avaliado nas duas ordens |
| [JudgeBench](https://arxiv.org/abs/2410.12784) (Tan et al.) | ICLR 2025 · topo | Na parte de código (42 pares): o1-preview 85,7%; GPT-4o ~60%; *reward models* 50% | Juízes especializados não servem para código |
| [Can External Validation Tools Improve Annotation Quality for LLM-as-a-Judge?](https://arxiv.org/abs/2507.17015) (Findeis et al., Apple) ✔ | **ACL 2025** · topo | Ferramentas externas melhoram "em muitos casos, não em todos" ✔. Números do corpo (a verificar): no APPS, de 31% para 71% (GPT-3.5) e de 38% para 72% (GPT-4o) com agente de execução; até −9 p.p. no HumanEval | **Evidência de execução estruturada ajuda; ferramenta crua não** |
| [TIR-Judge](https://arxiv.org/abs/2510.23038) (Xu et al.) | ICLR 2026 · topo | +6,4% e +7,7% com RL; **execução sem treino**: Qwen3-8B cai de 64,9 para 59,4 | Não esperar ganho só por dar *sandbox* ao L3 |
| [MCTS-Judge](https://arxiv.org/abs/2502.12468) (Wang et al.) | 2025 · Pre | Busca em tempo de teste leva de 41% para 80% | Alternativa de custo para a L3 |
| [CodeJudge](https://arxiv.org/abs/2410.02184) (Tong, Zhang) | EMNLP 2024 · topo | Juiz semântico sem testes; Llama-3-8B supera método com GPT-3.5 | Referência histórica |

### 2.11 Controle de fluxo de informação para agentes: CaMeL e FIDES (segunda rodada)

**Resolução.**
- **CaMeL e FIDES dão garantias por construção para agentes LLM**, mas cobrem **sigilo
  explícito**. Fluxos implícitos e canais laterais ficam fora do escopo, e o próprio CaMeL admite
  ~1 bit vazado por exceção.
- **Duas ideias encaixam na L0/L4:**
  - **rótulo do dono propagado até uma política de egresso**;
  - **saída tipada de baixa capacidade como parte do rótulo** (FIDES).
- **Mas a ameaça do DNAT é justamente o fluxo implícito e semântico pela saída legítima**, que
  essas garantias excluem. Isso justifica o teste relacional da L2 e deve ser dito com clareza no
  artigo.

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [CaMeL: Defeating Prompt Injections by Design](https://arxiv.org/abs/2503.18813) (Debenedetti et al., GDM) | 2025 · Pre (venue a verificar) | Um LLM planeja código Python restrito, outro LLM sem ferramentas faz o *parsing*, e um interpretador próprio checa as *capabilities*. Resolve 77% das tarefas do AgentDojo (contra 84% sem defesa), com ataques de 300 para 0, a ~2,8× o custo em *tokens* | IFC completo em Python exigiu subconjunto e interpretador próprios: não serve para imagens OCI arbitrárias. O modo STRICT inspira a L4 |
| [FIDES](https://arxiv.org/abs/2505.23643) (Costa et al., Microsoft) | 2025 · Pre | Reticulado integridade × confidencialidade; injeções de 163 para 1 com políticas; só "explicit secrecy" | **Esquema de saída de baixa capacidade conforme a tag do dono** |
| [Permissive Information-Flow Analysis for LLMs](https://arxiv.org/abs/2410.03055) (Siddiqui et al.) | 2026 · Pre | Propaga o rótulo só das entradas que de fato influenciaram a saída | Análogo à variação do segredo |
| [RTBAS](https://arxiv.org/abs/2502.08966) (Zhong et al.) | 2025 · Pre | IFC com triagem de dependência por LM-juiz; bloqueia os ataques dirigidos do AgentDojo com ~2% de perda | LLM como estimador de dependência |
| [Design Patterns for Securing LLM Agents](https://arxiv.org/abs/2506.08837) (Beurer-Kellner et al.) | 2025 · Pre | 6 padrões, entre eles Dual LLM e Context-Minimization | Isolar a L3 do texto do atacante |
| [APPA: Recoverable IFC](https://arxiv.org/abs/2607.24625) (Kravchenko et al.) | 2026 · Pre | Monitor de referência e saídas limitadas por esquema; 0 ataques em 1.320 episódios protegidos | Saída limitada por esquema como fronteira |

### 2.12 Taint dinâmico em Python e sucessores do LLMDFA (segunda rodada)

**Resolução.**
- **Não existe taint dinâmico maduro para Python que atravesse código nativo.**
  - DynaPyt é framework de pesquisa.
  - O IAST da Datadog está em *preview* e "não propaga taint em código nativo" (numpy, Numba, JAX,
    TF).
  - TaintMonkey é projeto estudantil só para Flask.
  - PyT está descontinuado.

  **Para apps de dados em numpy/pandas, taint em nível de byte é impraticável**, o que reforça o
  teste relacional caixa-preta da L2.
- **Os sucessores do LLMDFA/IRIS quase não cobrem Python** (NESA, MoCQ, AdaTaint miram Java, C,
  JS, PHP). Avaliar em Python já é contribuição.

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [DynaPyt](https://2022.esec-fse.org/details/fse-2022-research-papers/48/DynaPyt-A-Dynamic-Analysis-Framework-for-Python) (Eghbali, Pradel) | FSE 2022 · topo | *Overhead* de 1,2–16×; exemplo de taint para SQLi | Protótipo, não produção |
| [Datadog IAST Python](https://docs.datadoghq.com/security/code_security/iast/setup/python/) | Doc · Rel | "Não propaga taint em código nativo"; conflita com Numba, JAX, TorchScript e TF | O taint quebra justamente nas bibliotecas de dados |
| [Fuzzingbook: Tracking Information Flow](https://www.fuzzingbook.org/html/InformationFlow.html) | Livro · Rel | Perde o taint em funções C e na conversão para número | Limites do taint em Python |
| [TaintMonkey](https://pypi.org/project/taintmonkey/) · [PyT](https://github.com/python-security/pyt) | Rel | Só Flask, um mantenedor · descontinuado, aponta para o Pysa | Descartar |
| [Cell-Level Provenance in Numpy](https://arxiv.org/abs/2506.18255) (Zhao, Krishnan) | 2025 · Pre | Proveniência por célula com um *dtype* em C; a versão em Python puro não escala | A única via encontrada dentro do numpy; protótipo |
| [NESA (ex-LLMSA)](https://arxiv.org/abs/2412.14399) (C. Wang et al.) | 2026 · Pre | Sucessor neuro-simbólico do LLMDFA; F1 0,72 no TaintBench (Android) | Não mira Python |
| [MoCQ](https://arxiv.org/abs/2504.16057) (P. Li et al.) · [AdaTaint](https://arxiv.org/abs/2511.04023) (S. Lin) | 2025–26 · Pre | LLM gera consultas CodeQL/Joern ou infere fontes e sumidouros; −43,7% de falsos positivos (C) | Ideia replicável para *specs* do Pysa; **sem Python** |
| [PyFlow](https://arxiv.org/abs/2608.07026) (Gu et al.) | 2026 · Pre | IFDS interprocedural para Python; melhor recall entre 9 ferramentas, entre elas CodeQL e Pysa (sem números na página) | Candidato para a L1 |
| [Vulnhuntr](https://github.com/protectai/vulnhuntr) (Protect AI) | Rel | LLM monta a cadeia de entrada a sumidouro só em Python; achou CVEs reais | Linha de base de "LLM faz *dataflow* em Python" |

### 2.13 Esteganografia numérica na saída: detectar ou desarmar? (segunda rodada)

**Resolução.**
- **Não há esteganálise que funcione para saídas pequenas** (algumas médias, uma tabela, um
  CSV). A esteganálise de bits menos significativos (LSB) só funciona com **milhões** de números,
  como os pesos de um modelo, e mesmo assim:
  - precisa de taxa de embutimento ≥ 25%;
  - perde para embutimento com chave ou espalhado.
- **O que funciona é desarmar: canonicalizar a saída.** Sobrescrever, zerar ou quantizar os bits
  baixos e reserializar em formato fixo custa quase nada.
- **Arredondar não zera o canal.** Se o app controla a função, ele escolhe de que lado da
  fronteira de arredondamento cai.
  - **Cálculo do levantamento:** a capacidade residual é ≈ log₂(2τ/g + 1) bits por número, com τ a
    tolerância e g a granularidade. Com τ ≈ g/2, sobra **~1 bit por número**.
  - **Cem números ≈ 100 bits**, o bastante para alguns CPFs.
- **O juiz LLM não enxerga sinal escondido em números.** No *subliminal learning*, um classificador
  LLM fica no acaso (47–53%).

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [ML Models that Remember Too Much](https://arxiv.org/abs/1709.07886) (Song et al.) ✔ (§4.1, §7) | CCS 2017 · topo | 18–22 dos 23 bits de fração do float32 servem de canal sem perda de acurácia; **trocar os bits baixos por ruído "destrói" a informação sem custo**; codificação por correlação ou sinal e *capacity abuse* não aparecem nos bits baixos | Canonicalizar é barato; os canais que sobram (valor, correlação) exigem D/D′ |
| [Transpose Attack](https://arxiv.org/abs/2311.07389) (Amit et al.) ✔ | NDSS 2024 · topo | Modelo treinado "ao contrário" esconde outro que exfiltra dezenas de milhares de amostras | O canal é o comportamento do modelo; arredondar não resolve |
| [Secret Stealing via Supply-Chain Model Code Backdoors](https://arxiv.org/abs/2604.27426) (Li et al.) ✔ | EMNLP 2026 segundo o arXiv · topo | Código malicioso faz o modelo **memorizar segredos durante LoRA local**; ASR > 98%; evade filtro semântico, auditoria de código e perplexidade | L1 e L3 falham contra memorização dirigida na família ML |
| [Model X-Ray](https://arxiv.org/abs/2409.19310) · [NeuPerm](https://arxiv.org/abs/2510.20367) (Gilkarov, Dubin) ✔ | JISA 2026 · PR; 2026 · Pre | Esteganálise de pesos confiável só com ≥ 25% de embutimento. **Permutar neurônios** zera o canal do MaleficNet com custo ~0 | **Princípio: transformar a saída em representação canônica equivalente** (ordem, formato fixo) |
| [Disarming Steganography Attacks Inside NN Models](https://arxiv.org/abs/2309.03071) (Dubin) ✔ | 2023 · Pre | 100% de prevenção com quantização Qint8 ou K-LRBP, perda mínima | "Desarmar em vez de detectar" |
| [On Significance of the LSBs for DP](https://www.microsoft.com/en-us/research/wp-content/uploads/2012/10/lsbs.pdf) (Mironov) ✔ | CCS 2012 · topo | O Laplace em ponto flutuante é "poroso": uma base de 18 mil registros foi reconstruída no PINQ com < 1000 consultas. **Arredondar em grade fina é inseguro**; o *snapping* é provadamente DP | A granularidade tem de acompanhar a variabilidade legítima |
| [Timing and Floating-Point Attacks on DP](https://arxiv.org/abs/2112.05307) (Jin et al.) ✔ | IEEE S&P 2022 · topo | Ataque de ponto flutuante a DP-SGD com até 92,56% de sucesso; ataque de **tempo** até 99,65% | Arredondar não basta se o tempo vaza; fixar ou ofuscar o tempo (E2c S3) |
| [Watermarking Relational Databases](https://www.vldb.org/conf/2002/S05P03.pdf) (Agrawal, Kiernan) ✔ | VLDB 2002 · topo | Marca em bits de atributos numéricos escolhidos por chave secreta: **sem a chave, indetectável** | Esteganografia tabular com chave já existe; só sobrescrever os bits baixos vence |
| [Chiron](https://arxiv.org/abs/1803.05961) (Hunt et al.) ✔ · [Ryoan](https://www.usenix.org/conference/osdi16/technical-sessions/presentation/hunt) ✔ | 2018 · Pre; OSDI 2016 · topo | Código de treino não confiável em SGX: **não há "mitigação genérica"** para modelo malicioso; recusar terminar, número de iterações e tempo vazam "dezenas de bits" | **Precedente direto do DNAT.** Aborto, *timeout*, código de saída e qualidade entram no orçamento da L4 |
| [Airavat](https://www.cs.utexas.edu/lasr/paper.php?uid=31) ✔ | NSDI 2010 · topo | MAC + DP para MapReduce não confiável, *overhead* ≤ 32% | Alternativa forte: a **plataforma** faz a agregação final e o arredondamento, não o app |

### 2.14 Auditoria de consultas: negar também vaza (segunda rodada)

**Resolução.**
- **Kenthapadi, Mishra e Nissim** (PODS 2005, "Simulatable auditing") ✔ e a versão longa no JCSS
  2013, "Denials leak information": um auditor que **nega com base nos dados verdadeiros vaza pela
  própria negação**. Ele só é seguro se for **simulável**, isto é, se a decisão puder ser
  computada sem olhar os dados.
- **Mardziel et al.** generalizam isso para **programas arbitrários**. Rejeitam se *algum* segredo
  possível levaria o conhecimento do atacante acima do limiar.
- **Não há trabalho de 2020–2026** que aplique auditoria simulável a clean rooms ou a execuções
  repetidas de programas: **lacuna que o DNAT pode ocupar**.
- A versão moderna do problema: **filtros de saída viram canal** (Debenedetti, USENIX Sec 2024).

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [Simulatable auditing](https://seclab.cs.georgetown.edu/bibliography/DBLP_conf/pods/KenthapadiMN05.html) (Kenthapadi, Mishra, Nissim) ✔ · [Denials leak information](https://doi.org/10.1016/j.jcss.2013.06.004) | PODS 2005 · topo; JCSS 2013 · PR | Auditores *offline* não servem *online* porque a negação vaza; define o auditor simulável | **Toda negação da L4** (k mínimo, PII, orçamento) deve ser simulável ou contada como saída |
| [Knowledge-based policies](https://www.cs.umd.edu/~mwh/papers/beliefpol-extended.pdf) (Mardziel, Magill, Hicks, Srivatsa) ✔ | J. Computer Security 2013 (CSF 2011) · PR | Rastreia a crença do consultante por interpretação abstrata probabilística; rejeitar com base no segredo real pode revelar o segredo inteiro | **Modelo direto para o orçamento da L4** entre execuções |
| [Adaptive side-channel attacks](https://doi.org/10.1145/1315245.1315282) (Köpf, Basin) | CCS 2007 · topo | Vazamento acumulado em n execuções adaptativas | Limitar execuções do mesmo comprador sobre o mesmo dado |
| [Privacy Side Channels in ML Systems](https://arxiv.org/abs/2309.05610) (Debenedetti et al.) ✔ | USENIX Sec 2024 · topo | **Filtros anti-memorização** permitem exfiltrar chaves do treino | **O portão L4 vira oráculo** se a decisão de bloquear depende do dado |
| [Auditing Boolean attributes](https://doi.org/10.1145/335168.335210) (Kleinberg et al.) · [Chin](https://doi.org/10.1145/5925.5928) | PODS 2000 · JACM 1986 · topo | Auditoria exata de somas é computacionalmente difícil | Preferir orçamento conservador a auditoria exata |

---

## 3. Consensos da área (síntese cruzada)

1. **Monitor LLM cai diante de atacante adaptativo que conhece o monitor.** Exemplos: Terekhov;
   Loughridge (0,87 → 0,41); Kutasov (reamostragem cai para 17%); ALIBI (> 90%). Avaliação sem
   atacante adaptativo superestima a defesa.
2. **Injeção de prompt no artefato julgado é o ataque mais barato contra LLM-juiz**, e nenhuma
   defesa isolada domina (RobustJudge, JudgeDeceiver, One Token).
3. **Diversidade de sinais vale mais que escala** (Koran 2,4×, Hua, Async Control,
   CTRL-ALT-DECEIT). Os LLMs de fronteira erram cada vez mais do mesmo jeito (Goel), então a
   diversidade tem de vir **de fora dos LLMs**.
4. **Mais texto cru não ajuda; evidência extraída e estruturada ajuda** (Arike "menos é mais",
   EaE +16,8 pp, Factor(T,U) 41 → 63%, fatias de taint 75 → 87%).
5. **LLMs triam bem e localizam mal** (F1 0,48 por linha em Ryan; Ullah: renomear variáveis
   muda o veredito em 26%). O padrão é pré-filtro barato seguido de LLM (SocketAI, MalGuard).
6. **Hipertestes de não interferência não dão alarme falso**: um par D/D′ que diverge é uma
   testemunha concreta. Quando a dependência é legítima (agregados), o oráculo precisa ser
   quantitativo.
7. **Estimar vazamento em caixa-preta é viável, mas sem cota universal de amostras.** É preciso
   um conjunto **finito** de segredos (Eureka), e o custo prático vai de centenas a milhões de
   execuções.
8. **k mínimo não protege contra diferença nem contra reconstrução.** Concordam a literatura
   (Dinur–Nissim, Censo, downcoding) **e os próprios fornecedores** (AWS, Google, Snowflake). A
   única defesa que compõe com garantia é ruído calibrado com orçamento (DP).
9. **Métricas de similaridade e supressão minimal viram oráculo** (Ganev, Cohen).
10. **Métrica padrão em controle:** TPR com FPR fixo e baixo (1%), AUROC e "sucesso não
    detectado". Acurácia não serve.

## 4. Controvérsias e lacunas

| Tema | Lado A | Lado B | Leitura |
|---|---|---|---|
| **Comentários** | Thornton: efeito pequeno com *templates* fixos; não remover | ALIBI (> 90%), Flashboom (iscas sem comentário), CoT Red-Handed (racionalização) | A diferença parece estar na **adaptatividade** do atacante; ninguém reconciliou os dois lados no mesmo conjunto de dados |
| **Mais ou menos evidência** | Arike: menos é mais; CoT enganosa | ResearchArena: executar e sondar o artefato ajudou muito (suspeição 92 vs. 4); Liao: execução eleva o monitor fraco | O que decide é a **origem** da evidência: texto do atacante atrapalha, evidência de ferramenta confiável ajuda |
| **Reamostragem** | Ctrl-Z, Kutasov: ajuda contra atacante ingênuo | Terekhov: vira best-of-n contra injeção | Reamostrar **só para incriminar** |
| **Weak-to-strong** | Kale, Baker: otimistas com *scaffold* | Engels: 10% em backdoor de código com gap de 400 Elo | O LLM barato sozinho não basta |
| **Viés de família** | Autopreferência (Panickssery) sugere leniência com a própria família | Pinto: calibrado na família do atacante, detecta **mais** | Sem estudo específico de código vazador |

**Lacunas que nos favorecem (oportunidades):**
- **Ninguém mediu um monitor LLM com evidência dinâmica de ferramenta confiável** (testes
  diferenciais, estimativa de bits) contra atacante adaptativo. O mais próximo é Liao, só com
  monitores isolados. **É exatamente a nossa pergunta de pesquisa.**
- A literatura de controle trata exfiltração por **rede ou ações**. Vazamento pela **saída
  legítima** com estimativa quantitativa como evidência não foi estudado.
- **Esteganografia numérica** em agregados não foi estudada com LLMs; o precursor é Song'17.
- Não há estimador com cota finita para n ≈ 20–50 em programas reais.

**Lacunas que nos expõem (riscos):**
- O Juiz é público e determinístico, então o atacante faz busca offline ilimitada. Quanto do
  protocolo pode continuar secreto (canários, sementes de D′, escolha de juízes) sem quebrar a
  atestação?
- Ataques de diferença entre execuções **não têm solução sem DP**. A **atualização do dataset
  pelo dono** (D_t → D_{t+1}) já é um par diferencial natural (análise do levantamento).
- Taint dinâmico para Python é imaturo (DynaPyt; hipertestes só em Java e C).

## 5. O que isso sugere para o Juiz (insumo para decisão, não decisão)

**Reforça o que já temos**
1. **Defensor com evidência mecânica** é a aposta certa e está na lacuna (Liao, Hua, Koran,
   Engels). A tese do artigo pode ser formulada como "evidência dinâmica confiável + LLM barato
   contra atacante adaptativo".
2. **L1 barata antes do LLM** (SocketAI e MalGuard cortam 60–78% do custo). Vamsa e SemTaint
   indicam como checar `transformacao` e como gerar *specs* do Pysa.
3. **D/D′ como hipertest:** é testemunha sem alarme falso e deve prevalecer sobre L3 quando os
   dois divergem.
4. **Batalha como control evaluation, reportando TPR@1%FPR**, com *safety case* de exfiltração
   no estilo Korbak como modelo de argumento.
5. **Vários juízes**, agregando por **máximo de suspeição** (ou por regra Neyman-Pearson), nunca
   "aprova se algum aprovar".

**Exige ajuste**
6. **Atacante adaptativo e com simulador do Juiz** na batalha, com segurança reportada com e sem
   conhecimento do Juiz. Considerar uma rodada pequena com **red team humano** (LinuxArena).
7. **Qualificar "não remover comentários".** Rodar L3 duas vezes, com o código original e com
   comentários e strings normalizados. A **divergência entre os dois vereditos vira evidência**.
   Todo texto vindo da app, inclusive o que L1/L2 ecoam no relatório, deve ser tratado como dado
   não confiável.
8. **Reamostrar só para incriminar.** Limitar e registrar ressubmissões por desenvolvedor, porque
   ressubmeter variantes é um best-of-n.
9. **Segredos do protocolo:** canários, sementes de D′ e sorteio de juízes gerados na execução,
   com *commitment* da semente no recibo, para manter o veredito auditável.
10. **Variação do segredo (L2):**
    - sortear de um **conjunto pequeno e repetido** de valores (4–8) ou usar ganho com tolerância
      (Romanelli). Com valores únicos e n ≈ 20–50, o kNN tende a falso negativo;
    - **variar também o fundo do dataset**, senão todo `agregado:k` legítimo parece vazamento
      (a saída é injetiva no canário);
    - usar teste sequencial *anytime-valid* em vez de n fixo.
11. **Não vender o k mínimo como defesa contra diferença.** Opções: `agregado:k` + `dp:ε`
    opcional (como na AWS); orçamento por (comprador, dataset, versão); versões de app
    imutáveis. Declarar no artigo, junto com a atualização do dataset como par diferencial.
12. **Portão binário e pouco informativo:** sem supressão minimal, sem score exposto (Ganev,
    Cohen).
13. **Ampliar o catálogo V1–V6** com:
    - injeção **otimizada** e adaptativa (JudgeDeceiver, ALIBI);
    - código-isca (Flashboom);
    - inchaço de contexto (CASHEWS);
    - **texto que provoca recusa do Juiz** (Hades);
    - nomes plausíveis e *model priors* (SLEIGHT);
    - vazamento gradual entre versões (Hills);
    - esteganografia em parâmetros e predições para a família ML (Song'17).
14. **Canários desenhados para o canal de saída:** prefixo plausível com marca de alta entropia
    (Canary's Echo). PII por regras + LLM + canários do dono (REDACT).

**Novo, a considerar**
15. Implementar a batalha como um *setting* do **ControlArena/Inspect** (MIT): dá
    comparabilidade imediata com BigCodeBench-Sabotage e SHADE-Arena.
16. Proteger o benchmark contra contaminação: dados cifrados em repouso e GUID canário, como no
    SLEIGHT-Bench.
17. Se L3 for *fine-tunado*, os dados e pesos do Juiz precisam da mesma proveniência in-toto/SLSA
    das apps (BadJudge).

**Da segunda rodada (§2.8–§2.12)**

18. **A L1 detecta, não normaliza** (UTS #55). Tags Unicode, *zero-width*, *bidi*, seletores de
    variação, comentários HTML ou markdown ocultos e texto em imagem são **sinal forte**, que
    escala ou reprova. Vale para **todos** os artefatos da imagem: código, notebooks, *lockfiles*,
    arquivos de regras e PNGs. A L3 recebe a visão renderizada junto com os bytes crus, porque
    cada fornecedor lê uma codificação diferente.
19. **Um crítico, não um debate.** Um único crítico independente, munido da evidência da L2,
    captura quase todo o ganho (Elasky). **Não dar voz ao autor da app** diante do Juiz, porque
    isso piora o recall.
20. **Evidência estruturada, não *sandbox* crua, para a L3.** A execução ajuda quando chega
    estruturada (Findeis); acoplada sem treino, é neutra ou negativa (TIR-Judge). Isso reforça o
    desenho L2 → L3. Avaliar nas duas ordens e reportar o viés de posição (até 14 p.p.).
21. **IFC (CaMeL, FIDES) inspira a L0/L4, mas não substitui a L2.** O rótulo do dono vira política
    de egresso, e a **capacidade do esquema de saída entra na tag**. O artigo deve dizer que essas
    garantias cobrem só fluxo explícito, e que a nossa ameaça é o fluxo implícito pela saída
    legítima.
22. **Não prometer taint dinâmico na L2.** O taint em Python quebra em código nativo. O teste
    diferencial caixa-preta é a escolha certa; taint estático (Pysa, CodeQL, PyFlow) fica como
    sinal barato da L1.
23. **A batalha preenche outra lacuna:** não há benchmark de juiz de código para backdoor ou
    exfiltração com execução. Reportar métricas comparáveis (acerto pareado, viés de posição,
    custo). CamoLeak e Ghostcommit servem de sementes (segredo como inteiros ou imagens na saída
    legítima).
24. **A L4 canonicaliza a saída numérica ela mesma** (§2.13):
    - arredondamento ou *snapping* para uma granularidade g ligada à variabilidade legítima;
    - reserialização em formato fixo, sem floats livres;
    - ordem canônica.

    Os ~1–2 bits residuais por número entram no orçamento; por exemplo, limitar quantos números
    cada saída pode ter. **Não confiar em esteganálise.** Rodar o estimador da L2 **depois** do
    arredondamento da plataforma mede o que sobra.
25. **Teste de consistência de sensibilidade na L2** (proposta do levantamento): com
    `agregado:k`, trocar um registro e checar se |f(D) − f(D′)| cabe na sensibilidade declarada
    (por exemplo, (b − a)/n para uma média). Bits baixos que mudam além disso, ou que não mudam
    quando deveriam, indicam canal.
26. **Negações simuláveis** (§2.14). Bloqueios da L4 por k mínimo, PII ou orçamento precisam ser
    decididos a partir de informação pública (programa, esquema, saídas já liberadas) ou contados
    como saída e debitados do orçamento. Aborto, *timeout*, código de saída e tempo também são
    canais (Chiron: "dezenas de bits").
27. **L3 consultivo, não barreira.** Com injeção, o GPT-4.1 deu nota 0 a 375 backdoors; iscas
    cegam auditores pequenos; o LLM não vê sinal em números. O veredito de reprovação precisa
    poder vir só de L1/L2/L4.
28. **Repertório extra do atacante na batalha:**
    - LSB numa média;
    - 1 bit por número pela escolha do lado do arredondamento;
    - *value-mapping*;
    - **memorização dirigida** em apps da família ML (Song, Transpose, Secret Stealing).

    Reportar AUROC e FNR@5%FPR por camada, como Liao.
29. **Acesso aos modelos atacantes:** CVP (Anthropic), Daybreak Blue (OpenAI) e Fairwind (Google,
    aceita laboratórios acadêmicos de benchmarking defensivo). Pedir como organização.

## 6. Ferramentas, código e benchmarks reutilizáveis

| Recurso | Link | Licença / estado |
|---|---|---|
| ControlArena (UK AISI + Redwood), sobre o Inspect | https://github.com/UKGovernmentBEIS/control-arena | MIT. Settings Apps, Bash, BashArena, BigCodeBench, AgentDojo, Data Poisoning…; **nenhum de exfiltração pela saída** |
| BigCodeBench-Sabotage (CoT Red-Handed) | https://github.com/cotredhanded/code | MIT |
| SLEIGHT-Bench | https://github.com/safety-research/sleight-bench | MIT; dados cifrados com GUID canário |
| BashArena | https://github.com/redwoodresearch/basharena_public | licença a verificar |
| CTRL-ALT-DECEIT | https://github.com/TeunvdWeij/ctrl-alt-deceit | licença não informada |
| AgentDojo | https://github.com/ethz-spylab/agentdojo | MIT |
| RedCode | https://github.com/ai-secure/redcode | código MIT, dados CC BY 4.0 |
| Dataset de pacotes maliciosos (DataDog) | https://github.com/DataDog/malicious-software-packages-dataset | Apache-2.0; ~30 mil pacotes |
| fbleau | https://github.com/gchers/fbleau | MIT; Rust com bindings Python |
| QFuzz | https://github.com/yannicnoller/qfuzz | Apache-2.0; Java |
| NIFuzz | https://github.com/DanBlackwell/NIFuzz | licença não declarada; C |
| DP-Auditorium (Google) | https://github.com/google/differential-privacy/tree/main/python/dp_auditorium | licença a verificar |
| RepoAudit | https://github.com/PurCL/RepoAudit | licença Purdue |
| ACRO / SACRO | https://github.com/AI-SDC/ACRO | MIT |
| Flashboom | https://github.com/oxygen-hunter/Flashboom | licença não informada |
| Calibration-family overfit | https://github.com/digdoug/calibration-family-overfit | licença a verificar |

## 7. Correções na nossa base

- **Thornton (`thornton2026fool` no `refs.bib` e JUIZ §7).** O título no arXiv 2602.16741 é *"Can
  Adversarial Code Comments Fool AI Security Reviewers — Large-Scale Empirical Study of
  Comment-Based Attacks and Defenses Against LLM Code Analysis"*. Há uma só versão (v1,
  18/fev/2026), sem venue: citar como preprint ✔. O título "LLM Code Reviewers Are Harder to Fool
  Than You Think", que está no bib, não é o do registro.
- **Ctrl-Z e AI Control:** sem mudança. Notar que Terekhov e Kutasov qualificam a reamostragem.

## 8. Lacunas de cobertura deste levantamento

**A segunda rodada (2026-10-20)** cobriu:
- injeção invisível (§2.8);
- debate (§2.9);
- juízes de código com execução (§2.10);
- IFC para agentes (§2.11);
- taint em Python (§2.12);
- esteganografia numérica (§2.13);
- auditoria de consultas (§2.14);
- programas de acesso da OpenAI e do Google (§2.7).

Também conferiu no corpo dos artigos os números de Liao, Terekhov e Flashboom (§2.1, §2.2).

**Continuam em aberto (a verificar):**
- venue do CaMeL e do NYU CTF Bench;
- licenças de BashArena, CTRL-ALT-DECEIT, DP-Auditorium e RobustJudge;
- Ghostcommit, conhecido só pela imprensa;
- a campanha "Hades" (Socket), só por fonte secundária;
- termos atuais do Cybersecurity Grant Program da OpenAI (o site openai.com devolve 403).
