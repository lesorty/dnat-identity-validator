# Avaliação de aplicações contra vazamento de dados: arcabouço de leitura

**Data:** 2026-10-20 · **Formato:** um paper por linha, com a contribuição em uma frase e, quando ajuda,
o uso no DNAT depois de "→". ✔ quer dizer que a referência foi conferida na página primária (ou no
registro do DOI, quando a editora barrou o acesso); sem ✔, a referência existe, mas não foi aberta
nesta rodada. [$] marca o que dá para aplicar barato, em CPU e sem treino. **(01)** indica que o
trabalho já está detalhado em [01](01_juiz_seguranca_apps.md).

**Pergunta que guia a leitura.** Antes de liberar a app e na hora de entregar o resultado, decidir:
- **quais dados saem** da execução;
- se a saída é **coerente com o assunto, o contexto e a finalidade do dataset** ou se é **maliciosa**.

A decisão combina análise **estática** com análise **agêntica** (LLM com ferramentas). No DNAT o
container roda sem rede, então o canal que sobra é a saída legítima.

**Método.** Seis levantamentos em paralelo, um para cada tema:
1. fundamentos e análise estática;
2. dinâmica e caixa-preta;
3. agêntica e LLM;
4. finalidade e contexto;
5. controle de saída;
6. plataformas vizinhas e benchmarks.

Venues corrigidas na fonte ficam anotadas na própria linha. **Nada aqui é decisão.**

**Leitura mínima: comece por estes 12**
1. Sabelfeld & Myers, *Language-based Information-Flow Security* (JSAC 2003), e Sabelfeld & Sands,
   *Declassification* (JCS 2009): o vocabulário. Toda saída útil revela algo, então declara-se o que
   pode sair.
2. Smith, *On the Foundations of Quantitative Information Flow* (FoSSaCS 2009): medir o vazamento em bits.
3. Clarkson & Schneider, *Hyperproperties* (JCS 2010): por que uma execução não decide e o par D/D′ decide.
4. Gruner, Brust & Zeller, *Information Flow Fuzzing* (TOSEM 2025): o oráculo "mudei só o segredo e a
   saída mudou?".
5. Denning et al., *The Tracker* (TODS 1979), e Dinur & Nissim (PODS 2003): "só agregado" não protege.
6. Nissenbaum, *Privacy as Contextual Integrity* (2004), e Shao et al., *PrivacyLens* (NeurIPS 2024): o
   que é fluxo apropriado e quanto o LLM erra ao julgá-lo.
7. Gorla et al., *CHABADA* (ICSE 2014), e Bui et al., *PurPliance* (CCS 2021): conferir o comportamento
   contra a finalidade declarada.
8. Lawson et al. e Cabili et al., *DUO* e *DUOS* (Cell Genomics 2021): finalidade × permissões do dataset
   decididas automaticamente.
9. Du et al., *Reducing False Positives… in Industry* (ICSE-SEIP 2026): o LLM barato como árbitro da
   evidência mecânica.
10. Bernstein et al., *Trust Me, I Know This Function* (NDSS 2026), e ALIBI (2026, 01): como o atacante
    engana o juiz LLM.
11. Desai, Ritchie & Welpton, *Five Safes* (2016), e o *Handbook on SDC for Outputs* (2019/2024): a
    prática madura de checar a saída.
12. Fisk et al., *Active Wardens* (IH 2002), e Arp et al., *Dos and Don'ts of ML in Computer Security*
    (USENIX Sec 2022): desarmar em vez de detectar; avaliar com taxa base baixa.

---

## 1. Fundamentos: o que é "vazar"

**Fluxo de informação**
- [**A Note on the Confinement Problem**](https://doi.org/10.1145/362375.362389) (Lampson, CACM 1973) ✔: define confinar um programa e cataloga os canais (legítimos, de armazenamento, encobertos) → sem rede, só resta o legítimo.
- [**Certification of Programs for Secure Information Flow**](https://doi.org/10.1145/359636.359712) (Denning & Denning, CACM 1977) ✔: certificação estática sobre um reticulado de classes; nomeia os **fluxos implícitos** (via controle).
- [**Security Policies and Security Models**](https://doi.org/10.1109/SP.1982.10014) (Goguen & Meseguer, S&P 1982) ✔: introduz a **não interferência**, a definição-alvo de "não vazar".
- [**Language-based Information-Flow Security**](https://doi.org/10.1109/JSAC.2002.806121) (Sabelfeld & Myers, JSAC 2003) ✔: survey canônico de IFC (tipos, semântica, canais encobertos, desclassificação).
- [**Declassification: Dimensions and Principles**](https://doi.org/10.3233/JCS-2009-0352) (Sabelfeld & Sands, JCS 2009) ✔: organiza a desclassificação em "o quê, quem, onde, quando" → `agregado:k` e `transformacao` são desclassificação do tipo "o quê". [$]
- [**Secure Information Flow by Self-Composition**](https://doi.org/10.1109/CSFW.2004.1310735) (Barthe, D'Argenio & Rezk, CSFW 2004) ✔: compor o programa consigo mesmo reduz a não interferência a verificação comum; é a base formal do D/D′.
- [**Hyperproperties**](https://doi.org/10.3233/JCS-2009-0393) (Clarkson & Schneider, JCS 2010) ✔: a não interferência é propriedade de **pares** de execuções e não se verifica numa execução só.

**Fluxo quantitativo (QIF)**
- [**On the Foundations of QIF**](https://doi.org/10.1007/978-3-642-00596-1_21) (Smith, FoSSaCS 2009) ✔: mede o vazamento por min-entropia (a chance de acertar em uma tentativa), não por Shannon. [$]
- [**The Science of Quantitative Information Flow**](https://doi.org/10.1007/978-3-319-96131-6) (Alvim et al., Springer 2020, livro) ✔: teoria unificada (g-vulnerabilidade, refinamento, capacidade).
- [**Automatic Discovery and Quantification of Information Leaks**](https://doi.org/10.1109/SP.2009.18) (Backes, Köpf & Rybalchenko, S&P 2009) ✔: sintetiza a partição que a saída induz no segredo e conta as classes.
- [**QIF as Network Flow Capacity**](https://doi.org/10.1145/1375581.1375606) (McCamant & Ernst, PLDI 2008) ✔: limite superior de bits vazados por fluxo máximo sobre execuções observadas → bits por execução na L2 e na L4. [$]
- [**Leakage Bounds via Approximate Model Counting**](https://doi.org/10.1145/3591281) (Saha et al., PLDI 2023) ✔: limites sólidos com execução simbólica parcial, mas **só para C** (KLEE).

## 2. Análise estática

**Taint e IFC** (IRIS, LLMDFA, SemTaint, MoCQ e PyFlow estão em 01)
- [**FlowDroid**](https://doi.org/10.1145/2594291.2594299) (Arzt et al., PLDI 2014) ✔: taint estático sensível a contexto, campo e ciclo de vida; criou o DroidBench.
- [**SUSI**](https://doi.org/10.14722/ndss.2014.23039) (Rasthofer, Arzt & Bodden, NDSS 2014) ✔: classifica fontes e sumidouros por ML → catálogo de fontes (`pd.read_*`) e sumidouros (arquivo de saída).
- [**Seldon**](https://doi.org/10.1145/3314221.3314648) (Chibotaru et al., PLDI 2019) ✔: infere specs de taint para Python a partir de um corpus grande; é o precedente pré-LLM do IRIS.
- [**Code Property Graph**](https://doi.org/10.1109/SP.2014.44) (Yamaguchi et al., S&P 2014) ✔: AST, controle e dependência num grafo consultável; é a base do Joern.
- **JFlow/Jif** (Myers, POPL 1999) ✔ e **Merlin** (Livshits et al., PLDI 2009) ✔: IFC por tipos e inferência de specs de taint.

**Python e ciência de dados**
- [**PyCG**](https://doi.org/10.1109/ICSE43902.2021.00146) (Salis et al., ICSE 2021) ✔: grafo de chamadas prático para Python (repositório arquivado em 2023).
- [**Complex Python Features in the Wild**](https://doi.org/10.1145/3524842.3528467) (Yang, Milanova & Hirzel, MSR 2022) ✔: os recursos dinâmicos usados de fato e que quebram a estática → lista do que a L1 sinaliza. [$]
- [**Abstract Interpretation Framework for Input Data Usage**](https://doi.org/10.1007/978-3-319-89884-1_24) (Urban & Müller, ESOP 2018) ✔: semântica de "uso de dados de entrada" → provar que a saída depende só das colunas declaradas. [$]
- [**Quantitative Input Usage Static Analysis**](https://doi.org/10.1007/978-3-031-60698-4_5) (Mazzucato, Campion & Urban, NFM 2024) ✔: limita com solidez quanto cada entrada influencia a computação → ranquear colunas sensíveis. [$]
- [**Statically Detecting Data Leakages in Data Science Code**](https://doi.org/10.1145/3520313.3534657) (Subotić et al., SOAP 2022) ✔: estática leve sobre pandas e sklearn. **Homônimo:** aqui "data leakage" é vazamento entre treino e teste, como em Yang et al. (ASE 2022) e Kapoor & Narayanan (Patterns 2023). Vale reaproveitar a modelagem de pandas, não a política.

**LLM ajudando a estática**
- [**ZeroFalse**](https://arxiv.org/abs/2510.02534) (Iranmanesh et al., 2025) ✔: o LLM adjudica o alerta do SAST junto com o traço de fluxo e o contexto da CWE; F1 > 0,9. [$]
- [**LATTE**](https://doi.org/10.1145/3711816) (Liu et al., TOSEM 2025) ✔: a estática fatia o código e o LLM julga sumidouros e cadeias de chamadas.
- [**Soundness Checking of Taint Flow Models**](https://arxiv.org/abs/2609.28750) (Kishor, Nicolet & Dodds, 2026) ✔: um agente gera modelos de fluxo de bibliotecas e um verificador simbólico confere a solidez (93% de 97, em Go) → checar as specs de numpy e pandas geradas por LLM.

## 3. Análise dinâmica e relacional (caixa-preta)

**Taint dinâmico e seus limites**
- [**TaintDroid**](https://www.usenix.org/conference/osdi10/taintdroid-information-flow-tracking-system-realtime-privacy-monitoring) (Enck et al., OSDI 2010) ✔: taint dinâmico em todo o sistema; 20 de 30 apps populares usavam dados privados de forma suspeita.
- [**Panorama**](https://doi.org/10.1145/1315245.1315261) (Yin et al., CCS 2007) ✔: detecta malware pelo que ele faz com dado marcado, não por assinatura.
- [**All You Ever Wanted to Know About DTA**](https://cgi.di.uoa.gr/~thanassis/papers/symbolic.pdf) (Schwartz, Avgerinos & Brumley, S&P 2010) ✔: o taint dinâmico sub-marca o fluxo implícito e sobre-marca por política → serve de sinal, não de veredito.
- **DTA++** (Kang et al., NDSS 2011) ✔: propaga o taint por dependências de controle escolhidas.

**Teste relacional D/D′** (QFuzz, Hypertesting e SME estão em 01)
- [**Multiple Facets for Dynamic Information Flow**](https://doi.org/10.1145/2103656.2103677) (Austin & Flanagan, POPL 2012) ✔: simula a multi-execução num processo só. [$]
- [**Testing Noninterference, Quickly**](https://arxiv.org/abs/1409.0393) (Hriţcu et al., ICFP 2013) ✔: gera pares indistinguíveis e encolhe o contraexemplo até o mínimo. [$]
- [**DifFuzz**](https://2019.icse-conferences.org/details/icse-2019-Technical-Papers/86/DifFuzz-Differential-Fuzzing-for-Side-Channel-Analysis) (Nilizadeh, Noller & Păsăreanu, ICSE 2019) ✔: *fuzzing* que maximiza a diferença observável entre duas cópias com segredos distintos → buscar o pior D′. [$]
- [**Finding Information Leaks with Information Flow Fuzzing**](https://doi.org/10.1145/3711902) (Gruner, Brust & Zeller, TOSEM 2025) ✔: muta só o segredo e usa a mudança na saída como oráculo → é o oráculo central da L2. [$]

**A app como mecanismo: testar violação de DP** (Eureka e auditorias de DP estão em 01)
- [**StatDP**](https://arxiv.org/abs/1805.10277) (Ding et al., CCS 2018) ✔: testes estatísticos sobre entradas vizinhas produzem contraexemplos de ε-DP. [$]
- [**DP-Sniper**](https://github.com/eth-sri/dp-sniper) (Bichsel et al., S&P 2021) ✔: um classificador que distingue saídas de D e de D′ vira ataque quase ótimo → regressão logística em CPU como medidor da L2. [$]
- [**Delta-Siege**](https://github.com/eth-sri/Delta-Siege) (Lokna et al., CCS 2023) ✔: audita (ε,δ)-DP; achou falhas em bibliotecas e em geradores de dados sintéticos. [$]
- [**DP-Auditorium**](https://arxiv.org/abs/2307.05608) (Kong et al., 2023) ✔: biblioteca Python; mostra que **nenhum testador domina** os outros. [$]

**Canários e pior caso**
- [**The Secret Sharer**](https://www.usenix.org/conference/usenixsecurity19/presentation/carlini) (Carlini et al., USENIX Sec 2019) ✔: canários aleatórios e a métrica de exposição. [$]
- [**Privacy Auditing with One (1) Training Run**](https://proceedings.neurips.cc/paper_files/paper/2023/hash/9a6f6e0d6781d1cb8689192408946d73-Abstract.html) (Steinke, Nasr & Jagielski, NeurIPS 2023) ✔: muitos canários numa execução só dão um limite inferior de ε. [$]
- [**Evaluations of ML Privacy Defenses are Misleading**](https://arxiv.org/abs/2404.17399) (Aerni, Zhang & Tramèr, CCS 2024) ✔: médias subestimam o vazamento em cerca de 10× → medir o registro mais vulnerável.

**Por que "só agregado" não basta** (as reconstruções do Censo e do Diffix estão em 01)
- [**The Tracker**](https://faculty.nps.edu/dedennin/publications/TrackerThreat.pdf) (Denning, Denning & Schwartz, TODS 1979) ✔: o tamanho mínimo de consulta é quase sempre contornado.
- **Revealing Information while Preserving Privacy** (Dinur & Nissim, PODS 2003): somas com ruído o(√n) permitem reconstruir quase todo o banco.
- [**Knock Knock, Who's There?**](https://arxiv.org/abs/1708.06145) (Pyrgelis, Troncoso & De Cristofaro, NDSS 2018) ✔: inferência de pertencimento em séries agregadas de localização.
- [**QuerySnout**](https://arxiv.org/abs/2211.05249) (Cretu et al., CCS 2022) ✔: busca automática de consultas que inferem o atributo de um alvo → ataque de diferença contra a L4.
- [**DeSIA**](https://arxiv.org/abs/2504.18497) (Mao, Stevanoski & de Montjoye, 2025) ✔: com poucos agregados fixos, a inferência de atributo supera a reconstrução.
- [**Covariance Information Creates Vulnerability in FL Frameworks**](https://pmc.ncbi.nlm.nih.gov/articles/PMC10516515/) (Huth et al., Bioinformatics 2023) ✔: médias e covariâncias **permitidas** reconstroem os dados no DataSHIELD, e repetir a consulta remove o ruído → o portão olha a sessão, não a função.

**Dados sintéticos para testar**
- [**Synthetic Data – Anonymisation Groundhog Day**](https://www.usenix.org/conference/usenixsecurity22/presentation/stadler) (Stadler, Oprisanu & Troncoso, USENIX Sec 2022) ✔: dado sintético não anonimiza → serve de insumo de teste, não de saída.
- [**Linear Reconstruction Attribute Inference against Synthetic Data**](https://usenix.org/conference/usenixsecurity24/presentation/annamalai) (Annamalai, Gadotti & Rocher, USENIX Sec 2024) ✔: infere o atributo de qualquer registro, com até 94,8% de acerto → app que gera sintético é saída de alto risco.

## 4. Análise agêntica e com LLM

**Agentes de auditoria**
- [**CyberGym**](https://arxiv.org/abs/2506.02548) (Wang et al., ICLR 2026) ✔: 1.507 vulnerabilidades reais; os melhores agentes reproduzem ~20%.
- [**SEC-bench**](https://arxiv.org/abs/2506.11791) (Lee et al., NeurIPS 2025) ✔: monta ambientes reproduzíveis a US$ 0,87 por caso; os agentes chegam a 18% de PoC. [$]
- [**SoK: DARPA AIxCC**](https://arxiv.org/abs/2602.07666) (Zhang et al., USENIX Sec 2026) ✔: os finalistas usam o LLM para orquestrar *fuzzing*, execução simbólica e estática.

**LLM como árbitro da evidência mecânica**
- [**Reducing False Positives… An Empirical Study in Industry**](https://arxiv.org/abs/2601.18844) (Du et al., ICSE-SEIP 2026) ✔: na Tencent, LLM + análise estática elimina 94–98% dos falsos positivos a US$ 0,001–0,12 por alerta. [$]
- [**Memoir**](https://arxiv.org/abs/2608.09181) (Guan et al., 2026) ✔: falsos positivos antigos viram memórias verificadas; a memória pode ser envenenada.
- [**LLMs for Code Analysis: Do LLMs Really Do Their Job?**](https://arxiv.org/abs/2310.12357) (Fang et al., USENIX Sec 2024) ✔: LLMs diante de código ofuscado; modelos pequenos sofrem mais (números a conferir no PDF) → desofuscar antes da L3.
- [**JsDeObsBench**](https://arxiv.org/abs/2506.20170) (Chen, Jin & Lin, CCS 2025) ✔: o LLM desofusca melhor que as ferramentas, mas quebra a sintaxe → revalidar mecanicamente.
- **LLM4SA** (Wen et al., TKDD 2024): relata P = 81% e R = 95% na triagem de alertas, mas uma reavaliação mediu F1 de 13% (a verificar) → exemplo de número que não se replica.

**Código malicioso e intenção declarada × implementada** (SocketAI e MalGuard estão em 01)
- [**Evaluation of LLMs for Malicious Python Packages**](https://arxiv.org/abs/2602.16304) (Ryan et al., 2026) ✔: em 4.070 pacotes, detectar vai bem (F1 até 0,99), mas localizar a linha cai a F1 0,48 → o LLM tria, não aponta o mecanismo. [$]
- [**CHASE**](https://arxiv.org/abs/2601.06838) (Toda & Mori, AIware 2025) ✔: agentes com ferramentas determinísticas nas etapas críticas; recall 98,4% e FPR 0,08% no PyPI.
- [**SkillSieve**](https://arxiv.org/abs/2604.06550) (Hou & Yang, 2026) ✔: regex/AST, depois subtarefas de LLM, depois júri de 3 modelos; F1 0,929 a US$ 0,006 por item → espelha a sequência L1 → L3. [$]
- [**Behavioral Integrity Verification for Agent Skills**](https://neurips.cc/virtual/2026/172975) (Wu, Li & Liu, NeurIPS 2026 WS) ✔: compara a capacidade declarada com a implementada; 80% de 49.943 skills divergem → **é a L0 aplicada a skills**.
- [**DCIChecker**](https://arxiv.org/abs/2606.04769) (Shi et al., 2026) ✔ e [**MCPDiFF**](https://arxiv.org/abs/2602.03580) (Li et al., 2026) ✔: inconsistência entre descrição e código em servidores MCP (10–13%), por estática e LLM com arbitragem.

**Monitores**
- [**AgentAuditor**](https://arxiv.org/abs/2506.00641) (Luo et al., NeurIPS 2025) ✔: juiz sem treino, com memória de casos, que chega à acurácia humana. [$]
- **Reliable Weak-to-Strong Monitoring** (Kale et al., ICLR 2026, 01): escalar só os casos sinalizados dá +15% de TPR a 1% de FPR.
- **How Does Information Access Affect LLM Monitors** (Arike et al., 2026, 01): menos contexto é melhor; extrair e depois avaliar ganha 16,8 p.p. → a L3 recebe só o trecho que a L1 apontou. [$]

**O juiz LLM sob ataque** (ALIBI, Thornton e Flashboom estão em 01)
- [**Trust Me, I Know This Function**](https://arxiv.org/abs/2508.17361) (Bernstein et al., NDSS 2026) ✔: o LLM lê padrões familiares como benignos; o ataque transfere entre fornecedores e funciona em Python → exfiltração disfarçada de pandas idiomático.
- [**Syntax-Preserving Evasion of LLM Vuln Detectors**](https://arxiv.org/abs/2602.00305) (Sun, Oprea & Wong, 2026) ✔: edições que preservam a semântica evadem 87% das detecções, e strings universais transferem com até 92,5% de sucesso.

**LLM julgando a saída (PII e dado sensível)** (REDACT está em 01: Presidio tem recall 0,07 nas categorias mais sensíveis)
- [**OpenAI Privacy Filter: 32 Benchmarks**](https://arxiv.org/abs/2608.02616) (Uppala, 2026) ✔: o OPF (1,5B, aberto) supera o Presidio com precisão baixa; um XLM-R ajustado com 100–1.000 exemplos supera o OPF. [$]
- [**Towards Contextual Sensitive Data Detection**](https://arxiv.org/abs/2512.04120) (Telkamp & Hulsebos, 2025) ✔: o contexto do dataset eleva o recall de 63% para 94% → a L4 guiada pelas tags.
- [**Detection of Personal Data in Structured Datasets**](https://arxiv.org/abs/2506.22305) (Ntwali et al., LLM-DPM 2025) ✔: o LLM com nomes de colunas e descrição supera o Presidio em tabelas.

## 5. Finalidade e contexto: a saída combina com o dataset?

**Integridade contextual (CI)**
- [**Privacy as Contextual Integrity**](https://digitalcommons.law.uw.edu/wlr/vol79/iss1/10) (Nissenbaum, Washington Law Review 2004) ✔: privacidade é fluxo apropriado às normas do contexto (atores, tipo de informação, princípio de transmissão).
- [**Privacy and Contextual Integrity: Framework and Applications**](https://doi.org/10.1109/SP.2006.32) (Barth et al., S&P 2006) ✔: normas de CI em lógica temporal, aplicadas a HIPAA, COPPA e GLBA → tags como normas checáveis.
- [**VACCINE**](https://par.nsf.gov/biblio/10095711) (Shvartzshnaider et al., WWW 2019) ✔: DLP por CI; uma política declarativa compilada em regras supera o DLP sintático. [$]
- [**Contextual Integrity through the Lens of CS**](https://doi.org/10.1561/3300000016) (Benthall, Gürses & Nissenbaum, FnT 2017) ✔: a computação operacionaliza "contexto" de formas divergentes.
- [**The Five Safes as a Privacy Context**](https://arxiv.org/abs/2510.05803) (Bailie & Gong, 2025) ✔: mapeia os parâmetros da CI nas cinco dimensões do Five Safes.

**LLM como juiz de contexto**
- [**ConfAIde: Can LLMs Keep a Secret?**](https://proceedings.iclr.cc/paper_files/paper/2024/hash/08305d8b2ddab98932c163ea73df065f-Abstract-Conference.html) (Mireshghallah et al., ICLR 2024) ✔: o GPT-4 revela informação em contexto impróprio em 39% dos casos, e o ChatGPT em 57%.
- [**PrivacyLens**](https://arxiv.org/abs/2409.00138) (Shao et al., NeurIPS 2024 D&B) ✔: como agente, o GPT-4 vaza em 25,7% dos casos mesmo instruído; responder bem não é agir bem.
- [**CI-Bench**](https://arxiv.org/abs/2409.13903) (Cheng et al., Google, 2024) ✔: 44 mil casos sintéticos de CI em 8 domínios. [$]
- [**Operationalizing CI in Privacy-Conscious Assistants**](https://arxiv.org/abs/2408.02373) (Ghalebikesabi et al., 2024) ✔: pedir raciocínio explícito em termos de CI melhora o assistente. [$]
- [**PrivaCI-Bench**](https://arxiv.org/abs/2502.17041) (Li et al., ACL 2025) ✔: LLMs extraem bem os parâmetros de CI, mas erram o veredito → **o LLM extrai, a regra decide**. [$]
- [**Privacy Checklist**](https://arxiv.org/abs/2408.10053) (Li et al., NAACL 2025) ✔: um *checklist* hierárquico via RAG serve de contexto ao juiz. [$]
- [**GoldCoin**](https://aclanthology.org/2024.emnlp-main.195/) (Fan et al., EMNLP 2024) ✔ e [**CI via Reasoning and RL**](https://arxiv.org/abs/2506.04245) (Lan et al., NeurIPS 2025) ✔: ancoram a CI em lei e ajustam o LLM; exigem treino, então ficam para o futuro.
- [**Position: CI is Inadequately Applied to LMs**](https://proceedings.mlr.press/v267/shvartzshnaider25a.html) (Shvartzshnaider & Duddu, ICML 2025) ✔: denuncia o "CI-washing"; vale como *checklist* metodológico.
- [**User Perceptions vs. Proxy LLM Judges**](https://aclanthology.org/2026.acl-long.1645/) (Wu et al., ACL 2026) ✔: os juízes LLM concordam entre si, mas não com humanos.
- [**CI-Work**](https://arxiv.org/abs/2604.21308) (Fu et al., ACL 2026 Industry) ✔: 16–51% de violações; nem escala nem raciocínio resolvem.
- [**Mao et al.**](https://arxiv.org/abs/2505.11502) (2025) ✔: grafo de conhecimento + LLM ganha 37,6% de precisão com 93,5% menos tokens. [$]

**Finalidade e controle de uso**
- [**Hippocratic Databases**](https://doi.org/10.1016/B978-155860869-6/50021-4) (Agrawal et al., VLDB 2002) ✔: a finalidade vira metadado de primeira classe, e uso e retenção ficam limitados a ela.
- [**Purpose-Based Access Control**](https://www.cs.purdue.edu/homes/ninghui/papers/pbac_vldbj.pdf) (Byun & Li, VLDB J 2008) ✔: hierarquia de finalidades com proibições explícitas → forma das tags.
- [**Purpose Control**](https://doi.org/10.1007/978-3-642-23556-6_10) (Petković, Prandi & Zannone, SDM 2011) ✔: a permissão não garante a finalidade; é preciso auditar o comportamento.
- [**UCON_ABC**](https://www.profsandhu.com/journals/tissec/ucon-abc.pdf) (Park & Sandhu, TISSEC 2004) ✔ e [**Distributed Usage Control**](https://doi.org/10.1145/1151030.1151053) (Pretschner, Hilty & Basin, CACM 2006) ✔: obrigações e condições sobre o uso, inclusive depois do acesso.

**Declarado × comportamento**
- [**WHYPER**](https://www.usenix.org/conference/usenixsecurity13/technical-sessions/presentation/pandita) (Pandita et al., USENIX Sec 2013) ✔ e [**AutoCog**](https://doi.org/10.1145/2660267.2660287) (Qu et al., CCS 2014) ✔: acham as frases da descrição que justificam cada permissão (P e R ~92%).
- [**CHABADA**](https://doi.org/10.1145/2568225.2568276) (Gorla et al., ICSE 2014) ✔: agrupa apps pelo assunto da descrição e marca o uso de API destoante; pegou 56% do malware novo → **achar a app destoante entre as do mesmo assunto**.
- [**FlowCog**](https://www.usenix.org/conference/usenixsecurity18/presentation/pan) (Pan et al., USENIX Sec 2018) ✔: justifica cada fluxo, não o app inteiro (P 90%, R 93%) → justificar cada campo da saída.
- [**PolicyLint**](https://usenix.org/conference/usenixsecurity19/presentation/andow) (USENIX Sec 2019) ✔ e [**PoliCheck**](https://usenix.org/conference/usenixsecurity20/presentation/andow) (Andow et al., USENIX Sec 2020) ✔: confrontam fluxo e política por destinatário; até 42% dos apps divulgam errado → declarar como tuplas (dado, destinatário, finalidade).
- [**PurPliance**](https://rtcl.eecs.umich.edu/rtclweb/assets/publications/2021/ccs21-duc.pdf) (Bui et al., CCS 2021) ✔: taxonomia de finalidades e modelo formal de contradição; 70% de 23 mil apps são inconsistentes.
- [**PoliGraph**](https://www.usenix.org/conference/usenixsecurity23/presentation/cui) (Cui et al., USENIX Sec 2023) ✔: a política vira um grafo com subsunção → subsunção entre tags.
- [**Lalaine**](https://www.usenix.org/conference/usenixsecurity23/presentation/xiaoyue) (Xiao et al., USENIX Sec 2023) ✔ e [**Data Safety**](https://www.usenix.org/conference/usenixsecurity24/presentation/khandelwal) (Khandelwal et al., USENIX Sec 2024) ✔: os rótulos de privacidade não batem com o comportamento real → a autodeclaração é hipótese.

## 6. Controle de saída

**Checagem de saída em TREs (ambientes de pesquisa confiáveis)** (ACRO, SACRO e OpenSAFELY estão em 01)
- [**Five Safes**](https://ideas.repec.org/p/uwe/wpaper/20161601.html) (Desai, Ritchie & Welpton, 2016) ✔: projetos, pessoas, dados, ambientes e saídas seguros → o Juiz é o projeto seguro e a L4 é a saída segura. [$]
- [**Principles- versus Rules-Based Output SDC**](https://doi.org/10.29173/iq778) (Ritchie & Elliot, IASSIST Q 2015) ✔: regra padrão + exceção justificada é mais segura e barata que regra fixa. [$]
- [**Not Fit for Purpose: Five Safes**](https://arxiv.org/abs/2011.02142) (Culnane, Rubinstein & Watts, 2020) ✔: não há padrão objetivo de "seguro" → orçamento formal além do *checklist*.
- [**GRAIMATTER**](https://arxiv.org/abs/2211.01656) (Jefferson et al., 2022) ✔ e [**ML Models in TREs**](https://doi.org/10.23889/ijpds.v8i1.2165) (Ritchie et al., IJPDS 2023) ✔: um modelo de ML que sai do TRE é risco novo; esconder dado em modelo é real e não tem checagem clara.
- [**SACRO-ML**](https://arxiv.org/abs/2212.01233) (Smith et al., 2022–25) ✔: checagem ante-hoc do treino e ataques post-hoc (MIA, LiRA) em CPU. [$]
- [**RELEASE-AI**](https://doi.org/10.23889/ijpds.v11i5.3646) (Crespi-Boixader et al., IJPDS 2026) ✔: níveis de controle por probabilidade de ataque × severidade.
- [**Output Checking (CBS)**](https://doi.org/10.23889/ijpds.v11i5.3500) (Bär, Kuin & Verkooijen, IJPDS 2026) ✔: automatiza a checagem de células pequenas e valores cifrados; sem avaliação de eficácia publicada.

**Privacidade diferencial e anonimização**
- [**Calibrating Noise to Sensitivity**](https://doi.org/10.1007/11681878_14) (Dwork et al., TCC 2006) ✔ e [**Algorithmic Foundations of DP**](https://doi.org/10.1561/0400000042) (Dwork & Roth, 2014) ✔: DP, mecanismo de Laplace e composição → orçamento entre execuções.
- [**Towards Practical DP for SQL**](https://arxiv.org/abs/1706.09479) (Johnson, Near & Song, PVLDB 2018) ✔: sensibilidade elástica para SQL, usada na Uber. [$]
- [**PrivateSQL**](https://doi.org/10.14778/3342263.3342274) (Kotsogiannis et al., PVLDB 2019) ✔: responde a partir de sinopses privadas, com orçamento fixo.
- [**DP SQL with Bounded User Contribution**](https://petsymposium.org/popets/2020/popets-2020-0025.php) (Wilson et al., PoPETs 2020) ✔: limita a contribuição por pessoa, não por linha. [$]
- **k-anonimato** (Sweeney, 2002) ✔, **ℓ-diversidade** (Machanavajjhala et al., TKDD 2007) ✔ e **t-closeness** (Li et al., ICDE 2007) ✔: cada um mostra a falha do anterior → o k mínimo é piso, não garantia.

**Desarmar em vez de detectar**
- [**Traffic Normalization**](https://www.usenix.org/conference/10th-usenix-security-symposium/network-intrusion-detection-evasion-traffic-normalization) (Handley, Paxson & Kreibich, USENIX Sec 2001) ✔: o normalizador reescreve o tráfego para tirar a ambiguidade.
- [**Active Wardens**](https://doi.org/10.1007/3-540-36415-3_2) (Fisk et al., Information Hiding 2002) ✔: o *warden* reescreve campos sem semântica sob uma **"fidelidade mínima requerida"** → fixar casas decimais e ordem por coluna. [$]
- [**CDR of RTF Files**](https://doi.org/10.1109/TIFS.2023.3241480) (Dubin, TIFS 2023) ✔: *Content Disarm and Reconstruction* reconstrói o arquivo formato a formato → reconstruir CSV e JSON a partir do schema. [$]

**Detecção e marcação**
- [**Data Leakage Detection**](https://doi.org/10.1109/TKDE.2010.100) (Papadimitriou & Garcia-Molina, TKDE 2011) ✔: objetos falsos distintos por destinatário identificam o vazador → canário diferente por execução. [$]
- [**Detection of Sensitive Data Exposure**](https://doi.org/10.1109/TIFS.2015.2398363) (Shu, Yao & Bertino, TIFS 2015) ✔ e [**Transformed Data Leaks**](https://hdl.handle.net/10919/76658) (Shu et al., TIFS 2016) ✔: *fingerprints* e alinhamento de sequências → achar linhas de entrada reembaralhadas na saída. [$]
- [**A Survey on Data Leakage Prevention Systems**](https://doi.org/10.1016/j.jnca.2016.01.008) (Alneyadi et al., JNCA 2016) ✔: o DLP convencional depende de regras fixas e é pouco proativo.

## 7. Vizinhos: plataformas code-to-data e mercados de dados

- **DataSHIELD** (Gaye et al., IJE 2014): só estatísticas "não divulgadoras" saem de cada centro → lista branca de funções; Huth et al. (§3) mostra o limite.
- **Personal Health Train** (Beyan et al., 2020) e **vantage6** (Moncada-Torres et al., AMIA 2020): o algoritmo em Docker vai até o dado, e o dono aprova por imagem, sem analisar o conteúdo.
- **PySyft** (Ziller et al., 2021) e [**External Scrutiny with PETs**](https://arxiv.org/abs/2502.05219) (Beers & Toner, 2025) ✔: ciência de dados remota com *code request* aprovado pelo dono; já foi usado em auditoria externa de IA (UK AISI + Anthropic).
- [**Data Station**](https://arxiv.org/abs/2305.03842) (Xia et al., PVLDB 2022) ✔: *escrow* com enclaves em que nada sai sem consentimento; **não descreve como o código é revisado**.
- **Data-Sharing Markets** (Castro Fernandez, SIGMOD 2023): incentivos para formar consórcios de dados.
- **Ryoan** (OSDI 2016, 01) e **Chancel** (Ahmad et al., NDSS 2021): confinam código não confiável sobre dado secreto em SGX, mediando todo o I/O.
- [**Citadel++**](https://arxiv.org/abs/2412.08534) (Chen et al., 2024) ✔: TEE de VM, sandbox de SO e DP imposta mesmo com código malicioso → arquitetura quase idêntica à nossa.
- [**SNPeek**](https://www.ndss-symposium.org/ndss-paper/snpeek-side-channel-analysis-for-privacy-applications-on-confidential-vms) (Zhang et al., NDSS 2026) ✔: canais laterais em SEV-SNP (um canal encoberto de 497 kbit/s) → "sem rede" não cobre o hipervisor.
- [**Data Market Design: SLR**](https://research.tilburguniversity.edu/en/publications/data-market-design-a-systematic-literature-review/) (Driessen et al., IEEE Access 2022) ✔, **A Marketplace for Data** (Agarwal, Dahleh & Sarkar, EC 2019) e Arrow (1962): taxonomia de mercados de dados, precificar o resultado em vez da cópia e o paradoxo da informação.

## 8. Benchmarks e como avaliar o avaliador

- [**ReproDroid**](https://doi.org/10.1145/3236024.3236029) (Pauck, Bodden & Wehrheim, FSE 2018) ✔: 4 de 6 ferramentas de taint descumprem as próprias promessas → verdade-base reproduzível. [$]
- **Analyzing the Analyzers** (Qiu, Wang & Rubin, ISSTA 2018) ✔ e [**TaintBench**](https://doi.org/10.1007/s10664-021-10013-5) (Luo et al., EMSE 2021) ✔: as ferramentas vão pior em malware real do que no sintético.
- [**An Empirical Study on SAST Tools for Python**](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/30/An-Empirical-Study-on-Static-Application-Security-Testing-SAST-Tools-for-Python) (Liu et al., ICSE 2026, Distinguished Paper) ✔: uma ferramenta acha no máximo 40%, e todas juntas 66,7%.
- **SAST Tools for Java** (Li et al., FSE 2023): as ferramentas acham só 12,7% das vulnerabilidades reais.
- [**CASTLE**](https://arxiv.org/abs/2503.09433) (Dubniczky et al., 2025) ✔ e **SecVulEval** (Ahmed et al., 2025): os LLMs pioram com o tamanho do código; o melhor F1 no nível de instrução foi 23,8%.
- [**RealVuln**](https://arxiv.org/abs/2604.13764) (Pellew & Raza, 2026) ✔: 26 repositórios Python com armadilhas de falso positivo; Semgrep 17,7 contra LLM 51,7 (F3). [$]
- **Backstabber's Knife Collection** (Ohm et al., DIMVA 2020) e [**MalOSS**](https://www.ndss-symposium.org/ndss-paper/towards-measuring-supply-chain-attacks-on-package-managers-for-interpreted-languages) (Duan et al., NDSS 2021) ✔: taxonomia de gatilhos e pipeline metadados + estática + dinâmica.
- [**Bad Snakes**](https://conf.researchr.org/details/icse-2023/icse-2023-technical-track/120/Bad-Snakes-Understanding-and-Improving-Python-Package-Index-Malware-Scanning) (Vu et al., ICSE 2023) ✔: os scanners do PyPI têm 15–97% de falso positivo, e os administradores toleram 0,01%.
- **The Base-Rate Fallacy** (Axelsson, CCS 1999) e **Dos and Don'ts of ML in Computer Security** (Arp et al., USENIX Sec 2022): com prevalência baixa, quem manda é o FPR → reportar precisão e TPR a FPR baixo.
- **Why Don't Developers Use Static Analysis Tools** (Johnson et al., ICSE 2013): falso positivo e má apresentação matam a adoção → o laudo precisa ser acionável.

## 9. Práticas, normas e ferramentas (não são papers)

**Vocabulários de finalidade (forma das tags)**
- **GA4GH DUO + DUOS** (Lawson et al. e Cabili et al., Cell Genomics 2021) ✔: ontologia de permissões de uso com mais de 200 mil datasets anotados. O DUOS casa a finalidade da pesquisa com as limitações do dataset e coincidiu com o comitê em todos os casos medidos. [grátis]
- **W3C ODRL 2.2** ✔: Permission, Prohibition, Duty e Constraint, com o operando `odrl:purpose`. [grátis]
- **W3C DPV, Purposes** ✔: ~95 finalidades em SKOS; é relatório de grupo comunitário, não padrão W3C. [grátis]
- **IDS Usage Control (IDS-G)** ✔: 25 classes de política (restringir finalidade, exigir agregado, limitar contagem, apagar após uso, registrar), na arquitetura PAP/PDP/PEP → o Juiz faz o papel de PDP. [grátis]

**Checagem de saída e *clean rooms***
- **Handbook on SDC for Outputs v2.0** (2024) ✔, **guia SACRO** (2023) ✔ e Hundepool et al., **Statistical Disclosure Control** (Wiley 2012) ✔: N = 10, regras de dominância, risco de diferenciação entre tabelas e critérios de exceção por tipo de saída. [grátis]
- **SATRE** (DARE UK, 2023) ✔: arquitetura padrão de TRE com 29 capacidades e 160 declarações. [grátis]
- **AWS Clean Rooms** ✔: a própria AWS admite que o limiar por consulta não cobre ataques de diferença. **Google Ads Data Hub** ✔: ~50 usuários por linha com *difference checks*, e a checagem estática proíbe exportar IDs.
- **Azure Confidential Clean Rooms** ✔: containers atestados, `allowedFields`, pré-condições e pós-filtros, aprovação de todos os donos → a arquitetura comercial mais próxima.
- **NCSC, Cross Domain Solutions** ✔: transformar tipos complexos em simples e verificáveis antes de cruzar a fronteira. [grátis]
- **PySyft *code request*** ✔, **Ocean Compute-to-Data** ✔ e **declaração de controles do DataSHIELD**: a aprovação é manual ou nominal, sem análise automática do código.

**Detecção na saída**
- **Microsoft Presidio** ✔ e **OpenAI Privacy Filter** ✔ (1,5B, Apache-2.0, roda em laptop): PII por regra e por modelo. [grátis]
- **Google Sensitive Data Protection** ✔ e **Amazon Macie** ✔: catálogo de detectores e de transformações (mascaramento, *bucketing*, tokenização) a imitar.
- **Canarytokens** (Thinkst) ✔: *tripwires* gratuitos; os honeytokens remontam a Spitzner (2003). [grátis]

**Análise estática**
- **Pysa** ✔, **CodeQL** (Python e *threat model* `local`) ✔, **Semgrep** (modo taint) ✔, **Joern** ✔, **Bandit** ✔, **Scalpel** ✔ e **Lyra** (análise de uso de dados de Urban) ✔: do filtro barato ao taint interprocedural. A licença comercial do CodeQL está a verificar. [grátis]
- **GuardDog** e **DataDog malicious-software-packages-dataset**: mais de 2,8 mil pacotes PyPI e npm maliciosos, com viés de seleção. [grátis]

**Análise dinâmica e testes**
- **OSSF package-analysis** ✔, **gVisor** ✔, **Falco** ✔ e **Tetragon** ✔: rastreiam e barram syscalls, rede e arquivos; pegam a **tentativa** de exfiltração, não o vazamento pela saída legítima. [grátis]
- **Hypothesis** ✔, **Pandera** ✔ e **SDV** ✔: geram pares D/D′ e DataFrames a partir do schema e encolhem os contraexemplos. [grátis]
- **Tumult Analytics**, **OpenDP** e **Google DP** ✔: ruído e orçamento sem implementar o mecanismo. [grátis]

**Agentes e LLM em produção**
- **Big Sleep** (Google) ✔, **Buttercup** (Trail of Bits, aberto, roda em laptop) ✔ e **ATLANTIS** ✔: o LLM orquestra a evidência mecânica e reproduz antes de reportar.
- **Codex Security** (ex-Aardvark, OpenAI) e **Claude Code `/security-review`** (Anthropic): linhas de base de prateleira (a verificar).
- **LlamaFirewall** (Meta) ✔: o AlignmentCheck confere ações contra o objetivo declarado → padrão "saída × finalidade do contrato".
- **Datadog BewAIre** ✔: juiz de intenção maliciosa em ~10 mil PRs por semana, com FPR de 0,03%. **Semgrep Assistant** ✔: tria ~60% dos achados, sem medir falso negativo.

**Normas e lei**
- **LGPD art. 6º, I–III** (finalidade, adequação, necessidade) e **GDPR art. 5(1)(b)–(c)** ✔ (limitação da finalidade, minimização): base legal para barrar saída fora da finalidade.
- **ISO/IEC 27002:2022, controle 8.12** (prevenção de vazamento de dados), **NIST SP 800-53 r5 AC-4** (*information flow enforcement*), **MITRE ATT&CK TA0010** (*exfiltration*) e **CWE-200**: vocabulário de conformidade para o artigo (não conferidos nesta rodada).

## 10. Consensos, controvérsias e lacunas

**Consensos**
- **Não interferência estrita é incompatível com saída útil.** O caminho aceito é declarar o que pode sair (as tags) e medir o vazamento residual (Sabelfeld & Sands; Smith).
- **Vazamento é propriedade de pares de execuções.** O taint de uma execução só não decide; o teste relacional D/D′ decide (Clarkson & Schneider; Schwartz; FlowFuzz).
- **Teste caixa-preta só dá limite inferior**, e nenhum testador domina os outros (StatDP, DP-Sniper, DP-Auditorium). O veredito honesto é "não achamos", não "é seguro".
- **"Só agregado" e limiar por consulta não protegem** contra diferença e reconstrução (Tracker, Dinur–Nissim, Huth, DeSIA, AWS). É preciso orçamento entre execuções.
- **O LLM rende como árbitro de evidência, não como detector isolado** (Du, ZeroFalse, CHASE, Buttercup), e rende mais com menos contexto (Arike).
- **O LLM extrai bem o contexto, mas erra o veredito** (PrivaCI-Bench, ConfAIde, PrivacyLens, CI-Work). Regra determinística decide; o LLM entra só na etapa semântica (DUOS, PoliGraph, Mao).
- **Declarado ≠ real é a regra** (PoliCheck 42%, PurPliance 70%, BIV 80%, MCP 10–13%). A finalidade declarada pela app é hipótese a verificar, nunca evidência.
- **Desarmar vence detectar:** normalização de tráfego, *active wardens*, CDR e soluções *cross domain* convergem nisso.
- **Benchmark sintético superestima** o detector (Li 12,7%; TaintBench; SAST para Python ≤ 40%). Com taxa base baixa, o que conta é o FPR (Axelsson, Arp, Bad Snakes).

**Controvérsias**
- **Comentários e strings.** ALIBI e Sun et al. mandam sanitizar antes do juiz; Thornton e a decisão atual do Juiz dizem para não remover. O 01 já propõe rodar a L3 com e sem o texto do atacante.
- **Validade do juiz LLM de privacidade.** O juiz do CI-Work concorda 88% com humanos; Wu et al. (ACL 2026) mostram juízes que concordam entre si e não com humanos.
- **Números que não se replicam** na triagem por LLM (LLM4SA: de 81/95 relatados para F1 13% numa reavaliação).

**Lacunas (oportunidades do DNAT)**
- **Não existe benchmark de exfiltração pela saída legítima** de apps Python e pandas. Três levantamentos chegaram a isso, o que reforça a lacuna C3 do 01.
- **Não há ferramenta relacional nem QIF madura para Python e pandas.** DifFuzz, FlowFuzz e Saha et al. miram C, Java ou binários.
- **Ninguém une a análise de uso de dados** (Urban) a políticas de desclassificação como `agregado:k` sobre um sumidouro de arquivo.
- **A comparação declarado × implementado** existe para apps móveis, skills e MCP, mas não para jobs de dados com saída agregada.
- **As plataformas code-to-data revisam o código à mão** (PySyft, Ocean, vantage6), e nenhuma publica TPR/FPR dessa revisão.
- **Não há "fidelidade mínima requerida" formal** para saídas tabulares e estatísticas.
- **A checagem automatizada de saída** (SACRO, CBS) não tem avaliação de eficácia publicada.

## 11. O que isso dá ao DNAT (insumo, não decisão)

| Camada | O que a literatura sugere | Base |
|---|---|---|
| **L0 finalidade** | Tags num vocabulário fechado inspirado em DUO, ODRL e DPV. A app declara tuplas (dado, destinatário, finalidade) e cada campo da saída precisa de justificativa. O casamento finalidade × tag é **regra determinística**; o LLM só extrai os parâmetros. No futuro, com corpus, achar a app destoante entre as do mesmo assunto. | DUOS, PoliCheck, FlowCog, PrivaCI-Bench, CHABADA |
| **L1 estática** | Bandit/Semgrep, depois Pysa/CodeQL com fonte `pd.read_*` e sumidouro no arquivo de saída. Somar a análise de **uso de colunas** (Lyra/Urban) e sinalizar recursos dinâmicos de Python. Esperar recall baixo. | Urban, Yang (MSR 2022), SAST para Python (ICSE 2026) |
| **L2 dinâmica** | Oráculo "mudou só o segredo" com pares D/D′ gerados por Hypothesis e Pandera. Um classificador logístico mede a distinguibilidade. Canários em uma execução, medindo o pior registro. gVisor/Falco pegam a tentativa de rede. | FlowFuzz, DP-Sniper, Steinke, Aerni, OSSF |
| **L3 agêntica** | O LLM arbitra a evidência da L1 e da L2 recebendo só o trecho apontado. Reportar TPR a 1% de FPR **sob ataque adaptativo**. Incluir o ataque "pandas idiomático" (FPA) no repertório da batalha. | Du, Arike, Kale, Bernstein, SkillSieve |
| **L4 saída** | Regras SDC padrão (N = 10, dominância, diferenciação) e exceção decidida pelo dono. Canonicalizar com fidelidade mínima por coluna e reconstruir a saída a partir do schema. PII com Presidio + OPF (nunca só o Presidio). Canário distinto por execução. Orçamento entre execuções. | Ritchie & Elliot, Fisk, Dubin, REDACT, Papadimitriou, Dwork & Roth |
| **Avaliação** | Precisão e TPR com FPR baixo, ou curvas PR. Conjunto real além do sintético. Pior caso, não média. | Arp, Axelsson, TaintBench, Aerni |

**Contribuições possíveis e baratas, todas em CPU:**
1. **Benchmark de exfiltração pela saída legítima** em Python e pandas, com verdade CTF (app + decodificador). É lacuna em três levantamentos.
2. **"Fidelidade mínima requerida" para saídas tabulares**: canonicalização por tipo de coluna, com o vazamento residual medido em bits.
3. **Primeira avaliação com TPR/FPR da revisão automática de código** em plataforma code-to-data. Hoje essa revisão é manual em PySyft, Ocean e vantage6.
