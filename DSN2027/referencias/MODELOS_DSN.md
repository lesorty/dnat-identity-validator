# Modelos de ML/LLM no DSN 2021–2026: que problemas o DSN já aceitou

**Data:** 2026-10-27 · **Para:** definir com precisão o problema do rumo B (custódia de modelos
abertos + portão de liberação de derivados; "proteção de cadeia de suprimentos de modelos").
**Base:** [TEMAS_DSN.md](TEMAS_DSN.md), [temas_dsn_2021_2026.csv](temas_dsn_2021_2026.csv),
[GUIA_DSN.md](GUIA_DSN.md) (fichas [44]–[58]), [E6](../etapas/E6_alt_modelos_abertos.md),
[E8 §9](../etapas/E8_alinhamento_dsn.md), [E9](../etapas/E9_testes_validos.md).
**Convenções:** ✔ = conferido no PDF nesta rodada; **(a verificar)** = não conferido (em geral,
classificado só pelo título ou pelo resumo). Nada aqui afirma novidade: "não encontramos" vale só
para as listas abaixo.

---

## Resumo

- **96 trabalhos selecionados**: 58 nos anais principais (Research Track 43, Industry/DSN-S 15) e
  38 no workshop **DSML** (2021–2026).
- **Relevância:** 8 alta, 17 média, 71 baixa.
- **PDFs:** dos 25 de relevância alta ou média, **18 estão em `dsn/`** (5 baixados nesta rodada);
  7 não têm versão aberta encontrada (ficam para a instituição).
- **Lidos nesta rodada (✔):** Prefill, LymphNode, BProm, AnBridge, MCP, Plinius, variância de
  robustez certificada (DSML'26) e sondagem de espaço latente (DSML'26). Multi-version ML, ReMlX e
  TPU-FI já tinham ficha de leitura no GUIA §4.9.
- **Achado central:** o DSN já aceitou (i) proteger o modelo **contra o host** (Plinius, AnBridge),
  (ii) proteger o modelo **contra quem consulta** (LymphNode), (iii) **certificar** um modelo de
  terceiros sem ver o interior (BProm), (iv) derrubar o alinhamento **pela interface** (Prefill) e
  (v) **cadeia de suprimentos de componentes de LLM** (MCP). Não encontramos nenhum trabalho que
  trate o **derivado de um modelo aberto como artefato de cadeia de suprimentos** cuja propriedade
  de segurança (recusa) precisa sobreviver à derivação. O mais próximo é um artigo curto do DSML 2026
  sobre *unlearning* que não sobrevive à quantização (sem PDF aberto, **a verificar**).

---

## 1. Método

### 1.1 Fontes

| Fonte | O que deu | Observação |
|---|---|---|
| `temas_dsn_2021_2026.csv` (393 artigos RT + Industry, listas oficiais de cada ano) | Candidatos dos anais principais | Filtro por palavras-chave no título (learn, neural, DNN, LLM, model, AI, GPU/TPU, backdoor, jailbreak, prompt, adversar, federated, inference, training, enclave/SGX/TEE/confidential, supply, package, bit-flip, fault injection) + leitura manual dos 221 títulos restantes |
| Programas oficiais do DSML: `dependablesecureml.github.io/{2021..2025}/program.html` e `program.html` (2026) | 38 trabalhos ligados a ML | O DSML existe desde 2018; o TEMAS_DSN.md diz "2024, 2025 e 2026", mas o site lista edições de 2018 a 2026 ✔. Corrigir lá numa próxima rodada |
| OpenAlex (API pública, sem `mailto`, sem chave) | DOIs, páginas e resumos | DOIs do DSML vêm dos volumes DSN-W (`dsn-w52860.2021`, `dsn-w54100.2022`, `dsn-w58399.2023`, `dsn-w60302.2024`, `dsn-w65791.2025`, `dsn-w70714.2026`) |
| arXiv (API pública) e repositórios institucionais | Versões abertas | Só acesso aberto |

- **dblp não foi usado** (bloqueio anti-robô, não contornado).
- **Não usamos** sites de pirataria, e-mail nem dado pessoal em parâmetros.
- **Fora do escopo:** trabalhos que só *aplicam* ML/LLM a outra tarefa (detecção de vulnerabilidade,
  phishing, intrusão, senhas, decompilação, fuzzing). Alguns aparecem na §5 como apoio.
- **Outros workshops** do DSN (ex.: CRAI 2026, IA agêntica) não foram varridos.

### 1.2 Critério de relevância para nós

- **Alta:** define um problema vizinho do nosso (integridade, custódia, controle de uso ou
  certificação de modelo; burla de alinhamento; cadeia de suprimentos de componentes de LLM; uma
  propriedade de segurança que se perde por transformação do modelo).
- **Média:** dá molde de forma (modelo de falhas, métricas, injeção) ou é peça de motivação.
- **Baixa:** ML clássico (visão, FL, robustez a evasão) sem ponte direta com custódia ou derivados.

### 1.3 Limites

- Resumos de 2026 (RT) faltam na OpenAlex; para esses, o "problema em uma frase" sem ✔ vem do
  título ou do GUIA e leva **(a verificar)**.
- O Industry Track de 2026 não tem registro completo na OpenAlex; os DOIs DSN-S 2026 abaixo vieram
  da busca por título.

---

## 2. Tabela

Legenda de trilha: **RT** = Research Track; **Ind** = Industry/DSN-S; **DSML** = workshop.
Relevância: **A** alta, **M** média, **B** baixa. PDF: nome em `dsn/`, "inst." = sem versão aberta
encontrada, "—" = não buscado (relevância baixa).

### 2.1 Anais principais (RT e Industry)

| # | Ano | Trilha | Título (curto) | DOI 10.1109/… | Problema em uma frase | Avaliação | Rel. | PDF |
|---|---|---|---|---|---|---|---|---|
| 1 | 2021 | RT | Ranger: Low-cost Fault Corrector for DNNs via Range Restriction | dsn48987.2021.00018 | Falhas transitórias de hardware corrompem a predição de DNNs em domínios críticos; propõe corrigir a saída sem recomputar | Injeção de falhas em vários DNNs; overhead | B | — |
| 2 | 2021 | RT | Decamouflage | dsn48987.2021.00023 | Atacante esconde imagem maliciosa que só aparece após o redimensionamento de entrada da CNN; detectar o ataque | Três detectores; limiar transferível entre datasets | B | — |
| 3 | 2021 | RT | GARFIELD: System Support for Byzantine ML | dsn48987.2021.00021 | Nós bizantinos corrompem o treino distribuído em frameworks comuns; dar resiliência bizantina com pouco código | Biblioteca sobre TF/PyTorch; custo da resiliência em CPU/GPU | B | — |
| 4 | 2021 | RT | MILR: Mathematically Induced Layer Recovery for CNNs | dsn48987.2021.00024 | Erros de bit (naturais ou provocados) nos parâmetros de CNN tornam a inferência não confiável; detectar e recuperar por software | Injeção de erros de 1 e vários bits | B | — |
| 5 | 2021 | RT | **Plinius: Secure and Persistent ML Model Training** | dsn48987.2021.00022 | Adversário com controle de SO, hipervisor e acesso físico (exceto ao pacote do processador) quer ler ou alterar pesos e dados de treino numa nuvem não confiável; treinar em SGX com recuperação rápida após falha ✔ | Protótipo SGX-Darknet + memória persistente; MNIST; salvar/restaurar 3,2×/3,7× mais rápido que disco ✔ | **A** | 2021_yuhala_plinius.pdf |
| 6 | 2021 | Ind | Adversarial Attack and Defence for Android Malware Detection | dsn-s52858.2021.00025 | Atacante modifica apps para enganar detectores de malware baseados em ML; tornar os detectores robustos | 12 detectores; taxa de engano | B | — |
| 7 | 2022 | RT | GoldenEye | dsn53405.2022.00031 | Formatos numéricos novos em aceleradores de DNN mudam a resiliência a bit-flips; avaliar por simulação com injeção | Simulador funcional no PyTorch | B | — |
| 8 | 2022 | RT | The Fault in Our Data Stars | dsn53405.2022.00027 | Dados de treino rotulados com defeito levam modelos críticos a errar; comparar cinco técnicas de mitigação | Estudo experimental por dataset, modelo e tipo de falha; *ensemble* é o mais resiliente | M | inst. |
| 9 | 2022 | RT | DiverseAV: Temporal Data Diversity in AV Compute | dsn53405.2022.00021 | Corrupção silenciosa de dados por falha de hardware no computador do veículo autônomo ameaça a segurança; detectar com redundância de dados barata | Injeção de falhas em pilha de AV | B | — |
| 10 | 2022 | Ind | SimLane | dsn-s54099.2022.00013 | Detecção de faixa falha sob variações ambientais comuns; benchmark orientado a risco | Benchmark | B | — |
| 11 | 2022 | Ind | Groq Deterministic Tensor-Streaming Processors | dsn-s54099.2022.00016 | Manter execução determinística e confiável ao escalar aceleradores de ML | Relato de projeto | B | — |
| 12 | 2023 | RT | **Don't Knock! Rowhammer at the Backdoor of DNN Models** | dsn58367.2023.00023 | Atacante sem acesso de escrita aos pesos usa Rowhammer para implantar backdoor num classificador em execução, em hardware real | Ataque fim a fim em hardware real | M | 2023_tol_rowhammer-backdoor.pdf |
| 13 | 2023 | RT | Fabricated Flips: Poisoning FL without Data | dsn58367.2023.00036 | Cliente malicioso sem dados nem escuta degrada o modelo federado | Ataque contra defesas de agregação robusta | B | — |
| 14 | 2023 | RT | CIP: FL against Membership Inference | dsn58367.2023.00037 | Servidor, cliente ou terceiro infere se um registro estava no treino federado; defender por perturbação no cliente | Ataques MI × utilidade | B | — |
| 15 | 2023 | RT | Adversarial Robustness of Point Cloud Segmentation | dsn58367.2023.00056 | Amostras adversariais degradam ou escondem objetos na segmentação 3D | Estudo comparativo | B | — |
| 16 | 2023 | RT | Poisoning Online Learning Filters | dsn58367.2023.00033 | Atacante envenena filtros de DDoS com aprendizado online mudando o perfil de tráfego | Ataque e avaliação | B | — |
| 17 | 2023 | RT | ReFace | dsn58367.2023.00038 | Ataque adversarial em tempo real e transferível contra reconhecimento facial | Taxa de sucesso, transferência | B | — |
| 18 | 2023 | RT | MalAder | dsn58367.2023.00027 | Ataque só com rótulo contra detectores de malware por sequência de API | Black-box, decisão | B | — |
| 19 | 2023 | Ind | PyTorchALFI (extensão do PyTorchFI) | dsn-s58398.2023.00025 | Falhas de hardware geram erros silenciosos em redes neurais; tornar a injeção de falhas em larga escala repetível e comparável | Ferramenta + exemplos | B | — |
| 20 | 2024 | RT | Privacy Leakage from Logits in Federated Distillation | dsn58291.2024.00029 | Os logits enviados na destilação federada permitem reconstruir dados privados | Ataque + defesa LabelAvg | B | 2024_xiao_logits-leakage.pdf |
| 21 | 2024 | RT | Robustness of RL with Adversarial Policy | dsn58291.2024.00038 | Adversário manipula agentes de RL por política adversarial | Ambientes multiagente | B | — |
| 22 | 2024 | RT | Goldfish: Federated Unlearning | dsn58291.2024.00035 | Remover a contribuição de um cliente do modelo federado com eficiência **(a verificar)** | **(a verificar)** | B | — |
| 23 | 2024 | Ind | Road Decals as Trojans | dsn-s60304.2024.00039 | Padrões adversariais pintados na via enganam a detecção de objetos de AV | Experimentos | B | — |
| 24 | 2024 | Ind | Federated Unlearning in the IoV | dsn-s60304.2024.00034 | *Unlearning* federado em veículos **(a verificar)** | **(a verificar)** | B | — |
| 25 | 2025 | RT | **BProm: Prompting the Unseen** | dsn64029.2025.00058 | Um avaliador só com acesso caixa-preta a um modelo de terceiro (mercado de modelos, MLaaS; no resumo dos anais, "centros de teste" de certificação) precisa decidir se ele tem backdoor ✔ | 5 datasets de imagem, 9 ataques (inclusive adaptativos), 10 linhas de base; AUROC/F1; falha declarada contra backdoor *all-to-all* ✔ | **A** | 2025_huang_backdoor-prompting.pdf |
| 26 | 2025 | RT | **Multi-version ML and Rejuvenation** | dsn64029.2025.00071 | Falhas acidentais, OOD e ataques deixam módulos de percepção "comprometidos mas funcionais"; tolerar com réplicas, votador e rejuvenescimento | Redes de Petri + injeção (PyTorchFI) + CARLA (GUIA §4.9) | **A** | 2025_wen_multiversion-ml.pdf |
| 27 | 2025 | RT | ReMlX | dsn64029.2025.00069 | Dados de treino defeituosos reduzem a acurácia; manter a capacidade preditiva com *ensembles* ponderados por XAI | Curvas × quantidade de falha (0–50%), RQs (GUIA §4.9) | M | 2025_chan_remlx.pdf |
| 28 | 2025 | RT | Safety Interventions against Adversarial Patches in openpilot | dsn64029.2025.00062 | Ataques à percepção de um ADAS aberto causam riscos; avaliar mecanismos de segurança | Simulação | B | — |
| 29 | 2025 | RT | SAM-CP: adversarial attack via MLM | dsn64029.2025.00029 | Gerar exemplos adversariais de texto imperceptíveis e eficazes | Benchmarks de NLP | B | — |
| 30 | 2025 | RT | VerifyVFL | dsn64029.2025.00022 | Partes maliciosas em FL vertical manipulam gradientes ou inferem rótulos; tornar gradientes verificáveis | Protocolo criptográfico + overhead | B | — |
| 31 | 2025 | RT | An Analysis of Malicious Packages in OSS | dsn64029.2025.00045 | Pacotes maliciosos entram em ecossistemas OSS; caracterizar em larga escala (24.356 pacotes) | Estudo empírico com RQs (GUIA [3]) | M | 2025_zhou_malicious-packages.pdf |
| 32 | 2025 | RT | RuleLLM | dsn64029.2025.00072 | Gerar regras de detecção de pacotes maliciosos com LLM | Precisão/revocação (GUIA [4]) | B | 2025_zhang_malicious-package-rules.pdf |
| 33 | 2025 | Ind | Polymorphic Prompt (PPA) | dsn-s65789.2025.00037 | Prompt injection quebra a estrutura previsível do prompt de sistema de agentes LLM; aleatorizar a estrutura | Ataques existentes × defesas | M | 2025_wang_polymorphic-prompt.pdf |
| 34 | 2025 | Ind | Adversarial Patches Transferability in Real Systems | dsn-s65789.2025.00040 | Patches adversariais transferem para sistemas reais de reconhecimento em CPS | Testes em sistemas reais | B | — |
| 35 | 2025 | Ind | Large-Scale AI Infra Reliability (Llama 3) | dsn-s65789.2025.00054 | Uma falha de GPU interrompe treinos de LLM em dezenas de milhares de GPUs; caracterizar falhas e estratégias | Revisão + experiência em 16K GPUs | M | inst. |
| 36 | 2025 | Ind | LLMPrism | dsn-s65789.2025.00034 | O provedor de plataforma de treino de LLM tem pouca visibilidade para diagnosticar problemas de desempenho | Plataforma de produção | B | — |
| 37 | 2026 | RT | **A First Look at the Security Issues in the MCP Ecosystem** | dsn69566.2026.00046 | Registros com verificação fraca deixam servidores MCP adversariais ou sequestrados entrar nos hosts, e metadados de ferramenta controlados pelo atacante induzem ações que o host executa sem verificação ✔ | 67.057 servidores em 6 registros; 4 hosts; ferramenta MCPInspect pré-integração; divulgação aos afetados ✔ | **A** | 2026_li_mcp.pdf |
| 38 | 2026 | RT | **AnBridge: Protecting On-Device AI with AVF** | dsn69566.2026.00081 | Adversário de software com controle do SO Android quer roubar ou alterar modelo e dados de IA no dispositivo; portar o código de IA para uma VM protegida sem reescrevê-lo ✔ | Latência e vazão (overhead 2–14%), 2 apps de IA, TCB +~600 LOC ✔ | **A** | 2026_farina_anbridge.pdf |
| 39 | 2026 | RT | **Prefill: Bypassing Safety Alignment via API Design** | dsn69566.2026.00054 | Um usuário de API caixa-preta que controla o início da resposta desloca o modelo da recusa para a obediência; a propriedade ameaçada é o alinhamento de segurança ✔ | 14 modelos, AdvBench (520), juiz por LLM, RQ1–RQ3, defesas ✔ | **A** | 2026_li_prefill-jailbreak.pdf (versão arXiv, título anterior) |
| 40 | 2026 | RT | **LymphNode: Access Control for DNNs** | dsn69566.2026.00062 | Na borda, um adversário com acesso de oráculo extrai ou inverte o modelo (IP); negar utilidade a consultas sem credencial ✔ | CIFAR-10/MNIST/SVHN, 6 arquiteturas; robustez a falsificação, fine-tuning e poda (GUIA [50]) ✔ | **A** | 2026_pei_lymphnode.pdf |
| 41 | 2026 | RT | TPU-FI: Realistic Radiation Faults in ML Accelerators | dsn69566.2026.00017 | Modelos de falha sintéticos subestimam o efeito da radiação em TPUs; derivar o modelo de falhas do feixe e validar o injetor | Feixe + 6 milhões de injeções (GUIA §4.9) | M | 2026_coelho_radiation-tpu.pdf |
| 42 | 2026 | RT | LLMGuard: Fault Diagnosis for LMaaS | dsn69566.2026.00018 | Diagnosticar falhas de um serviço de LLM com agentes **(a verificar)** | **(a verificar)** | M | inst. |
| 43 | 2026 | RT | RIPE-II: Indirect Injections in RAG | dsn69566.2026.00078 | Conteúdo envenenado no corpus de recuperação injeta instruções no LLM; benchmark **(a verificar)** | **(a verificar)** | M | inst. |
| 44 | 2026 | RT | VCAligner | dsn69566.2026.00048 | O artefato publicado pode não corresponder ao código-fonte auditado ("provenance gap", caso XZ); ligar distribuição a commit (GUIA [5]) | 2.984 pacotes PyPI | M | inst. |
| 45 | 2026 | RT | Beyond Corner Patches: Semantic Backdoor in FL | dsn69566.2026.00032 | Backdoor semântico implantado por cliente federado **(a verificar)** | **(a verificar)** | B | — |
| 46 | 2026 | RT | Efficient Anomaly Detection and Exclusion for Robust FL | dsn69566.2026.00055 | Excluir clientes anômalos em FL com custo baixo **(a verificar)** | **(a verificar)** | B | — |
| 47 | 2026 | RT | From Centralized Learning to Federated: Keeping Reliability | dsn69566.2026.00057 | Manter a confiabilidade ao passar do treino central para o federado **(a verificar)** | **(a verificar)** | B | — |
| 48 | 2026 | RT | LaserTag | dsn69566.2026.00063 | Perturbações adversariais físicas em pipelines industriais de visão **(a verificar)** | Ferramenta **(a verificar)** | B | — |
| 49 | 2026 | RT | SpeechShield | dsn69566.2026.00037 | Proteger a voz contra clonagem por síntese **(a verificar)** | **(a verificar)** | B | — |
| 50 | 2026 | RT | TLG: Gradient Inversion in FL | dsn69566.2026.00066 | Reconstruir dados de clientes a partir de gradientes **(a verificar)** | **(a verificar)** | B | — |
| 51 | 2026 | RT | VulLens | dsn69566.2026.00025 | Detectores de vulnerabilidade com ML sofrem ataques de evasão **(a verificar)** | **(a verificar)** | B | — |
| 52 | 2026 | RT | MIRAGE → CLEAR | dsn69566.2026.00072 | Explicar anomalias por componente na percepção de AV **(a verificar)** | **(a verificar)** | B | — |
| 53 | 2026 | RT | DP Quantization for FL | dsn69566.2026.00051 | Quantização com privacidade diferencial em FL **(a verificar)** | **(a verificar)** | B | — |
| 54 | 2026 | Ind | Aegis: Cross-Domain Resource Abuse in MCP | dsn-s70715.2026.00036 | Agentes LLM abusam de recursos via ferramentas MCP; impor política fina fora do modelo (GUIA [47]) | **(a verificar)** | M | 2026_priya_aegis.pdf |
| 55 | 2026 | Ind | Event Burst Trigger | dsn-s70715.2026.00020 | Backdoor de disponibilidade em detecção de objetos com SNN de eventos | **(a verificar)** | B | — |
| 56 | 2026 | Ind | Robustness Metric for ML in Aviation | dsn-s70715.2026.00029 | Métrica de robustez para certificar componentes de ML em aviação **(a verificar)** | **(a verificar)** | B | — |
| 57 | 2026 | Ind | AIReSim | (a verificar) | Simular a confiabilidade de clusters de IA em larga escala **(a verificar)** | Simulador | B | — |
| 58 | 2026 | Ind | Anatomy of Silent Data Corruption in GPUs | (a verificar) | Padrões de erro silencioso em GPUs **(a verificar)** | Estudo de campo | B | — |

### 2.2 Workshop DSML (2021–2026)

DOIs no prefixo 10.1109/; "(a v.)" = DOI não encontrado.

| # | Ano | Título (curto) | DOI | Problema em uma frase | Avaliação | Rel. | PDF |
|---|---|---|---|---|---|---|---|
| 59 | 2021 | Fault-Tolerant Low-Precision DNNs using XAI | dsn-w52860.2021.00036 | Tolerar falhas em DNNs de baixa precisão guiado por XAI | **(a verificar)** | B | — |
| 60 | 2021 | Detecting DNN Defects with Data Flow Analysis | dsn-w52860.2021.00039 | Achar defeitos em DNNs por análise de fluxo de dados | **(a verificar)** | B | — |
| 61 | 2021 | Poisoning via Generative Text-to-Image Synthesis | dsn-w52860.2021.00035 | Envenenar treino com imagens sintéticas | **(a verificar)** | B | — |
| 62 | 2021 | RADICS: Runtime Assurance of Intelligent Control | dsn-w52860.2021.00038 | Garantia em execução para controle distribuído com ML | **(a verificar)** | B | — |
| 63 | 2021 | Byzantine FT Distributed ML (D-SGD + CGE) | (a v.) | Agentes bizantinos em aprendizado distribuído | Teórica/experimental | B | — |
| 64 | 2022 | Robustness Testing of Anomaly Detection in CPS | dsn-w54100.2022.00017 | Testar robustez de detectores de anomalia em CPS | **(a verificar)** | B | — |
| 65 | 2022 | Resilient Ensembles against Training Data Faults (talk) | dsn-w54100.2022.00020 | Precursor do ReMlX | **(a verificar)** | B | — |
| 66 | 2022 | Filter Ensembles to Detect Adversarial Inputs | (a v.) | Detectar entradas adversariais | **(a verificar)** | B | — |
| 67 | 2022 | FL with Anomaly Client Detection | dsn-w54100.2022.00016 | Excluir clientes anômalos | **(a verificar)** | B | — |
| 68 | 2022 | Non-IID data in DP Federated Learning | (a v.) | Efeito de dados não-IID em FL com DP | **(a verificar)** | B | — |
| 69 | 2023 | Adversarial Patch Detection (High Entropy) | dsn-w58399.2023.00040 | Detectar e mitigar patches adversariais | **(a verificar)** | B | — |
| 70 | 2023 | IB-RAR | dsn-w58399.2023.00041 | Regularizar para robustez adversarial | **(a verificar)** | B | — |
| 71 | 2023 | Pasting Attacks on Image Classification | dsn-w58399.2023.00042 | Ataques por colagem em classificação | **(a verificar)** | B | — |
| 72 | 2023 | FADO: FL Attack and Defense Orchestrator | dsn-w58399.2023.00043 | Orquestrar ataques e defesas em FL para avaliação | Ferramenta | B | — |
| 73 | 2023 | N-version Perception and Rejuvenation | dsn-w58399.2023.00044 | Precursor do Multi-version ML [26] | **(a verificar)** | B | — |
| 74 | 2024 | Adversarial Patch Detection (Depth Contrast) | dsn-w60302.2024.00020 | Detectar patches por contraste de profundidade | **(a verificar)** | B | — |
| 75 | 2024 | Unlearning Backdoors via Gradient-Based Pruning | dsn-w60302.2024.00021 | Remover um backdoor já implantado modificando o modelo (poda) sem retreinar do zero | **(a verificar)** | M | 2024_dunnett_backdoor-pruning.pdf |
| 76 | 2024 | Universal Soldier: UAPs for Detecting Backdoors | dsn-w60302.2024.00024 | Decidir se um modelo tem backdoor usando perturbações universais | **(a verificar)** | M | 2024_xu_universal-soldier.pdf |
| 77 | 2024 | TrustDDL | dsn-w60302.2024.00022 | Treino distribuído com privacidade e tolerância bizantina | **(a verificar)** | B | — |
| 78 | 2024 | Environmental Influences on Object Detection | dsn-w60302.2024.00018 | Medir efeito do ambiente na detecção | **(a verificar)** | B | — |
| 79 | 2024 | Hybrid CNNs with Reliability Guarantee | (a v.) | CNNs com garantia de confiabilidade | **(a verificar)** | B | — |
| 80 | 2025 | Revisiting Adversarial Perception Attacks on ADS | dsn-w65791.2025.00071 | Reavaliar ataques e defesas de percepção em AV | **(a verificar)** | B | — |
| 81 | 2025 | Transferability CNN → ChatGPT-4 variants | dsn-w65791.2025.00072 | Exemplos adversariais de CNN transferem para LLMs multimodais? | **(a verificar)** | B | — |
| 82 | 2025 | Risk Profiling Defenses against Evasion | dsn-w65791.2025.00073 | Defender DNNs contra evasão com perfis de risco | **(a verificar)** | B | — |
| 83 | 2025 | Audio Jailbreak on SpeechGPT (white-box) | dsn-w65791.2025.00074 | Um atacante com acesso aos pesos de um modelo de fala aberto contorna o alinhamento por entrada de áudio | **(a verificar)** | M | 2025_ma_audio-jailbreak.pdf |
| 84 | 2025 | FHE ML Tuxedo | dsn-w65791.2025.00075 | Encapsular ML com criptografia homomórfica | **(a verificar)** | B | — |
| 85 | 2025 | Hallucination Detection via Beam Search | dsn-w65791.2025.00076 | Detectar alucinação de LLM por consistência semântica | **(a verificar)** | B | — |
| 86 | 2025 | Securing AI Code Generation (pattern patching) | dsn-w65791.2025.00077 | Corrigir código inseguro gerado por IA | **(a verificar)** | B | — |
| 87 | 2025 | Reputation for Decentralized FL | dsn-w65791.2025.00079 | Incentivar cooperação em FL descentralizado | **(a verificar)** | B | — |
| 88 | 2026 | **Trust Without Safeguards: Red-Teaming ProteinMPNN** | dsn-w70714.2026.00040 | Um modelo aberto de desenho de proteínas, usado sem salvaguardas em pipelines abertos, pode ser levado a saídas de risco **(a verificar)** | Red-teaming **(a verificar)** | M | inst. |
| 89 | 2026 | Drivers of Secure and Correct Code | dsn-w70714.2026.00031 | Fatores (tamanho, pré-treino, dados) que explicam código seguro em LLMs | Estudo fatorial | B | — |
| 90 | 2026 | **On the Reliability of Targeted Unlearning in 4-Bit Quantized LLMs** | dsn-w70714.2026.00034 | Uma remoção de conhecimento feita no modelo pode não sobreviver à quantização em 4 bits, ou seja, uma transformação comum do derivado desfaz uma propriedade de segurança **(a verificar; só título, 5 pp.)** | **(a verificar)** | **A** | inst. |
| 91 | 2026 | Latent Space Probing for Adult Content in Video Generation | dsn-w70714.2026.00039 | Filtros por prompt ou por saída não veem as representações internas; sondar o latente durante a geração para detectar conteúdo proibido ✔ | 11.039 clipes, CogVideoX, F1 97,29%, 4–6 ms; não testa sondas contra adversário ✔ | M | 2026_khatri_latent-probing.pdf |
| 92 | 2026 | AdROD | dsn-w70714.2026.00043 | Redundância adaptativa em detecção de objetos | **(a verificar)** | B | — |
| 93 | 2026 | Driver-Level FI for AI Accelerators (proposta) | dsn-w70714.2026.00042 | Injeção de falhas no driver de aceleradores | Proposta | B | — |
| 94 | 2026 | **Extreme Variance of Certified Robustness Across Seeds** | dsn-w70714.2026.00041 | Modelos que só diferem na semente têm robustez certificada muito diferente, então um resultado de verificação não é confiável sem intervalo de confiança ✔ | 10 ResNet4 por dataset (MNIST e Marte); desvio de 28,9% na robustez certificada contra 0,057% na acurácia ✔ | M | 2026_le_certified-variance.pdf |
| 95 | 2026 | Model Chunking in Decentralized Learning | dsn-w70714.2026.00032 | Fragmentar modelos vira vazamento de privacidade | **(a verificar)** | B | — |
| 96 | 2026 | Color Matters: Trigger Color in FL Backdoor | (a v.) | Cor do gatilho afeta backdoor federado | **(a verificar)** | B | — |

Não entraram (aplicam ML a outra tarefa ou não são de ML): DSML'26 LLM-PEA, Network Tomography e
Shades of Gray; DSML'21 Queueing e P2P FL; DSML'22 ICS attack mitigation e Coq. Nos anais: Asteria,
SEVulDet, PagPassGPT, ChatScam, detecção de vulnerabilidade com LLM, LUMEN, SPDAgent etc. (ver
TEMAS_DSN.md).

---

## 3. Fichas dos lidos (✔)

Foco: **como cada um formula o problema** (adversário, propriedade, sistema, premissas) e o que
isso nos dá. Fichas mais longas de Prefill, LymphNode e BProm estão no GUIA §4.7.

### ✔ [39] Prefill (DSN 2026, RT)
- **Formulação:** atacante com acesso caixa-preta à API, sem conhecer pesos; objetivo: obter conteúdo
  nocivo de um modelo alinhado; capacidade-chave: ditar o início da resposta (*prefill*). Métrica:
  ASR = esperança do juiz sobre a saída (§III-A).
- **Avaliação:** 14 modelos, AdvBench (520 pedidos), dois juízes (string e LLM), RQ1–RQ3; defesas de
  filtro de conteúdo (Llama-Guard) e duas propostas.
- **Limites declarados:** só caixa-preta; sem validação por ativações internas.
- **Para nós:** prova que o DSN aceita "alinhamento como propriedade de dependabilidade quebrada por
  uma funcionalidade legítima". No nosso caso a funcionalidade é o fine-tuning, e o adversário tem
  pesos (white-box). Também obriga o DNAT a **controlar a interface de inferência** do derivado.

### ✔ [40] LymphNode (DSN 2026, RT)
- **Formulação:** três partes (dono, operador de borda, usuários autorizados); adversário
  *gray-box* com oráculo; não tem chave, memória nem gradientes. O operador roda o modelo num
  "runtime confiável que preserva a integridade dos parâmetros" (§III-A).
- **Para nós:** a proteção mora **no modelo** e depende de a infraestrutura garantir a integridade
  dos pesos. O DNAT é exatamente essa infraestrutura. A avaliação mostra que fine-tuning com pesos
  e 10% dos dados recupera parte da utilidade (GUIA [50]): **derivados** desfazem proteções
  embutidas, o que reforça o portão.

### ✔ [25] BProm (DSN 2025, RT)
- **Formulação:** defensor só com consultas caixa-preta e um pequeno conjunto limpo (1–10%) decide se
  um modelo de terceiro tem backdoor. O PDF (arXiv) motiva com mercados de modelos (BigML, ONNX zoo)
  e MLaaS. O **resumo dos anais** (OpenAlex) fala em "centros de teste" que certificam modelos sem
  ver o interior. As duas versões divergem; o GUIA registrou só a do PDF.
- **Avaliação:** AUROC/F1, 9 ataques, 10 linhas de base; falha contra backdoor *all-to-all*.
- **Para nós:** é o precedente de **certificação no nível do modelo** antes de liberar. Diferenças:
  BProm é caixa-preta e sem referência; nosso portão tem o **base custodiado** como referência
  atestada e julga recusa, não backdoor de classificador.

### ✔ [38] AnBridge (DSN 2026, RT)
- **Formulação:** adversário de software que compromete o SO Android inteiro (rootkit) quer vazar
  ou alterar modelo e dados de IA; hipervisor pKVM confiável; fora do escopo: DoS, canais laterais,
  código defeituoso na pVM, entradas adversariais e **extração de modelo por entradas** (§II-A).
  Problema técnico: portar código nativo de IA para a pVM sem reescrevê-lo.
- **Avaliação:** latência/vazão, overhead de 2–14%, dois apps de IA, TCB +~600 LOC.
- **Para nós:** precedente direto de "modelo dentro de VM protegida com atestação" no DSN, de um grupo
  forte em dependabilidade (Cinque, Bagchi). O nosso adversário é o oposto: **quem está dentro da VM
  com os pesos** (o usuário que treina), não o host.

### ✔ [37] MCP Ecosystem (DSN 2026, RT)
- **Formulação:** cadeia em dois estágios: (I) registros com verificação fraca deixam entrar
  servidores adversariais ou sequestrados (vazamento de credencial, sequestro de namespace);
  (II) metadados de ferramenta controlados pelo atacante guiam o LLM, e o host executa sem
  verificação independente.
- **Avaliação:** 67.057 servidores em 6 registros, 4 hosts, ferramenta MCPInspect **antes da
  integração**; 833 servidores vulneráveis; divulgação responsável.
- **Para nós:** é a formulação de **cadeia de suprimentos de componentes de LLM** que o DSN aceitou
  (registro → integração → execução) e a solução tem a forma do nosso portão (checagem
  pré-integração). Mas o artefato é o servidor de ferramentas, não o peso.

### ✔ [5] Plinius (DSN 2021, RT)
- **Formulação:** treinar modelos em nuvem não confiável; adversário com acesso físico e controle de
  SO e hipervisor; objetivos: confidencialidade e integridade dos parâmetros durante o treino, da
  réplica persistente e dos dados (§III). Junta segurança (SGX) e **tolerância a falhas** (memória
  persistente, recuperação rápida).
- **Para nós:** prova que o DSN aceita "segurança + recuperação" no mesmo artigo de ML em TEE. O
  modelo de ameaça de Plinius supõe que "o código do enclave é correto e não vaza segredos de
  propósito"; o nosso precisa do contrário: o **código do usuário dentro da CVM é hostil**.

### ✔ [94] Variância da robustez certificada (DSML 2026)
- **Formulação:** a dependabilidade de um resultado de verificação é ameaçada pela aleatoriedade do
  treino; modelos que só diferem na semente têm robustez certificada muito diferente.
- **Avaliação:** 10 sementes por dataset; desvio de 28,9% contra 0,057% na acurácia; a "semente de
  sorte" nem sempre se mantém num segundo conjunto de teste.
- **Para nós:** o portão julga derivados que diferem do base por treino. Precisamos reportar
  **intervalos de confiança** do veredito e testar o portão em derivados com sementes diferentes
  (falso alarme em F1). Vale como ameaça à validade citada de dentro da comunidade DSN.

### ✔ [91] Sondagem de espaço latente (DSML 2026)
- **Formulação:** moderação por prompt ou por saída é cega às representações internas; sondas leves
  no latente detectam conteúdo proibido com baixo custo.
- **Limites declarados:** não avaliou robustez das sondas a perturbação adversarial; um só modelo.
- **Para nós:** precedente de usar **sinais internos** como juiz barato. O limite declarado é o nosso
  problema central: um derivado treinado contra o portão (F4) é exatamente o adversário que eles
  deixaram de fora.

---

## 4. Síntese

### 4.1 Formulações de problema que o DSN já aceitou nesta área

| # | Formulação (adversário ou falha → propriedade → sistema) | Exemplos | Forma de avaliação típica |
|---|---|---|---|
| F1 | **Falha de hardware** → saída correta do modelo (corrupção silenciosa) → aceleradores e infra de treino | Ranger, MILR, GoldenEye, DiverseAV, PyTorchALFI, TPU-FI, Llama 3, SDC em GPU | Injeção de falhas em escala, às vezes validada contra campo (feixe) |
| F2 | **Dados de treino defeituosos** (acidental) → capacidade preditiva → pipeline de treino | Fault in Data Stars, ReMlX | Curvas × quantidade de falha, RQs, overhead |
| F3 | **Atacante na entrada** (evasão, patch) → robustez da decisão → percepção, detectores | ~25 trabalhos (RT e DSML) | Taxa de sucesso, transferência, simulação |
| F4 | **Atacante no treino ou nos pesos** (envenenamento, backdoor, Rowhammer) → integridade do comportamento → modelo, FL | Rowhammer, Fabricated Flips, Beyond Corner Patches, BProm, DSML'24 | Ataque fim a fim ou detector com AUROC e adaptativos |
| F5 | **Atacante curioso** → privacidade dos dados → FL, destilação | Logits, CIP, TLG, unlearning federado | Reconstrução, MI |
| F6 | **Host comprometido ou oráculo** → confidencialidade e integridade do modelo (IP) → nuvem, borda, celular | Plinius (SGX), AnBridge (pVM), LymphNode | Overhead, TCB, robustez da proteção |
| F7 | **Usuário que controla a interface** → alinhamento de segurança (recusa) → LLM como serviço, agentes | Prefill, PPA, RIPE-II, Audio Jailbreak (DSML) | Benchmark multi-modelo, ASR com juiz, RQs |
| F8 | **Componente de terceiro malicioso que entra por um registro** → integridade do sistema que o integra → ecossistemas de pacotes e de ferramentas LLM | MCP, Aegis, pacotes maliciosos, VCAligner | Medição em larga escala + ferramenta de triagem |
| F9 | **Falhas operacionais** → disponibilidade e desempenho → serviço/plataforma de LLM | LLMGuard, LLMPrism, AIReSim | Dados de produção, diagnóstico |
| F10 | **Transformação ou aleatoriedade do modelo** → validade de uma propriedade verificada | Variância de robustez certificada, *unlearning* × quantização (DSML 2026) | Repetição com sementes ou transformações |

Padrões úteis:
- Os artigos de LLM aceitos no RT são **2025–2026** e usam **RQs + benchmark multi-modelo + juiz**.
- A comunidade de dependabilidade (Pattabiraman, Machida, Bagchi, Cinque) publica F1/F2 com
  **modelo de falhas explícito, injeção e quantidade de falha**. É o molde da E8 §9.
- F6 sempre protege o modelo **de fora para dentro** (host ou consultante hostil).
- F8 entrou com o MCP: **o DSN já reconhece a cadeia de suprimentos de LLM**, mas pelo lado das
  ferramentas.

### 4.2 Lacunas para o nosso problema

1. **Pesos abertos como artefato de cadeia de suprimentos.** Não encontramos no DSN 2021–2026 (RT,
   Industry, DSML) trabalho sobre hubs de modelos, modelos maliciosos publicados, serialização
   insegura de pesos ou linhagem de derivados. F8 cobre pacotes e servidores MCP; F4 cobre backdoor,
   mas não a **distribuição** do modelo.
2. **A propriedade "a recusa sobrevive à derivação".** F7 quebra o alinhamento pela interface; F4
   implanta comportamento pelo treino; nenhum define, como propriedade de dependabilidade, que um
   **derivado liberado** mantém a recusa do pai. O mais próximo é F10 no DSML 2026 (*unlearning*
   desfeito por quantização), que é curto, de workshop e sem PDF aberto **(a verificar)**.
3. **O adversário de dentro.** Em F6 o modelo é protegido do host (Plinius, AnBridge) ou de quem
   consulta (LymphNode, que supõe integridade dos parâmetros). Ninguém trata o **usuário legítimo
   com acesso white-box aos pesos dentro do ambiente confidencial** como adversário. É a inversão que
   a custódia + portão faz.
4. **Certificação com referência atestada.** BProm certifica sem ver o interior e sem referência. Não
   há precedente de um juiz que compara o derivado com um **base custodiado** que o atacante não pode
   forjar (o ponto da E6 §3).
5. **Portão adaptativo.** As sondas internas (DSML'26) e o PPA não avaliam atacante que treina contra
   o detector. O BProm testa ataques adaptativos e falha num caso. Uma RQ de atacante adaptativo (E8
   RQ4) responde a uma lacuna que os próprios artigos declaram.
6. **Métrica "liberação silenciosa".** O DSN premia o vocabulário de corrupção silenciosa (F1). Não
   encontramos quem o aplique a derivados de modelo.
7. **Estabilidade do veredito.** O DSML'26 mostra que propriedades verificadas variam muito com a
   semente; o portão precisa reportar IC e falso alarme sobre derivados benignos repetidos.
8. **Prêmio por entradas que exploram o modelo (bounty).** Red-teaming aparece só como estudo
   (ProteinMPNN, DSML'26) ou como avaliação de ataque. Não encontramos red-teaming **incentivado e
   verificado** como mecanismo de dependabilidade de modelos.

### 4.3 Formulação candidata (para discutir, no molde dos aceitos)

> Num serviço que custodia um modelo aberto e oferece fine-tuning e edição dentro de uma CVM, um
> usuário com acesso white-box aos pesos, ou dados benignos defeituosos, produz um derivado que
> continua útil mas perdeu a recusa do base. A propriedade ameaçada é a **preservação da recusa nos
> artefatos que o serviço libera para a cadeia de suprimentos**. Queremos limitar a **taxa de
> liberação silenciosa** com um portão barato que compara o derivado com a referência custodiada,
> inclusive contra um atacante que conhece o portão.

- Molde de falhas e métricas: E8 §9 (F1–F4 acidental → adaptativo; estados H/C/N).
- Citações-âncora: Prefill [39] e LymphNode [40] (motivação), BProm [25] (certificação no nível do
  modelo), AnBridge [38] e Plinius [5] (modelo em ambiente protegido), MCP [37] (cadeia de
  suprimentos de LLM no DSN), Multi-version [26]/ReMlX [27]/TPU-FI [41] (forma), e DSML'26 [90] e
  [94] (propriedade que não sobrevive a transformação; variância do veredito).

---

## 5. Apoio fora da contagem (infra de custódia, não ML)

| Ano | Trilha | Título | DOI 10.1109/… | Por que importa | PDF |
|---|---|---|---|---|---|
| 2024 | RT | Protecting CVMs from Hardware Performance Counter Side Channels | dsn58291.2024.00031 | Limites da CVM (premissa) | 2024_lou_cvm-hpc-side-channels.pdf |
| 2025 | RT | ConfBench | dsn64029.2025.00038 | Avaliar CVMs (TDX, SEV-SNP) | inst. |
| 2025 | RT | Continuous Integrity Attestation: Keylime | dsn64029.2025.00036 | Atestação contínua e falsos alarmes | inst. |
| 2025 | Ind | Triad TEE Trusted Time | (ver GUIA) | Tempo confiável em TEE | 2025_bettinger_triad-tee-time.pdf |
| 2026 | Ind | SNAS: Secure Egress in Sandboxed Workloads | (ver GUIA) | Saída controlada de cargas isoladas | 2026_sharma_snas.pdf |
| 2023 | RT | Tabby: Java Deserialization Gadget Chains | dsn58367.2023.00028 | Análogo de serialização insegura (pesos em pickle) **(a verificar)** a pertinência | — |

## 6. Pendências

- Baixar pela instituição: [8], [35], [42], [43], [44], [88], [90]. **[90] é o mais urgente**: pode
  ser o precedente mais próximo da lacuna 2.
- Conferir o texto final (anais) do BProm: a motivação de "centros de teste" está no resumo dos
  anais, mas não no PDF arXiv que temos.
- Corrigir em TEMAS_DSN.md: o DSML existe desde 2018, não só 2024–2026.
- Os DOIs DSN-S 2026 de [55] e [56] vieram da OpenAlex por título; o de [54] vem do GUIA.
