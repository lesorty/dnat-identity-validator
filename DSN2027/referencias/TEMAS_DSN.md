# Quanto o DSN publica sobre os temas A e B (2021–2026)

**Data:** 2026-10-26 · **Dados:** `temas_dsn_2021_2026.csv` (393 linhas, uma por artigo).

- **A**: cadeia de suprimentos de software e gestão de vulnerabilidades.
- **B**: segurança e confiabilidade de modelos de ML/LLM.

## Resumo

- O Research Track teve **307 artigos** de 2021 a 2026. O Industry Track teve mais **86**, contados à parte.
- **A-nucleo:** 9 artigos (2,9%). Vieram em ondas: 3 em 2021, nenhum em 2022–2023, 1 em 2024, 3 em 2025 e 2 em 2026. O artigo de SBOM de 2024 ganhou o Distinguished Paper Award.
- **B-nucleo:** 5 artigos (1,6%), **todos em 2025–2026**: 1 em 2025 e 4 em 2026. Até 2024, B só aparece como adjacente (robustez de DNN clássica).
- **Ponte:** 1 artigo no Research Track (ecossistema MCP, 2026) e 1 no Industry Track (Aegis, MCP, 2026).
- **Com os adjacentes, os dois temas crescem juntos.** A sobe de 12,5% (2021) para 24,6% (2026) e B de 10,4% para 27,7%. No núcleo, B passa A pela primeira vez em 2026: 4 artigos contra 2.
- O programa de 2026 já tinha **duas sessões sobre LLM** ("Making LLMs Safer" e "Security aspects of using LLMs"). Cadeia de suprimentos dividiu sessão com mobile e firmware ("Mobile, Firmware & Supply Chain Security").
- **Workshops:** o DSML (ML confiável e seguro) existe desde 2018 (9ª edição em 2026; site dependablesecureml.github.io); aqui só 2024–2026 foram varridos. O CRAI (IA agêntica) estreou em 2026. Nenhum workshop de 2024–2026 tem cadeia de suprimentos como tema central; só o DSAS 2026 a lista entre os tópicos, para tecnologia espacial. Os workshops de 2027 ainda não foram escolhidos.

---

## 1. Método

### 1.1 Fontes da lista de artigos

| Ano | Lista oficial usada | RT | Ind. | DOI (fonte) | Resumo (fonte) |
|---|---|---|---|---|---|
| 2021 | Espelho do site oficial em dependability.org/dsn2021 (páginas "Regular Track" e "Industry Track") | 48 | 9 | OpenAlex | OpenAlex |
| 2022 | dsn2022.github.io/cpaccepted.html | 49 | 6 | OpenAlex | OpenAlex |
| 2023 | dsn2023.dei.uc.pt/program_research.html e program_industry.html | 47 | 11 | OpenAlex | OpenAlex |
| 2024 | dsn2024uq.github.io/Proceedings (`data/data.js`, seções "Research Track" e "Industry") | 42 | 10 | OpenAlex | Anais oficiais (`data.js`) |
| 2025 | dsn2025.github.io/cpaccepted.html | 56 | 25 | OpenAlex | OpenAlex |
| 2026 | dsn2026.github.io/cpaccepted.html | 65 | 25 | OpenAlex (só RT) | OpenAlex (8), arXiv (11), PDF local (4); o resto, nenhum |

Notas:

- **O site original de 2021 está fora do ar.** O endereço 2021.dsn.org redireciona para dsn2021.ntu.edu.tw, que não respondeu. Usamos o espelho em dependability.org. O total bate com a OpenAlex: 48 artigos mais 18 itens de front matter = 66 registros.
- **Industry Track.** Em todos os anos de 2021 a 2025, os artigos industriais estão no volume suplementar (DSN-S) na OpenAlex.
- **OpenAlex.** Fonte "IEEE/IFIP International Conference on Dependable Systems and Networks (DSN)" (S7407088029) e "… Supplemental Volume (DSN-S)" (S7407086127). Consultamos a API pública sem `mailto` e sem chave, uma requisição por ano, porque a paginação por cursor exige chave.
- **2026 não tem fonte na OpenAlex.** Os registros existem, mas sem fonte. Foram buscados pelo padrão de DOI `10.1109/dsn69566.2026.000NN`, com NN de 1 a 160. Vieram 81 registros de 2026; o DOI 00015 não apareceu. Os 65 artigos do RT têm DOI; os 25 do Industry Track de 2026 não (DSN-S 2026 sem registro na OpenAlex).
- **Casamento lista × OpenAlex.** Feito por título normalizado (exato ou similaridade ≥ 0,85, no mesmo ano ou no vizinho). Nove artigos mudaram de título entre o programa e os anais e foram casados à mão pelo conteúdo:
  - **2022, DisTA:** "System-Agnostic…" virou "Generic Dynamic Taint Tracking for Java-Based Distributed Systems".
  - **2023:** "Micro Replication – …" → "Micro Replication"; "Exploiting Code Reuse Attacks from Obfuscated Programs" → "No Free Lunch: …"; "Does TLS Provide Any Privacy Anymore? …" → "Adaptive Webpage Fingerprinting from TLS Traces"; "IDTracker: … Illegal Campaigns …" → "IDTracker: … Illicit Website Communities …"; "Faster Asynchronous Distributed Key Generation …" → "Practical Asynchronous Distributed Key Generation: …". Esse último casamento é **(a verificar)**.
  - **2026:** ML-KEM, decompilação de AVR e PDLogger, com títulos ligeiramente diferentes nos anais.
- **O dblp não foi usado.** A página tem bloqueio anti-robô, que não contornamos.

### 1.2 Códigos e regras

| Código | O que entra |
|---|---|
| `A-nucleo` | Dependências, pacotes maliciosos, SBOM, build e proveniência de software, patches de segurança, divulgação e ciclo de vida de vulnerabilidades, bug bounty e economia de vulnerabilidades, reprodução ou verificação de exploits. |
| `A-adjacente` | Ferramentas de detecção de vulnerabilidade (estática, dinâmica, ML), inclusive de canal lateral em código; segurança de smart contracts e ataques econômicos/incentivos em DeFi; fuzzing para achar bugs. |
| `B-nucleo` | Jailbreak, alinhamento, guardrails, fine-tuning nocivo, prompt injection, backdoor em modelo, roubo ou extração de modelo, controle de uso de modelo, integridade e proveniência de modelo, robustez de LLM. |
| `B-adjacente` | Robustez de ML clássico (exemplo adversarial, envenenamento, tolerância bizantina em FL, falhas e bit-flips em DNN), ML em TEE ou ambiente isolado, ataques de privacidade a modelos, LLM aplicado a outra tarefa de segurança. |
| `ponte` | Cadeia de suprimentos **de modelos** (hubs, modelos maliciosos, serialização insegura, proveniência) ou ecossistemas de ferramentas de LLM (MCP). |
| `outro` | O resto. |

Regras de desempate adotadas (as dúvidas estão na coluna `duvida` do CSV):

1. **Um código por artigo.** Na dúvida entre núcleo e adjacente, ficou adjacente. Exemplo: backdoor em DNN injetado por Rowhammer (2023) ficou `B-adjacente`.
2. **LLM aplicado a tarefa de A.**
   - Se a tarefa é tema do núcleo de A (pacote malicioso, patch de segurança), vale A. Casos: RuleLLM 2025 e SPDAgent 2026, ambos `A-nucleo`.
   - Se a tarefa é adjacente (detectar vulnerabilidade, reentrância, gerar sementes de fuzzing), vale `B-adjacente`, como pede o exemplo do enunciado.
3. **LLM aplicado a confiabilidade** (diagnóstico de incidentes, reparo de especificação) ficou `outro`, com dúvida. Exceção: LLMGuard, que trata da confiabilidade do próprio serviço de LLM, ficou `B-adjacente`.
4. **Blockchain.** Consenso, ordenação e escalabilidade ficaram `outro`. Vulnerabilidade de contrato e ataque econômico (arbitragem, suborno) ficaram `A-adjacente`.
5. **Privacidade de ML.**
   - Ataques e defesas contra inferência de pertinência ou inversão de gradiente ficaram `B-adjacente`, com dúvida.
   - DP, unlearning e FL vertical sem adversário ficaram `outro`.

**72 artigos** têm dúvida ou observação registrada.

### 1.3 O que faltou

- **Resumos de 2026.**
  - A OpenAlex tem resumo de só 8 dos 90 artigos de 2026.
  - A API do Semantic Scholar respondeu 429 (limite de taxa) duas vezes.
  - O arXiv cobriu mais 11 e os PDFs já baixados em `dsn/` cobriram 4.
  - **67 artigos de 2026 (48 do RT e 19 do Industry Track) foram classificados só pelo título**, com apoio do nome da sessão no programa.
  - Dos 9 artigos de 2026 marcados `A-nucleo`, `B-nucleo` ou `ponte`, três foram classificados só pelo título: VCAligner, SPDAgent e RIPE-II. Os três têm nota em `GUIA_DSN.md` (coleta anterior, feita com resumo), e a nota confirma o tema.
- **DOIs do Industry Track de 2026:** os 25 levam "(a verificar)" no CSV.
- **Fora da contagem:** pôsteres, Disrupt, fórum doutoral e workshops (DSN-S e DSN-W). Os itens que tocam A ou B estão listados à parte (§5).
- **Internet Archive:** estava fora do ar na coleta. Não deu para conferir versões antigas das páginas.

---

## 2. Contagem por ano e código

### Research Track

| Ano | A-nucleo | A-adjacente | B-nucleo | B-adjacente | ponte | outro | Total |
|---|---|---|---|---|---|---|---|
| 2021 | 3 | 3 | 0 | 5 | 0 | 37 | 48 |
| 2022 | 0 | 5 | 0 | 2 | 0 | 42 | 49 |
| 2023 | 0 | 3 | 0 | 7 | 0 | 37 | 47 |
| 2024 | 1 | 4 | 0 | 3 | 0 | 34 | 42 |
| 2025 | 3 | 6 | 1 | 8 | 0 | 38 | 56 |
| 2026 | 2 | 14 | 4 | 14 | 1 | 30 | 65 |
| **Total** | **9** | **35** | **5** | **39** | **1** | **218** | **307** |

### Industry Track (à parte)

| Ano | A-nucleo | A-adjacente | B-nucleo | B-adjacente | ponte | outro | Total |
|---|---|---|---|---|---|---|---|
| 2021 | 0 | 0 | 0 | 1 | 0 | 8 | 9 |
| 2022 | 0 | 0 | 0 | 1 | 0 | 5 | 6 |
| 2023 | 0 | 0 | 0 | 1 | 0 | 10 | 11 |
| 2024 | 0 | 1 | 0 | 2 | 0 | 7 | 10 |
| 2025 | 0 | 1 | 1 | 1 | 0 | 22 | 25 |
| 2026 | 0 | 1 | 1 | 5 | 1 | 17 | 25 |
| **Total** | **0** | **3** | **2** | **11** | **1** | **69** | **86** |

---

## 3. Tendência 2021 → 2026 (Research Track)

| Ano | Total | A-nucleo | B-nucleo | ponte | A (núcleo + adj.) | B (núcleo + adj.) |
|---|---|---|---|---|---|---|
| 2021 | 48 | 3 (6,2%) | 0 (0,0%) | 0 (0,0%) | 6 (12,5%) | 5 (10,4%) |
| 2022 | 49 | 0 (0,0%) | 0 (0,0%) | 0 (0,0%) | 5 (10,2%) | 2 (4,1%) |
| 2023 | 47 | 0 (0,0%) | 0 (0,0%) | 0 (0,0%) | 3 (6,4%) | 7 (14,9%) |
| 2024 | 42 | 1 (2,4%) | 0 (0,0%) | 0 (0,0%) | 5 (11,9%) | 3 (7,1%) |
| 2025 | 56 | 3 (5,4%) | 1 (1,8%) | 0 (0,0%) | 9 (16,1%) | 9 (16,1%) |
| 2026 | 65 | 2 (3,1%) | 4 (6,2%) | 1 (1,5%) | 16 (24,6%) | 18 (27,7%) |

**Em blocos de três anos:**

| Período | Artigos | A-nucleo | B-nucleo | ponte | A-adjacente | B-adjacente |
|---|---|---|---|---|---|---|
| 2021–2023 | 144 | 3 (2,1%) | 0 | 0 | 11 (7,6%) | 14 (9,7%) |
| 2024–2026 | 163 | 6 (3,7%) | 5 (3,1%) | 1 (0,6%) | 24 (14,7%) | 25 (15,3%) |

**Leitura:**

- **A-nucleo é estável e pequeno.** São 0 a 3 artigos por ano, em torno de 3% do RT, sem crescimento claro. O que cresce em A é o adjacente: detecção de vulnerabilidade, fuzzing e smart contracts, com 14 em 2026.
- **B-nucleo surge do zero.** Não há nenhum até 2024; são 1 em 2025 e 4 em 2026. B-adjacente existe desde 2021 (DNN clássica) e salta para 14 em 2026. Entre esses 14, 6 aplicam LLM a outra tarefa e 3 tratam de FL.
- **Ponte só aparece em 2026,** via MCP. Nenhum artigo sobre hub de modelos, modelo malicioso ou serialização insegura (pickle) apareceu em 2021–2026.
- **LLM no título** (termos LLM, language model, GPT, generative AI, MCP, prompt): 0 em 2021–2023, 2 em 2024, 6 em 2025 e 8 em 2026.
- **Ressalva:** 2026 foi classificado em grande parte só pelo título. O número de B-adjacente e A-adjacente de 2026 é o menos firme da tabela.

---

## 4. Lista completa: `A-nucleo`, `B-nucleo` e `ponte`

### A-nucleo

| Ano | Trilha | Título | DOI |
|---|---|---|---|
| 2021 | RT | OCTOPOCS: Automatic Verification of Propagated Vulnerable Code Using Reformed Proofs of Concept | 10.1109/dsn48987.2021.00032 |
| 2021 | RT | PDGraph: A Large-Scale Empirical Study on Project Dependency of Security Vulnerabilities | 10.1109/dsn48987.2021.00031 |
| 2021 | RT | PatchDB: A Large-Scale Security Patch Dataset | 10.1109/dsn48987.2021.00030 |
| 2024 | RT | On the Correctness of Metadata-Based SBOM Generation: A Differential Analysis Approach | 10.1109/dsn58291.2024.00018 |
| 2025 | RT | What Lies Beneath: An Empirical Study of Silent Vulnerability Fixes in Open-Source Software | 10.1109/dsn64029.2025.00043 |
| 2025 | RT | An Analysis of Malicious Packages in Open-Source Software in the Wild | 10.1109/dsn64029.2025.00045 |
| 2025 | RT | Automatically Generating Rules of Malicious Software Packages via Large Language Model | 10.1109/dsn64029.2025.00072 |
| 2026 | RT | VCAligner: Aligning Source Distribution Versions with Upstream Git Commits to Secure Supply Chain | 10.1109/dsn69566.2026.00048 |
| 2026 | RT | SPDAgent: Leveraging LLM Agents for Context-Aware Binary Security Patch Detection via Pseudocode Diff Analysis | 10.1109/dsn69566.2026.00058 |

Nenhum `A-nucleo` no Industry Track.

### B-nucleo

| Ano | Trilha | Título | DOI |
|---|---|---|---|
| 2025 | RT | Prompting the Unseen: Detecting Hidden Backdoors in Black-Box Models | 10.1109/dsn64029.2025.00058 |
| 2026 | RT | Beyond Corner Patches: Semantics-Aware Backdoor Attack in Federated Learning | 10.1109/dsn69566.2026.00032 |
| 2026 | RT | Bypassing Safety Alignment via API Design: A Systematic Risk Analysis of Response Prefill in LLM systems | 10.1109/dsn69566.2026.00054 |
| 2026 | RT | LymphNode: A Plug-and-Play Access Control Method for Deep Neural Networks | 10.1109/dsn69566.2026.00062 |
| 2026 | RT | RIPE-II: Retrieval In-Place Poisoning Evaluation with Indirect Injections | 10.1109/dsn69566.2026.00078 |
| 2025 | Ind. | To Protect the LLM Agent Against the Prompt Injection Attack with Polymorphic Prompt | 10.1109/dsn-s65789.2025.00037 |
| 2026 | Ind. | Event Burst Trigger: An Availability Backdoor Attack on Event-Based SNN Object Detection | (a verificar) |

### Ponte

| Ano | Trilha | Título | DOI |
|---|---|---|---|
| 2026 | RT | A First Look at the Security Issues in the Model Context Protocol Ecosystem | 10.1109/dsn69566.2026.00046 |
| 2026 | Ind. | Aegis: Preventing Cross-Domain Resource Abuse in MCP | (a verificar) |

### Casos de fronteira

Eles mudariam a contagem se a regra fosse outra.

- **Para B-nucleo:**
  - Rowhammer no backdoor de DNN (2023, `B-adjacente`): backdoor injetado por bit-flip.
  - AnBridge (2026, `B-adjacente`): protege a IA no dispositivo dentro de uma VM protegida.
  - VerifyVFL (2025, `B-adjacente`): integridade do treino em FL vertical.
  - Ataque adversarial textual com masked LM (2025, `B-adjacente`).
- **Para A-nucleo:**
  - Estudo de gestão de vulnerabilidades com IA (2024, Ind., `A-adjacente`).
  - Experiência de security-by-design com OSS na borda de telecom (2025, Ind., `A-adjacente`).
  - Privilégio delegado para ferramentas de patch automatizado (2026, Ind., `outro`).
- **Entre A e B:**
  - Detectar vulnerabilidades com LLMs (2025) e reentrância na era dos LLMs (2026), ambos `B-adjacente`.
  - RuleLLM (2025) e SPDAgent (2026), ambos `A-nucleo`.

---

## 5. Itens do DSN-S que tocam A ou B (fora da contagem)

Os títulos vêm das listas de aceitos de 2024–2026 (pôsteres, Disrupt e fórum doutoral). O código entre parênteses é indicativo e foi atribuído só pelo título.

- **2024:**
  - Fórum doutoral: "Novel CAN Bus Fuzzing Framework for Finding Vulnerabilities in Automotive Systems" (A-adj.).
  - Disrupt: "PANDA: Practical Adversarial Attacks Against Intrusion Detection Applications" (B-adj.).
  - Pôster: "Balancing Privacy and Attack Utility: … Membership Inference Attacks in Transfer Learning" (B-adj.).
  - Tutorial: "Safe, Secure, and Trustworthy AI via Formal Verification of Neural Networks…".
- **2025:**
  - Pôster: "Jailbreaking Generative AI: Empowering Novices to Conduct Phishing Attacks" (B-núcleo).
  - Pôster: "Security Vulnerability Risk Growth Model based on CVSS 4.0" (A).
  - Fórum doutoral: "SCAMDETECT: … Uncover Threats in Smart Contracts" (A-adj.).
  - Fórum doutoral: "Towards Provenance for Cybersecurity in Cloud-Native Production Infrastructure" (escopo **a verificar**).
- **2026, pôsteres:**
  - "Evaluating Security Best Practices in the GitHub Actions Documentation" (A-núcleo, CI/CD).
  - "Efficient Backdoor Sample Identification via Blend Transform for Untrusted Training Data" (B-núcleo).
  - "Memory-Bandwidth Side Channels for Input Recovery in Edge-Deployed LLM Inference" (B).
  - "Does the Knight and Leveson Hypothesis Hold for LLM-Based Code Generation?".
  - "The Overlooked Role of False Negatives in Reentrancy Detection" (A-adj.).
  - "Co-evolving SQL Injection Attacks and ModSecurity Rules via Agentic AI".
- **2026, Disrupt:**
  - "RO: Reliable Orchestration of LLM Programs via Deterministic-Generative Separation".
  - "Towards Security by Performance: Rethinking Cyber Risk Assessment for Distributed ML Systems".

---

## 6. Workshops do DSN (2024–2027)

Fontes: página `cfworkshops.html` de 2024 e 2025, páginas `workshop_*.html` de 2026 e página Workshops do DSN 2027 (dsn2027-berlin.github.io/workshops/). As páginas `cpaccepted_wkshp.html` de 2024 e 2025 são cópias da de 2022 e foram descartadas.

**Workshops por ano:**

- **2024:** DCCS, DSML, SSIV, VERDI.
- **2025:** WDMD, VERDI, S2AIM, AxC, DT4DRS, FORCE, EnvSys, DSML (8ª edição). O CRGS 2025 aparece só em HTML comentado; se aconteceu é **(a verificar)**.
- **2026:** CRAI, DSAS, DSML (9ª edição), DT4DRS, FORCE, HAP, RASACC.
- **2027:** a chamada de propostas está aberta até 13/jan/2027, com notificação em 27/jan/2027. Nenhum workshop foi escolhido ainda.

**Os que tocam A ou B:**

| Ano | Workshop | Toca | Escopo em uma linha |
|---|---|---|---|
| 2024 | DSML: Dependable and Secure Machine Learning | B | ML confiável e seguro: entradas adversariais, excesso de confiança, falhas em aceleradores. Nos anais: backdoor (dois artigos), DL distribuído robusto a falhas bizantinas, detecção de patch adversarial. |
| 2025 | DSML (8ª): Dependable and Secure Machine Learning | B | Teste e certificação de sistemas com ML, ML adversarial, "safety, robustness, and alignment", segurança de aceleradores. |
| 2025 | VERDI (3ª): V&V of Dependable CPS | B (marginal) | V&V de sistemas ciberfísicos. Um dos tópicos é "Verification and validation of LLM-enhanced systems". |
| 2026 | DSML (9ª): Dependable and Secure Machine Learning | B | Inclui IA generativa e modelos de fundação: segurança, prompt injection, alucinação, ataques de energia e latência. |
| 2026 | CRAI (1ª): Composable Resilience for Agentic AI | B / ponte | Resiliência composicional de agentes: sandboxing, orquestração verificada, interação com ferramentas preservando privacidade, defesas adversariais. |
| 2026 | DSAS: Dependable and Secure Autonomous Systems | A e B (marginais) | Espaço e drones. Tópicos: robustez e verificação de componentes com aprendizado; "Secure software and hardware supply chains for space technologies". |
| 2027 | (chamada) | B (marginal) | A lista de tópicos sugeridos inclui "Dependability of AI, Machine Learning, and Data-driven Systems". |

**Nenhum workshop de 2024 a 2026 tem cadeia de suprimentos de software, SBOM ou gestão de vulnerabilidades como tema central.** O único que cita cadeia de suprimentos é o DSAS 2026, num tópico restrito a tecnologia espacial. A lista de tópicos sugeridos para 2027 também não cita esses temas.

---

## 7. Prêmios de melhor artigo (2023–2026)

**Fonte:** lista de vencedores do IFIP WG 10.4 (dependability.org/?p=370). Ela confere com as sessões "Best Paper" dos programas oficiais. Desde 2023 há até três Best Paper Awards por ano, e o voto da plateia escolhe o Distinguished Paper Award.

**Divergência:** as páginas de prêmios do DSN 2024 e 2025 descrevem um prêmio só, escolhido entre três candidatos. Já a lista do WG 10.4 dá os três como vencedores.

| Ano | Artigo | Código | Distinguished |
|---|---|---|---|
| 2023 | SHATTER: Control and Defense-Aware Attack Analytics for Activity-Driven Smart Home Systems | outro | |
| 2023 | SecDDR: Enabling Low-Cost Secure Memories by Protecting the DDR Interface (na lista do WG 10.4: "Making Replay Attack Protection Practical by Securing the DDR Interface"; título **a verificar**) | outro | |
| 2023 | Devils in Your Apps: Vulnerabilities and User Privacy Exposure in Mobile Notification Systems | outro | sim |
| 2024 | On the Correctness of Metadata-Based SBOM Generation: A Differential Analysis Approach (PER) | **A-nucleo** | **sim** |
| 2024 | ZLB: A Blockchain to Tolerate Colluding Majorities | outro | |
| 2024 | JITBULL: Securing JavaScript Runtime with a Go/No-Go Policy for JIT Engine | outro | |
| 2025 | Privacy Analysis of Oblivious DNS over HTTPS: a Website Fingerprinting Study | outro | |
| 2025 | GnuZero: A Compiler-Based Zeroization Static Detection Tool for the Masses | A-adjacente | sim |
| 2025 | Faster Hash-based Multi-valued Validated Asynchronous Byzantine Agreement | outro | |
| 2026 | PRAXIS: Integrating Program Analysis with Observability for Root-Cause Analysis | outro (LLM para diagnóstico) | |
| 2026 | Thinking Inside the Box: Injecting Realistic Radiation Faults in ML Accelerators | B-adjacente | sim |
| 2026 | Q3Fuzz: Multi-Layered Stateful Fuzzing for the QUIC-HTTP/3 Protocol Stack | A-adjacente | |

**Leitura:** o único prêmio dado a um artigo de núcleo foi o Distinguished de 2024, para o artigo de SBOM (A). Nenhum `B-nucleo` foi premiado. Os prêmios de 2025 e 2026 foram para trabalhos adjacentes: análise estática em 2025; fuzzing e falhas em acelerador de ML em 2026.

---

## 8. Limitações

- **A classificação é aproximada.** Ela usa título e resumo, nunca o texto completo. Um só classificador (este levantamento) atribuiu os códigos, sem segundo avaliador nem medida de concordância.
- **67 de 393 artigos (17%) foram classificados só pelo título,** todos de 2026: 48 do RT e 19 do Industry Track.
  - Os outros 326 tinham resumo, vindo da OpenAlex, dos anais de 2024 (`data.js`), do arXiv ou do PDF local.
  - Uma triagem por palavras-chave passou por todos os resumos. O resumo foi lido só nos candidatos a A ou B; os demais ficaram `outro` pelo título e pela triagem.
- **As fronteiras dependem das regras do §1.2.**
  - Outra regra para "LLM aplicado a A" moveria até 4 artigos entre A e B.
  - Outra regra para "backdoor via bit-flip" e "proteção de modelo em VM" moveria 2 para B-nucleo.
- **Os números são pequenos** (0 a 4 artigos de núcleo por ano). Um artigo a mais ou a menos muda o percentual de um ano em 1,5 a 2,4 pontos.
- **Os totais por ano dependem das listas oficiais.** Em 2023 a lista é a do programa (47 artigos, incluindo PER e TAR). Os demais anos usam a lista de aceitos ou os anais.
- **Ficaram de fora:** workshops (DSN-W), pôsteres, Disrupt e fórum doutoral. Nesses espaços B aparece com mais frequência (§5, §6).
- **A tabela não mede rejeições.** Não sabemos quantas submissões de A ou B o DSN recebeu.
