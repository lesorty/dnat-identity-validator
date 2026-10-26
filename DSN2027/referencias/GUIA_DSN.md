# Guia DSN 2021–2026: artigos relevantes para o DNAT

**Data:** 2026-10-26 · **Alvo:** DSN 2027 (Berlim), Research Track, regular paper.

**Escopo.** Anais do DSN de 2021 a 2026. Foco no **Research Track** (o antigo DCCS/PDS). Do
Industry Track, do volume suplementar (DSN-S) e dos pôsteres entram só os muito relevantes,
marcados como tal. Não entrou nenhum workshop (DSN-W).

**Como foi feito.**
1. CFP do DSN 2027 lido na fonte (§1).
2. Listas de artigos montadas assim:
   - **2021–2025:** OpenAlex (fonte "IEEE/IFIP DSN", 324 registros com front matter);
   - **2023:** programa oficial (dsn2023.dei.uc.pt), que marca o tipo de cada artigo;
   - **2024:** sumário oficial dos anais (dsn2024uq.github.io/Proceedings, 42 artigos no Research Track);
   - **2025 e 2026:** listas oficiais de aceitos (dsn2025.github.io e dsn2026.github.io).
   O dblp não pôde ser usado: a página exige um desafio anti-robô, que não contornamos.
3. Filtro por relevância para os rumos A, B e Juiz.
4. Metadados conferidos assim:
   - **DOI, páginas e resumos:** OpenAlex e Semantic Scholar;
   - **três referências:** reconferidas com `verify_reference` (todas "verified");
   - **versões abertas:** arXiv, páginas dos autores e repositórios institucionais.
   Nada foi baixado do IEEE Xplore nem de sites de pirataria.
5. **PDFs:** cada um foi conferido com `pdfinfo` e pela primeira página.

**Contagem.** 54 artigos listados. 29 PDFs baixados: 28 do próprio artigo e 1 tese de mestrado
que é a versão estendida (Torpedo). 25 estão pendentes, com o status "instituição". Dois desses
têm link aberto conhecido, mas o servidor não respondeu na coleta (ConfBench e lazypoline).

Contribuições e números vêm dos resumos e das primeiras páginas. Só seis artigos foram lidos
além da primeira página (Mutiny, KubeFence, AnBridge, prefill, SBOM e Reentrancy-LLM), e só
para o §2. O que não foi conferido leva **(a verificar)**.

---

## §1 DSN 2027: trilha e tópicos que nos cobrem

**Trilhas** (CFP, dsn2027-berlin.github.io/call-for-contributions): Research Track, Industry Track
e **Disrupt**. Só a Research Track tem descrição detalhada no CFP.

**Tipos de artigo** (limite de páginas sem as referências):

| Tipo | Páginas | Observação |
|---|---|---|
| Regular | 11 | Contribuição de pesquisa nova |
| *Practical experience report* (PER) | 7 | Lições práticas ou análise rigorosa de dados de campo |
| Ferramenta (*tool*) | 7 | Ferramenta de dependabilidade, de preferência pública |
| Versão revisada | 12 (regular) / 8 | Uma página a mais para responder aos revisores |

**Processo de revisão.**
- Revisão duplo-cega com **rejeição precoce** em 26/jan/2027.
- *Rebuttal* de até 750 palavras, sem material novo nem links.
- **Revisão** com no máximo cerca de 30% de conteúdo novo; o aceito ganha um *shepherd* do PC.
- *Desk reject* por anonimização, formato ou páginas.

**Artefatos.** A avaliação de artefatos é separada e single-blind. É preciso declarar na
submissão a intenção e o tipo (código, dados ou ambos). Há o prêmio *Distinguished Artifact*.

**Política de IA.** Uma seção "AI Tool Usage" (1–2 parágrafos, depois dos agradecimentos, fora do
limite) é obrigatória se a IA gerou conteúdo intelectual. Dado simulado por IA precisa ser
rotulado. Ferramentas de IA que afetam resultados precisam de detalhe para reprodução. **Isso
nos atinge diretamente:** o Juiz e a batalha de LLMs são resultados produzidos por IA.

**Tópicos do CFP que nos cobrem:**
- *Hardware:* **TEEs**. É a base do DNAT, com CVMs SEV-SNP e TDX.
- *Software:* **segurança de software** e projeto de software confiável (rumo A e Juiz).
- *Networked systems and clouds:* **cloud**, segurança de rede (isolamento e saída só para o DNAT).
- *Distributed ledgers/Blockchains:* criptomoedas e provas de conhecimento zero (marketplace em
  smart contract, rumo A).
- *AI/ML for resilient systems:* **robustez de AI/ML/LLM**, AI/ML para segurança (rumos B e Juiz).
- *Agentic AI systems:* dependabilidade, verificação, **alinhamento**, **prompt injection**,
  segurança multiagente (rumo B e o atacante LLM da batalha do Juiz).
- *Models and methodologies:* avaliação, verificação, **benchmarking**, dados de campo.

O CFP **não cita cadeia de suprimentos de software** pelo nome. O rumo A tem de se apresentar
como "software security" + "blockchains" + "models and methodologies". Mesmo assim, o DSN aceitou
artigos de cadeia de suprimentos em 2021, 2024, 2025 e 2026 (§4.1).

**Volume aceito, para referência:**

| Ano | Research Track | Fonte |
|---|---|---|
| 2023 | 47 (40 REG, 5 PER, 2 TAR) | Programa oficial |
| 2024 | 42 | Sumário oficial dos anais |
| 2025 | ≈ 55 | Lista oficial, contagem manual |
| 2026 | ≈ 64 | Lista oficial, contagem manual |

Taxa de aceitação de 2022: 49 de 262 (18,7%), segundo slide da reunião do IFIP WG 10.4 citado
por busca **(a verificar)**.

---

## §2 Padrão DSN (o que os artigos lidos fazem)

Base: os 29 PDFs, com a primeira página ou o resumo de todos e uma leitura mais funda de seis
(Mutiny, KubeFence, AnBridge, prefill, SBOM e Reentrancy-LLM).

### Modelo de falhas ou de ameaça
- **Artigos de segurança** trazem um "Threat Model" explícito, curto, numa subseção do desenho.
  Ele diz quem é o atacante, o que controla e o que fica fora de escopo. Encontramos a expressão
  em 13 dos 28 PDFs com texto extraível (o do LymphNode não converte), por exemplo KubeFence, AnBridge, VulStyle, MCP, prefill e Reentrancy-LLM.
- **Artigos de dependabilidade "clássica"** (Mutiny, Intrusion Injection) trazem um **modelo de
  falhas**:
  - Mutiny parte de uma **análise de falhas de campo (FFDA)** de incidentes reais;
  - daí deriva o modelo (bit-flip, corrupção de tipo, perda de mensagem);
  - depois mostra que a injeção **reproduz os padrões de campo**.
- **Intrusion Injection** estende o modelo AVI (*attack–vulnerability–intrusion*) com o
  "estado errôneo" e trata a intrusão como se trata a injeção de erro. É uma ponte explícita
  entre segurança e dependabilidade (resumo e slides; o texto completo **a verificar**).

### Vocabulário de dependabilidade
- **Avižienis/Laprie não é citado** pelo nome em nenhum dos 28 PDFs com texto extraível (grep
  por "Avizienis", "Avižienis" e "Laprie"). Isso vale para esta amostra, puxada para segurança.
- O vocabulário aparece mesmo assim:
  - Mutiny usa *fault/error/failure*, propagação de erro, *resiliency*, *stall* e *outage*;
  - Reentrancy-LLM se apresenta com "a dependability-oriented perspective" sobre detectores;
  - KubeChecker valida com injeção de falhas;
  - AnBridge e SNAS falam em isolamento e disponibilidade.
- **Recomendação para nós:**
  - usar o vocabulário com precisão: falha → erro → defeito; atributos de confidencialidade,
    integridade e disponibilidade; meios de prevenção, tolerância, remoção e previsão;
  - citar Avižienis et al. (2004) uma vez, para enquadrar o Juiz como **remoção/previsão de
    falhas** e o rumo A como **tolerância a intrusões via mercado**.
  Os revisores do DSN reconhecem esse enquadramento, mas ele não é obrigatório.

### Tipo de avaliação
Quatro padrões se repetem:
1. **Estudo empírico em larga escala** sobre dados reais, com contagens grandes:
   - 337 mil projetos (PDGraph);
   - 24.356 pacotes maliciosos;
   - 3.515 vulnerabilidades (silent fixes);
   - 67.057 servidores MCP;
   - 4 milhões de contratos;
   - 2.984 pacotes PyPI (VCAligner).
2. **Injeção de falhas ou intrusões** com campanha grande, como cerca de 9.000 injeções no Mutiny.
3. **Sistema + benchmark** em hardware real: TEEs com SGX, SEV-SNP e TDX; medição de overhead
   com YCSB, TPC-C e FaaS (Treaty, ConfBench, AnBridge).
4. **Benchmark comparativo de detectores**, cada vez mais com LLMs:
   - 12 ferramentas formais, 10 modelos de ML e 9 LLMs (Reentrancy-LLM);
   - 14 modelos de 8 provedores (prefill);
   - 12 LLMs como linha de base (LUMEN).
   O formato em **perguntas de pesquisa (RQ1…RQn)** aparece em vários artigos de 2025–2026.

### Tamanho típico
- Regulares ocupam 11–14 páginas nos anais (com referências).
- PER, ferramenta e Industry ocupam 7–10.
- As avaliações misturam:
  - um conjunto de dados real e grande;
  - um conjunto menor rotulado à mão (por exemplo, 143 exemplos no RSD de Reentrancy-LLM);
  - casos reais com impacto: CVEs obtidos (Tabby: 7 CVEs; Torpedo: zero-days) e integração upstream (Keylime).

### O que parece pesar na aceitação
Inferência nossa a partir da amostra, **não** de critério publicado:
- **Dados reais e escala.** Quase todo artigo de 2025–2026 desta lista tem uma contagem grande
  ou um sistema em produção (SNAS em todas as regiões do Snowflake).
- **Achado contraintuitivo e mensurável** em uma frase do resumo:
  - "15% de falha gera 10,3 milhões de commits para auditar";
  - "um bit-flip derruba o cluster";
  - "prefill passa de 99%".
- **Comparação justa com o estado da arte**, incluindo LLMs como linha de base.
- **Artefato aberto.** Vários artigos citam o repositório no resumo e há prêmio de artefato.
  Reentrancy Redux teve os artefatos "reviewed and reproducible".
- **Enquadramento de dependabilidade** (resiliência, propagação de erro) mesmo em artigo de
  segurança. Os artigos de LLM de 2026 se vendem como "confiabilidade de detectores" ou
  "risco sistêmico de API", não só como ataque.

---

## §3 Tabela-resumo

Relevância: **A** = mercado de bug bounty sobre a cadeia de suprimentos · **B** = guardrails de
LLM aberto · **Juiz** = vazamento pela saída · **base** = infraestrutura do DNAT (TEE/CVM,
isolamento), que vale para todos. Trilha: RT = Research Track; Ind = Industry Track (DSN-S);
Pôst = pôster (DSN-S).

| # | Ano | Título curto | Tema | Trilha | Relevância | PDF |
|---|---|---|---|---|---|---|
| 1 | 2021 | PDGraph | Cadeia de suprimentos | RT | A | instituição |
| 2 | 2024 | SBOM por metadados | Cadeia de suprimentos | RT | A | 2024_yu_sbom.pdf |
| 3 | 2025 | Pacotes maliciosos em OSS | Cadeia de suprimentos | RT | A | 2025_zhou_malicious-packages.pdf |
| 4 | 2025 | RuleLLM (regras de pacotes maliciosos) | Cadeia de suprimentos + LLM | RT | A | 2025_zhang_malicious-package-rules.pdf |
| 5 | 2026 | VCAligner | Cadeia de suprimentos | RT | A | instituição |
| 6 | 2026 | Boas práticas GitHub Actions | Cadeia de suprimentos (CI/CD) | Pôst | A | instituição |
| 7 | 2026 | Ecossistema MCP | Cadeia de suprimentos de ferramentas LLM | RT | A, B | 2026_li_mcp.pdf |
| 8 | 2021 | PatchDB | Patches de segurança | RT | A | instituição |
| 9 | 2021 | OCTOPOCS | Verificação de vulnerabilidade propagada | RT | A | 2021_kwon_octopocs.pdf |
| 10 | 2025 | Silent fixes | Divulgação de vulnerabilidades | RT | A | instituição |
| 11 | 2026 | SPDAgent | Patches em binário + agentes LLM | RT | A | instituição |
| 12 | 2023 | Tabby | Cadeias de gadgets (exploit) | RT (REG) | A | instituição |
| 13 | 2021 | Asteria | Similaridade de binários | RT | A | 2021_yang_asteria.pdf |
| 14 | 2023 | Intrusion Injection | Avaliação de segurança de hipervisor | RT (REG) | A, base | instituição |
| 15 | 2022 | SEVulDet | Detecção de vulnerabilidade com DL | RT | A | instituição |
| 16 | 2025 | Detectar vulnerabilidades com LLMs | Detecção com LLM | RT | A, Juiz | instituição |
| 17 | 2026 | VulLens | Detector robusto a evasão | RT | A, Juiz | instituição |
| 18 | 2026 | VulStyle | Detecção com estilometria | RT | A | 2026_biringa_vulstyle.pdf |
| 19 | 2026 | LUMEN | LLM ativa comportamento oculto | RT | Juiz | instituição |
| 20 | 2026 | Knight & Leveson para LLMs | Diversidade de geradores LLM | Pôst | Juiz | instituição |
| 21 | 2025 | Reentrancy Redux | Exploits reais em smart contracts | RT | A | 2025_liu_reentrancy-redux.pdf |
| 22 | 2026 | Reentrância na era dos LLMs | Detectores × LLMs | RT | A, Juiz | 2026_ressi_reentrancy-llm.pdf |
| 23 | 2026 | Multi-token / batch transfer | Auditoria de contratos em escala | RT | A | instituição |
| 24 | 2026 | Sol2Vy (zero-shot Vyper) | Detecção em contratos | RT | A | 2026_hu_zero-shot-smart-contracts.pdf |
| 25 | 2025 | PhishingHook | Contratos maliciosos por opcode | RT | A | 2025_derosa_phishinghook.pdf |
| 26 | 2024 | Iniva | Incentivo compatível em consenso | RT | A | 2024_baloochestani_iniva.pdf |
| 27 | 2021 | Deflection (verificação in-enclave) | TEE + verificação de código | RT | Juiz, base | 2021_liu_in-enclave-verification.pdf |
| 28 | 2021 | EncDBDB | Banco cifrado em enclave | RT | base | 2021_fuhry_encdbdb.pdf |
| 29 | 2021 | Plinius | Treino de ML em SGX | RT | B, base | 2021_yuhala_plinius.pdf |
| 30 | 2022 | Treaty | Transações seguras com TEE | RT | base | instituição |
| 31 | 2023 | SGX Switchless configless | Desempenho de SGX | RT (PER) | base | 2023_yuhala_switchless.pdf |
| 32 | 2024 | CVM × contadores de desempenho | Canal lateral em CVM | RT | base, Juiz | instituição |
| 33 | 2025 | ConfBench | Avaliação de CVMs (TDX/SEV-SNP) | RT | base | instituição |
| 34 | 2025 | Keylime | Atestação contínua | RT | base | instituição |
| 35 | 2025 | Triad (tempo confiável em TEE) | TEE | Ind | base | 2025_bettinger_triad-tee-time.pdf |
| 36 | 2026 | AnBridge | IA em VM protegida (Android) | RT | B, base | 2026_farina_anbridge.pdf |
| 37 | 2022 | Torpedo | Fuzzing de containers | RT | base | 2022_mcdonough_torpedo-tese.pdf (tese) |
| 38 | 2023 | Rewind & Discard | Compartimentalização | RT (REG) | base | 2023_gulmez_rewind-discard.pdf |
| 39 | 2024 | lazypoline (interposição de syscalls) | Sandbox e monitoração | RT | base, Juiz | instituição |
| 40 | 2024 | Mutiny (falhas do Kubernetes) | Injeção de falhas em orquestrador | RT | base | 2024_barletta_kubernetes.pdf |
| 41 | 2025 | KubeFence | Superfície de ataque do K8s | RT | base | 2025_cesarano_kubefence.pdf |
| 42 | 2025 | KubeChecker | Configuração de orquestração | Ind | base | instituição |
| 43 | 2026 | SNAS | Saída de rede de sandboxes | Ind | base, Juiz | 2026_sharma_snas.pdf |
| 44 | 2026 | Prefill burla o alinhamento | Jailbreak via API | RT | B | 2026_li_prefill-jailbreak.pdf |
| 45 | 2025 | Prompt polimórfico | Defesa contra prompt injection | Ind | B, Juiz | 2025_wang_polymorphic-prompt.pdf |
| 46 | 2026 | RIPE-II | Injeção indireta em RAG | RT | B, Juiz | instituição |
| 47 | 2026 | Aegis (MCP) | Política para ferramentas LLM | Ind | B | 2026_priya_aegis.pdf |
| 48 | 2025 | BProm | Backdoor em modelo caixa-preta | RT | B | 2025_huang_backdoor-prompting.pdf |
| 49 | 2023 | Rowhammer no backdoor de DNN | Backdoor por falha de hardware | RT (REG) | B | 2023_tol_rowhammer-backdoor.pdf |
| 50 | 2026 | LymphNode | Controle de acesso a DNN | RT | B | 2026_pei_lymphnode.pdf |
| 51 | 2024 | Vazamento por logits | Vazamento pela saída do modelo | RT | Juiz | instituição |
| 52 | 2024 | Owl | Detecção diferencial de vazamento | RT | Juiz | instituição |
| 53 | 2023 | YODA | Exfiltração por DNS | RT (PER) | Juiz, base | instituição |
| 54 | 2022 | DisTA | Rastreamento de taint distribuído | RT | Juiz | instituição |

---

## §4 Glossário por tema

Formato de cada bloco:
- **Ref.** — referência, com DOI e link aberto;
- **Trilha** — trilha e tipo;
- **Contribuição**;
- **Avaliação**;
- **Para nós** — relevância e como citar;
- **PDF** — arquivo baixado ou "instituição".

As páginas são as dos anais (OpenAlex). O tipo (regular, PER, ferramenta) só foi conferido em
2023, pelo programa oficial. Nos outros anos, artigo de 7 a 10 páginas pode ser PER ou
ferramenta **(a verificar)**.

### 4.1 Cadeia de suprimentos de software

**[1] PDGraph** (2021)
- **Ref.** Li, Q.; Song, J.; Tan, D.; Wang, H.; Liu, J. "PDGraph: A Large-Scale Empirical Study on
  Project Dependency of Security Vulnerabilities". DSN 2021, pp. 161–173.
  DOI 10.1109/DSN48987.2021.00031. Sem versão aberta encontrada.
- **Trilha:** RT.
- **Contribuição:** grafo de dependências com 337.415 projetos e 1,38 milhão de arestas. 42.441
  projetos ainda dependem de versões vulneráveis já divulgadas.
- **Avaliação:** estudo empírico em larga escala, mais acompanhamento de correções ao longo de
  meses.
- **Para nós (A):** base empírica de que um componente vulnerável contamina milhares de
  dependentes. Citar para motivar "marcar como comprometidas todas as apps com o componente no
  SBOM".
- **PDF:** instituição.

**[2] Correção de SBOM gerado por metadados** (2024)
- **Ref.** Yu, S.; Song, W.; Hu, X.; Yin, H. "On the Correctness of Metadata-Based SBOM Generation:
  A Differential Analysis Approach". DSN 2024, pp. 29–36.
  DOI 10.1109/DSN58291.2024.00018 (verificado). Aberto em cs.ucr.edu/~heng/pubs/sbom-dsn24.pdf.
- **Trilha:** RT, 8 pp. (curto; tipo **a verificar**).
- **Contribuição:** análise diferencial de quatro geradores de SBOM. Todos omitem dependências e
  divergem entre si. O artigo propõe o ataque de **confusão de parser**, que esconde pacotes
  maliciosos do SBOM.
- **Avaliação:** comparação diferencial em larga escala mais um benchmark.
- **Para nós (A):** ameaça direta ao rumo A. Se o SBOM omite o componente, a app vulnerável não é
  marcada. Citar para justificar SBOM gerado **dentro do build atestado** (D4), e não por
  metadados declarados.
- **PDF:** `2024_yu_sbom.pdf`.

**[3] Pacotes maliciosos em OSS** (2025)
- **Ref.** Zhou, X.; Zhang, Y.; Niu, W.; Liu, J.; Wang, H.; Li, Q. "An Analysis of Malicious Packages
  in Open-Source Software in the Wild". DSN 2025, pp. 371–385.
  DOI 10.1109/DSN64029.2025.00045. arXiv 2404.04991.
- **Trilha:** RT.
- **Contribuição:** o maior dataset do tipo (24.356 pacotes maliciosos), organizado num grafo de
  conhecimento. Achados: muito reuso de código e pouca diversidade. Pacotes escondidos via
  dependência vivem menos. Os relatórios de segurança são a única fonte confiável de contexto.
- **Avaliação:** estudo empírico com RQs.
- **Para nós (A):** dimensiona o problema e mostra que a divulgação é fragmentada. Citar para
  motivar um canal único de prova de exploit com recompensa.
- **PDF:** `2025_zhou_malicious-packages.pdf`.

**[4] RuleLLM** (2025)
- **Ref.** Zhang, X.; Du, X.; Chen, H.; He, Y.; Niu, W.; Li, Q. "Automatically Generating Rules of
  Malicious Software Packages via Large Language Model". DSN 2025, pp. 734–747.
  DOI 10.1109/DSN64029.2025.00072. arXiv 2504.17198. A lista de autores difere entre a OpenAlex
  e o arXiv no último nome **(a verificar)**.
- **Trilha:** RT.
- **Contribuição:** LLM gera regras YARA e Semgrep a partir de 1.633 pacotes maliciosos. Foram 763
  regras, com precisão de 85,2% e revocação de 91,8%.
- **Avaliação:** protótipo comparado com o estado da arte, mais uma taxonomia de regras.
- **Para nós (A, Juiz):** exemplo de LLM produzindo verificadores mecânicos. Citar como
  precedente de "LLM propõe, ferramenta determinística verifica".
- **PDF:** `2025_zhang_malicious-package-rules.pdf`.

**[5] VCAligner** (2026)
- **Ref.** Li, Y.; Jiang, N.; Zhou, Q.; Xu, S.; Xie, Y.; Jia, X. "VCAligner: Aligning Source
  Distribution Versions with Upstream Git Commits to Secure Supply Chain". DSN 2026, pp. 407–419.
  DOI 10.1109/DSN69566.2026.00048. Sem versão aberta encontrada.
- **Trilha:** RT.
- **Contribuição:** liga cada distribuição publicada ao commit de origem por índice invertido de
  conteúdo, sem depender de tags. Motivação: o caso XZ Utils, a "Provenance Gap".
- **Avaliação:** 2.984 pacotes PyPI. Heurísticas por tag falham em 15% dos casos, o que daria 10,3
  milhões de commits para auditar. O VCAligner reduz isso cerca de 158×.
- **Para nós (A):** proveniência fonte→artefato é pré-requisito para atribuir o exploit ao
  componente certo. Citar junto com o build atestado.
- **PDF:** instituição.

**[6] Boas práticas na documentação do GitHub Actions** (2026, **pôster**)
- **Ref.** Boschanski, L.; Vieira, M. "Evaluating Security Best Practices in the GitHub Actions
  Documentation". DSN-S 2026, pp. 283–284. DOI 10.1109/DSN-S70715.2026.00079.
- **Trilha:** pôster (2 pp.).
- **Contribuição:** um LLM com *few-shot* extrai 459 recomendações de segurança da documentação.
  Elas são mapeadas ao OWASP Top 10 CI/CD.
- **Avaliação:** análise documental.
- **Para nós (A, marginal):** CI/CD como vetor da cadeia de suprimentos. Citar só de passagem.
- **PDF:** instituição.

**[7] Problemas de segurança no ecossistema MCP** (2026)
- **Ref.** Li, X.; Gao, X. "A First Look at the Security Issues in the Model Context Protocol
  Ecosystem". DSN 2026, pp. 379–392. DOI 10.1109/DSN69566.2026.00046. arXiv 2510.16558. O PDF
  avisa que o preprint saiu antes com outro título.
- **Trilha:** RT.
- **Contribuição:** estudo de 67.057 servidores em seis registries. Registries com verificação
  fraca permitem sequestrar servidores, e metadados de ferramenta manipulam o LLM. A ferramenta
  MCPInspect achou 833 servidores vulneráveis.
- **Avaliação:** medição em larga escala mais uma ferramenta.
- **Para nós (A, B):** é a mesma lógica de cadeia de suprimentos (registry → host), agora
  aplicada a ferramentas de LLM. Citar como exemplo de que registry aberto sem verificação é a
  superfície de ataque (nosso proxy de registro aceita qualquer registry, D4).
- **PDF:** `2026_li_mcp.pdf`.

### 4.2 Vulnerabilidades: patches, divulgação e verificação de exploits

**[8] PatchDB** (2021)
- **Ref.** Wang, X.; Wang, S.; Feng, P.; Sun, K.; Jajodia, S. "PatchDB: A Large-Scale Security
  Patch Dataset". DSN 2021, pp. 149–160. DOI 10.1109/DSN48987.2021.00030. Sem PDF aberto. O
  dataset está no Hugging Face (`sunlab/patch_db`, com acesso controlado).
- **Trilha:** RT.
- **Contribuição:** dataset de patches de segurança em três partes: NVD, coletados no GitHub e
  sintéticos.
- **Avaliação:** melhora na identificação de patches de segurança.
- **Para nós (A):** fonte de dados para o lado "componente → correção" do mercado. Citar como
  dataset.
- **PDF:** instituição.

**[9] OCTOPOCS** (2021)
- **Ref.** Kwon, S.; Woo, S.; Seong, G.; Lee, H. "OCTOPOCS: Automatic Verification of Propagated
  Vulnerable Code Using Reformed Proofs of Concept". DSN 2021, pp. 174–185.
  DOI 10.1109/DSN48987.2021.00032. Aberto em ssp.korea.ac.kr/assets/papers/DSN21.pdf.
- **Trilha:** RT.
- **Contribuição:**
  - parte da PoC original da vulnerabilidade;
  - extrai, por taint, as primitivas de crash do código compartilhado;
  - gera com execução simbólica dirigida as entradas que levam o software derivado até ele;
  - remonta uma **nova PoC que verifica a vulnerabilidade no dependente**.
- **Avaliação:** 15 pares reais em C/C++, com 14 vulnerabilidades propagadas verificadas.
- **Para nós (A, central):** é o mais próximo de "verificar mecanicamente o exploit e propagá-lo
  aos dependentes". Citar como trabalho relacionado direto. O nosso difere em marcar pela
  presença no SBOM e em verificar dentro da CVM, sem expor os dependentes ao atacante.
- **PDF:** `2021_kwon_octopocs.pdf`.

**[10] Silent fixes em OSS** (2025)
- **Ref.** Dong, J.; Chen, X.; Susilo, W.; Sun, N.; Shaghaghi, A.; Ma, S. "What Lies Beneath: An
  Empirical Study of Silent Vulnerability Fixes in Open-Source Software". DSN 2025, pp. 345–357.
  DOI 10.1109/DSN64029.2025.00043. Sem versão aberta encontrada.
- **Trilha:** RT.
- **Contribuição:** 3.515 vulnerabilidades analisadas. Quase 50% ficaram mais de 30 dias expostas
  depois da correção silenciosa, e mais de 10% tiveram exploit público nesse período.
- **Avaliação:** estudo empírico.
- **Para nós (A):** mostra o custo da divulgação lenta e opaca. Citar para motivar divulgação com
  prova verificada e marcação imediata dos dependentes.
- **PDF:** instituição.

**[11] SPDAgent** (2026)
- **Ref.** Yang, F.; Gao, Z.; Xiao, X.; Ying, L.; Yin, B.; Zhang, C.; Li, Q. "SPDAgent: Leveraging LLM
  Agents for Context-Aware Binary Security Patch Detection via Pseudocode Diff Analysis".
  DSN 2026, pp. 536–549. DOI 10.1109/DSN69566.2026.00058. Sem versão aberta encontrada.
- **Trilha:** RT.
- **Contribuição:** diff de pseudocódigo (IMP-Diff) mais agentes LLM para detectar patches de
  segurança em binários. Cria o dataset SPD-BIN, com 6.250 pares.
- **Avaliação:** acurácia de 73,44% e F1 de 0,75.
- **Para nós (A):** detectar correções silenciosas em componentes binários de imagens-base.
  Citar como trabalho relacionado do lado defensivo.
- **PDF:** instituição.

**[12] Tabby** (2023)
- **Ref.** Chen, X.; Wang, B.; Jin, Z.; Feng, Y.; Li, X.; Feng, X.; Liu, Q. "Tabby: Automated Gadget
  Chain Detection for Java Deserialization Vulnerabilities". DSN 2023, pp. 179–192.
  DOI 10.1109/DSN58367.2023.00028. Sem versão aberta; a ferramenta está em github.com/tabby-sec/tabby.
- **Trilha:** RT, REG.
- **Contribuição:** busca de cadeias de gadgets em Java com Soot e Neo4j. Em 248 JARs achou 80
  cadeias práticas e rendeu 7 CVEs (XStream, Dubbo).
- **Avaliação:** análise de JARs reais, com divulgação a fornecedores.
- **Para nós (A):** exemplo de exploit em dependência que afeta todos os usuários. Citar como
  classe de vulnerabilidade herdada.
- **PDF:** instituição.

**[13] Asteria** (2021)
- **Ref.** Yang, S.; Cheng, L.; Zeng, Y.; Lang, Z.; Zhu, H.; Shi, Z. "Asteria: Deep Learning-based
  AST-Encoding for Cross-platform Binary Code Similarity Detection". DSN 2021, pp. 224–236.
  DOI 10.1109/DSN48987.2021.00036. arXiv 2108.06082.
- **Trilha:** RT.
- **Contribuição:** Tree-LSTM sobre a AST para achar funções semelhantes em binários de
  arquiteturas diferentes, com uso em busca de vulnerabilidades.
- **Avaliação:** cerca de 1 milhão de pares de funções no treino, mais busca de vulnerabilidades
  em firmware **(a verificar o detalhe)**.
- **Para nós (A, marginal):** identificar o componente vulnerável quando não há SBOM confiável.
  Citar como alternativa ao SBOM.
- **PDF:** `2021_yang_asteria.pdf`.

**[14] Intrusion Injection** (2023)
- **Ref.** Gonçalves, C. F.; Antunes, N.; Vieira, M. "Intrusion Injection for Virtualized Systems:
  Concepts and Approach". DSN 2023, pp. 417–430. DOI 10.1109/DSN58367.2023.00047. Só os slides
  são abertos (eden.dei.uc.pt/~charles/intrusion_injection/).
- **Trilha:** RT, REG.
- **Contribuição:** injetar diretamente os **estados errôneos** que uma intrusão causaria no Xen,
  como se injeta erro para simular falha residual.
- **Avaliação:** protótipo testado com exploits públicos em três versões do Xen.
- **Para nós (A, base):** traz a ponte segurança↔dependabilidade que o DSN valoriza. Citar para
  enquadrar a "verificação mecânica do exploit" como efeito observável, e não como a
  vulnerabilidade em si.
- **PDF:** instituição.

### 4.3 Detecção de vulnerabilidades e análise com ML/LLM

**[15] SEVulDet** (2022)
- **Ref.** Tang, Z.; Hu, Q.; Hu, Y.; Kuang, W.; Chen, J. "SEVulDet: A Semantics-Enhanced Learnable
  Vulnerability Detector". DSN 2022, pp. 150–162. DOI 10.1109/DSN53405.2022.00026. Sem versão
  aberta.
- **Trilha:** RT.
- **Contribuição:** fatiamento sensível a caminho mais CNN com *spatial pyramid pooling*.
- **Avaliação:** comparação com detectores estáticos e de DL.
- **Para nós (A, marginal):** linha de base pré-LLM. Citar só se precisar de histórico.
- **PDF:** instituição.

**[16] Detectar vulnerabilidades com LLMs** (2025)
- **Ref.** Huynh, L. K.; Zhang, Y.; Jayasundera, D.; Jeon, W.; Kim, H.; Bi, T.; Hong, J. B.
  "Detecting Code Vulnerabilities using LLMs". DSN 2025, pp. 401–414.
  DOI 10.1109/DSN64029.2025.00047. Sem PDF aberto oficial; código no Zenodo, registro 15108502.
- **Trilha:** RT.
- **Contribuição:** estratégias de prompt para detectar vulnerabilidades no DiverseVul. O prompt
  dinâmico melhora o F1 em até 100% no GPT-3.5. **Identificar o tipo** da vulnerabilidade
  continua ruim (melhor F1 = 0,16). Corrigir funciona em 45,77% dos casos com o GPT-4o.
- **Avaliação:** benchmark com vários LLMs.
- **Para nós (Juiz, A):** prova que o LLM sozinho é fraco para dizer "o quê" e "onde". Citar para
  justificar o Juiz com evidência dinâmica e o rumo A com verificação mecânica, e não com
  julgamento de LLM.
- **PDF:** instituição.

**[17] VulLens** (2026)
- **Ref.** Sun, S.; Sharma, P.; Maitra, S.; Stavrou, A.; Wang, H. "VulLens: Enhancing Software
  Vulnerability Detection against Evasion Attacks". DSN 2026, pp. 109–121.
  DOI 10.1109/DSN69566.2026.00025. Sem versão aberta.
- **Trilha:** RT.
- **Contribuição:**
  - defesa contra evasão (renomear identificadores, inserir código morto) em detectores com
    modelos de código;
  - limpeza de código morto;
  - mascaramento dos identificadores de maior atenção;
  - a variação de confiança indica amostra adversarial.
- **Avaliação:** **a verificar**; o resumo foi cortado.
- **Para nós (Juiz):** o atacante adaptativo engana detectores com transformações que preservam
  a semântica. Citar na ameaça ao Juiz: o atacante tem o Juiz por construção.
- **PDF:** instituição.

**[18] VulStyle** (2026)
- **Ref.** Biringa, C.; Abbas, A.; Selvaraj, V.; Kul, G. "VulStyle: A Multi-Modal Pre-Training for
  Code Stylometry-Augmented Vulnerability Detection". DSN 2026 (a primeira página do arXiv cita
  o DSN 2026); DOI **a verificar**. arXiv 2604.26313.
- **Trilha:** RT.
- **Contribuição:** pré-treino em 4,9 milhões de funções com AST não-terminal e estilometria.
- **Avaliação:** cinco benchmarks (Devign, BigVul, DiverseVul, REVEAL, VulDeePecker), com F1 4–48%
  acima das linhas de base em BigVul e VulDeePecker.
- **Para nós (A, marginal):** estado da arte em detecção estática. Citar como contraste: detectar
  não é provar exploit.
- **PDF:** `2026_biringa_vulstyle.pdf`.

**[19] LUMEN** (2026)
- **Ref.** Valakuzhy, K.; Wong, M. Y.; Blough, D. M.; Ahamad, M.; Monrose, F. "LUMEN: A Systems
  Approach to LLM-Guided Activation of Hidden Behaviors in Malware". DSN 2026, pp. 122–135.
  DOI 10.1109/DSN69566.2026.00026. Sem versão aberta. Há também um pôster complementar no DSN 2026
  ("LUMENating…").
- **Trilha:** RT.
- **Contribuição:** o LLM aponta os pontos de decisão que escondem comportamento, e o sistema
  constrói a ativação. A **análise dinâmica (sandbox CAPE) passa a ver o que estava oculto**.
- **Avaliação:**
  - 22 famílias em que o CAPE falhava;
  - revela atividade grave em 68% das amostras;
  - 4× mais comportamento que o JuanLesPIN;
  - supera prompt direto de 12 LLMs em 64% dos casos.
- **Para nós (Juiz, central):** é exatamente "LLM + teste dinâmico" para revelar comportamento
  que o programa esconde da análise. Citar como o precedente mais próximo do Juiz no DSN.
- **PDF:** instituição.

**[20] A hipótese de Knight e Leveson vale para geração de código por LLM?** (2026, **pôster**)
- **Ref.** Nogueira, R. P.; Pattabiraman, K.; Vieira, M.; Campos, J. R. "Does the Knight and Leveson
  Hypothesis Hold for LLM-Based Code Generation?". Pôster, DSN 2026. DOI **a verificar**.
- **Trilha:** pôster.
- **Contribuição:** **a verificar**; só conferimos o título e os autores na lista oficial. Testa se
  as falhas de versões geradas por LLMs diferentes são independentes.
- **Avaliação:** **a verificar**.
- **Para nós (Juiz):** a batalha usa vários defensores LLM. Se as falhas são correlacionadas, a
  votação entre LLMs vale menos. Citar como alerta sobre diversidade de juízes.
- **PDF:** instituição.

### 4.4 Smart contracts, blockchain e incentivos

**[21] Reentrancy Redux** (2025)
- **Ref.** Liu, Y.; Xi, R.; Pattabiraman, K. "Reentrancy Redux: The Evolution of Real-World
  Reentrancy Attacks on Blockchains". DSN 2025, pp. 576–588. DOI 10.1109/DSN64029.2025.00060.
  PDF dos autores via blogs.ubc.ca/dependablesystemslab/?p=6100.
- **Trilha:** RT. Artefatos "reviewed and reproducible", segundo a página do laboratório.
- **Contribuição:** 73 ataques reais de reentrância (2016–2024) em cadeias EVM. Os ataques são
  mais diversos e atravessam contratos, projetos e cadeias. Os atacantes se adaptam para escapar
  das defesas.
- **Avaliação:** análise qualitativa e quantitativa, mais a ferramenta ReSect (Tool no DSN 2026).
- **Para nós (A):**
  - o próprio marketplace em smart contract é alvo;
  - o artigo também é exemplo de estudo de exploits reais no estilo DSN.
  Citar no modelo de ameaça do contrato do mercado.
- **PDF:** `2025_liu_reentrancy-redux.pdf`.

**[22] Detecção de reentrância na era dos LLMs** (2026)
- **Ref.** Ressi, D.; Spanò, A.; Rizzo, M.; Benetollo, L.; Rossi, S. "Reentrancy Detection in the
  Age of LLMs". DSN 2026, pp. 432–447. DOI 10.1109/DSN69566.2026.00050. arXiv 2603.26497.
- **Trilha:** RT.
- **Contribuição:** avaliação de **dependabilidade** de detectores em Solidity 0.8+. Dois
  benchmarks verificados à mão: 432 contratos reais e 143 cenários mínimos (RSD). Compara 12
  ferramentas formais, 10 modelos de ML e 9 LLMs. Os melhores LLMs chegam a F1 0,96 (agregado) e
  0,82 (RSD).
- **Avaliação:** benchmark comparativo com RQs.
- **Para nós (Juiz, A):** é o modelo de avaliação mais parecido com o que o Juiz precisa:
  - benchmark rotulado à mão;
  - cenários mínimos que isolam cada padrão;
  - LLM × ferramentas clássicas;
  - enquadramento de dependabilidade.
  Citar no desenho da avaliação.
- **PDF:** `2026_ressi_reentrancy-llm.pdf`.

**[23] Batch transfers em contratos multi-token** (2026)
- **Ref.** Kasthuri, A.; Meisami, S.; Jiang, L.; Wang, B.; Duan, Y. "Large-Scale Security Analysis of
  Multi-Token Smart Contracts: Uncovering Hidden Flaws in Batch Transfers". DSN 2026, pp. 220–233.
  DOI 10.1109/DSN69566.2026.00034. Sem versão aberta.
- **Trilha:** RT.
- **Contribuição:** regras derivadas dos padrões ERC. O BatchAudit analisa 4 milhões de contratos
  e acha 915 implementações com erro (precisão amostral de 0,804). Exploits demonstrados em
  testnet.
- **Avaliação:** análise estática em escala, transações on-chain e exploit controlado.
- **Para nós (A):** padrão "achado estático + **exploit demonstrado**" como prova. Citar para
  sustentar que a recompensa exige demonstração.
- **PDF:** instituição.

**[24] Sol2Vy: detecção zero-shot em Vyper** (2026)
- **Ref.** Hu, M.; Zeng, Q.; Luo, L. "Zero-Shot Vulnerability Detection in Low-Resource Smart
  Contracts Through Solidity-Only Training". DSN 2026, pp. 704–717.
  DOI 10.1109/DSN69566.2026.00071. arXiv 2603.21058.
- **Trilha:** RT.
- **Contribuição:** transferência entre linguagens (Solidity→Vyper) para detectar reentrância,
  aleatoriedade fraca e transferência não checada.
- **Avaliação:** comparação com o estado da arte em Vyper.
- **Para nós (A, marginal):** auditoria do contrato do mercado, se for escrito em Vyper.
- **PDF:** `2026_hu_zero-shot-smart-contracts.pdf`.

**[25] PhishingHook** (2025)
- **Ref.** De Rosa, P.; Queyrut, S.; Bromberg, Y.-D.; Felber, P.; Schiavoni, V. "PhishingHook:
  Catching Phishing Ethereum Smart Contracts leveraging EVM Opcodes". DSN 2025, pp. 222–232.
  DOI 10.1109/DSN64029.2025.00033. arXiv 2506.19480.
- **Trilha:** RT.
- **Contribuição:** detecção de contratos de phishing pelo bytecode, antes da interação, com 16
  técnicas de ML comparadas. Evita reexecutar transações, o que exporia dados de usuários.
- **Avaliação:** benchmark de classificadores.
- **Para nós (A, marginal):** contratos maliciosos de terceiros que interagem com o mercado.
- **PDF:** `2025_derosa_phishinghook.pdf`.

**[26] Iniva** (2024)
- **Ref.** Baloochestani, A.; Gogada, H.; Jehl, L.; Meling, H. "Iniva: Inclusive and
  Incentive-Compatible Vote Aggregation". DSN 2024, pp. 443–455.
  DOI 10.1109/DSN58291.2024.00050. arXiv 2404.04948.
- **Trilha:** RT.
- **Contribuição:** agregação de votos que impede o proponente de omitir votos alheios. Omitir
  muitos votos passa a custar caro.
- **Avaliação:** análise mais experimentos de escala.
- **Para nós (A, marginal):** mostra que o DSN aceita **compatibilidade de incentivos** como
  propriedade de dependabilidade. Citar no desenho das recompensas, por exemplo contra o
  operador que omite a prova de um caçador.
- **PDF:** `2024_baloochestani_iniva.pdf`.

### 4.5 TEEs e computação confidencial (base do DNAT)

**[27] Deflection: verificação de conformidade de privacidade dentro do enclave** (2021)
- **Ref.** Liu, W.; Wang, W.; Chen, H.; Wang, X.; Lu, Y.; Chen, K.; Wang, X.; Shen, Q.; Chen, Y.;
  Tang, H. "Practical and Efficient in-Enclave Verification of Privacy Compliance". DSN 2021,
  pp. 413–425. DOI 10.1109/DSN48987.2021.00052.
- **Versões abertas:** hc50.pages.iu.edu; PMC 9343090; o preprint é o arXiv 2007.10513, com o
  título "Confidential Attestation…".
- **Trilha:** RT.
- **Contribuição:** o dono dos dados não vê o código, mas um **verificador pequeno e público dentro
  do enclave** checa se o código cumpre a política de privacidade. O desenho segue a ideia de
  *proof-carrying code*: o gerador faz o trabalho pesado e o verificador é simples.
- **Avaliação:** implementação em SGX com medição de overhead.
- **Para nós (Juiz, central):** é o precedente direto de "uma aplicação confiável dentro do TEE
  verifica outra aplicação antes de ela tocar os dados". Citar no trabalho relacionado do Juiz.
  Diferença: o Deflection verifica estaticamente uma política fixa; o Juiz julga o vazamento pela
  saída com testes dinâmicos e LLM.
- **PDF:** `2021_liu_in-enclave-verification.pdf`.

**[28] EncDBDB** (2021)
- **Ref.** Fuhry, B.; Jain H A, J.; Kerschbaum, F. "EncDBDB: Searchable Encrypted, Fast, Compressed,
  In-Memory Database Using Enclaves". DSN 2021, pp. 438–450. DOI 10.1109/DSN48987.2021.00054.
  arXiv 2002.05097 (preprint de 2020).
- **Trilha:** RT.
- **Contribuição:** banco colunar cifrado com busca por faixa num enclave pequeno. São nove
  dicionários com compromissos diferentes de vazamento.
- **Avaliação:** microbenchmarks com milhões de registros.
- **Para nós (base, Juiz):** explicita **o vazamento admitido** como parte do desenho. Citar ao
  declarar o que o DNAT aceita vazar.
- **PDF:** `2021_fuhry_encdbdb.pdf`.

**[29] Plinius** (2021)
- **Ref.** Yuhala, P.; Felber, P.; Schiavoni, V.; Tchana, A. "Plinius: Secure and Persistent Machine
  Learning Model Training". DSN 2021, pp. 52–62. DOI 10.1109/DSN48987.2021.00022.
  arXiv 2104.02987.
- **Trilha:** RT.
- **Contribuição:** treino de ML em SGX com espelhamento cifrado em memória persistente.
- **Avaliação:** salvar e restaurar o modelo fica 3,2× e 3,7× mais rápido que checkpoint em disco.
- **Para nós (B, base):** precedente de **treino confidencial** dentro de TEE. Citar no rumo B.
- **PDF:** `2021_yuhala_plinius.pdf`.

**[30] Treaty** (2022)
- **Ref.** Giantsidi, D.; Bailleu, M.; Crooks, N.; Bhatotia, P. "Treaty: Secure Distributed
  Transactions". DSN 2022, pp. 14–27. DOI 10.1109/DSN53405.2022.00015. Só os slides são abertos
  (dse.in.tum.de); código em github.com/TUM-DSE/Treaty.
- **Trilha:** RT.
- **Contribuição:** KV transacional distribuído com TEEs. Garante confidencialidade, integridade e
  **frescor**, com 2PC seguro e persistência consistente após crash.
- **Avaliação:** YCSB e TPC-C em hardware real.
- **Para nós (base):** modelo de ameaça "nuvem não confiável + TEE". Citar ao definir o operador
  como não confiável.
- **PDF:** instituição.

**[31] SGX Switchless sem configuração** (2023)
- **Ref.** Yuhala, P.; Paper, M.; Zerbib, T.; Felber, P.; Schiavoni, V.; Tchana, A. "SGX Switchless
  Calls Made Configless". DSN 2023, pp. 229–238. DOI 10.1109/DSN58367.2023.00032. arXiv 2305.00763.
- **Trilha:** RT, **PER**.
- **Contribuição:** ajuste dinâmico das *worker threads* das chamadas switchless.
- **Avaliação:** benchmarks.
- **Para nós (base, marginal):** exemplo de PER curto sobre desempenho de TEE.
- **PDF:** `2023_yuhala_switchless.pdf`.

**[32] CVMs × canais laterais por contadores de desempenho** (2024)
- **Ref.** Lou, X.; Chen, K.; Xu, G.; Qiu, H.; Guo, S.; Zhang, T. "Protecting Confidential Virtual
  Machines from Hardware Performance Counter Side Channels". DSN 2024, pp. 195–208.
  DOI 10.1109/DSN58291.2024.00031. Sem versão aberta.
- **Trilha:** RT.
- **Contribuição:** o arcabouço Aegis (mesmo nome do [47], trabalho diferente):
  - perfila a aplicação e estima o vazamento por evento de HPC com teoria da informação;
  - faz fuzzing de sequências de instruções;
  - ofusca com **privacidade diferencial** dentro da VM SEV.
- **Avaliação:** **a verificar**.
- **Para nós (base, Juiz):** canal lateral é limitação declarada do DNAT (D3). Citar como a defesa
  que existe para CVMs.
- **PDF:** instituição.

**[33] ConfBench** (2025)
- **Ref.** De Murtas, A.; D'Elia, D. C.; Di Luna, G. A.; Felber, P.; Querzoni, L.; Schiavoni, V.
  "ConfBench: A Tool for Easy Evaluation of Confidential Virtual Machines". DSN 2025, pp. 279–288.
  DOI 10.1109/DSN64029.2025.00038.
- **Versões abertas:** diag.uniroma1.it/~delia/papers/dsn25.pdf e IRIS hdl 11573/1739400. Nenhuma
  respondeu na coleta: conexão falhou e 403.
- **Trilha:** RT, 10 pp. (ferramenta, provável; **a verificar**).
- **Contribuição:** ferramenta que gerencia o ciclo de vida de cargas (FaaS e clássicas) em CVMs
  Intel TDX e AMD SEV-SNP, com ARM CCA simulado.
- **Avaliação:** overhead em inferência de ML, SGBD, benchmarks nativos e atestação.
- **Para nós (base, central para a medição):** é a referência de como medir overhead de CVM no
  DSN. Citar e, se der, **usar** para medir o warm pool e as CVMs de uso único (E2).
- **PDF:** instituição (link aberto inacessível na coleta).

**[34] Atestação contínua: o caso Keylime** (2025)
- **Ref.** Ruffin, M.; Wang, C.; Almási, G.; Adebayo, A. A.; Franke, H.; Wang, G. "Towards Continuous
  Integrity Attestation and Its Challenges in Practice: A Case Study of Keylime". DSN 2025,
  pp. 256–265. DOI 10.1109/DSN64029.2025.00036. Sem versão aberta; código em
  github.com/mruffin/Dynamic-Policy-Generator.
- **Trilha:** RT, 10 pp. (tipo **a verificar**).
- **Contribuição:**
  - falsos positivos vêm de atualizações do SO não agendadas;
  - propõe política dinâmica, testada por 66 dias;
  - acha cinco problemas em Keylime/IMA que permitem escapar da detecção em todos os cenários
    testados.
- **Avaliação:** experimentos ativos de longa duração.
- **Para nós (base):** atestação está fora do escopo (D3), mas este artigo mostra que atestação
  contínua tem falhas práticas. Citar ao justificar a **CVM de uso único**, que dispensa
  atestação contínua.
- **PDF:** instituição.

**[35] Tempo confiável do Triad** (2025, **Industry Track**)
- **Ref.** Bettinger, M.; Ben Mokhtar, S.; Simonet-Boulogne, A. "An Open-source Implementation and
  Security Analysis of Triad's TEE Trusted Time Protocol". DSN-S 2025.
  DOI 10.1109/DSN-S65789.2025.00053 (lido no PDF). arXiv 2507.20851.
- **Trilha:** Industry.
- **Contribuição:** implementação aberta do Triad. O SO malicioso acelera o relógio do TEE, e o
  salto de tempo se propaga a máquinas honestas.
- **Avaliação:** experimentos com a implementação.
- **Para nós (base, A):** tempo dentro do TEE não é confiável. Citar se o mercado depender de
  prazos medidos dentro da CVM, como janelas de prova ou expiração de recompensa.
- **PDF:** `2025_bettinger_triad-tee-time.pdf`.

**[36] AnBridge** (2026)
- **Ref.** Farina, G.; Della Corte, R.; Machiry, A.; Cinque, M.; Bagchi, S. "AnBridge: Protecting
  On-Device AI with Android Virtualization Framework". DSN 2026, pp. 835–848.
  DOI 10.1109/DSN69566.2026.00081. Aberto em
  engineering.purdue.edu/dcsl/publications/papers/2026/anbridge-dsn26.pdf.
- **Trilha:** RT.
- **Contribuição:** modelo de programação e middleware para levar código de IA para VMs protegidas
  (pVM) do Android sem reescrever.
- **Avaliação:** latência e vazão com overhead de 2–14%, RQs e dois apps reais.
- **Para nós (B, base):** proteger o **modelo** dentro de VM isolada. É o mesmo problema do rumo B,
  em celular. Citar como precedente de "modelo em VM protegida".
- **PDF:** `2026_farina_anbridge.pdf`.

### 4.6 Containers, isolamento e controle de saída

**[37] Torpedo** (2022)
- **Ref.** McDonough, K.; Gao, X.; Wang, S.; Wang, H. "Torpedo: A Fuzzing Framework for Discovering
  Adversarial Container Workloads". DSN 2022, pp. 402–414. DOI 10.1109/DSN53405.2022.00048.
  Aberta só a **tese de mestrado** do primeiro autor (VTechWorks hdl 10919/104159), não o artigo.
- **Trilha:** RT.
- **Contribuição:** fuzzing de syscalls que acha cargas que furam o isolamento de recursos entre
  containers, inclusive *zero-days*.
- **Avaliação:** plataformas de container populares.
- **Para nós (base):** o container sozinho não isola recursos. Citar ao justificar **uma CVM por
  job** em vez de containers lado a lado.
- **PDF:** `2022_mcdonough_torpedo-tese.pdf` (é a tese, 89 pp.).

**[38] Rewind & Discard** (2023)
- **Ref.** Gülmez, M.; Nyman, T.; Baumann, C.; Mühlberg, J. T. "Rewind & Discard: Improving Software
  Resilience using Isolated Domains". DSN 2023, pp. 402–416. DOI 10.1109/DSN58367.2023.00046.
  Aberto no repositório da ULB.
- **Trilha:** RT, REG.
- **Contribuição:** o domínio isolado é descartado após um ataque, sem replicar nem fazer
  checkpoint.
- **Avaliação:** biblioteca SDRaD aplicada a software real.
- **Para nós (base):** paralelo com "CVM de uso único descartada". Citar ao enquadrar o descarte
  como mecanismo de resiliência.
- **PDF:** `2023_gulmez_rewind-discard.pdf`.

**[39] lazypoline: interposição de syscalls** (2024)
- **Ref.** Jacobs, A.; Gülmez, M.; Andries, A.; Volckaert, S.; Voulimeneas, A. "System Call
  Interposition Without Compromise". DSN 2024, pp. 183–194. DOI 10.1109/DSN58291.2024.00030.
  Aberto no repositório da TU Delft (File_499bdf55-…), que não respondeu na coleta.
- **Trilha:** RT.
- **Contribuição:** a interposição é exaustiva (pega toda instrução de syscall) com o custo da
  reescrita binária.
- **Avaliação:** micro e macrobenchmarks.
- **Para nós (base, Juiz):** a camada L2 do Juiz observa syscalls (seccomp em modo log). Citar
  como alternativa de monitoração barata e completa.
- **PDF:** instituição (link aberto inacessível na coleta).

**[40] Mutiny: como o Kubernetes falha** (2024)
- **Ref.** Barletta, M.; Cinque, M.; Di Martino, C.; Kalbarczyk, Z.; Iyer, R. K. "Mutiny! How Does
  Kubernetes Fail, and What Can We Do About It?". DSN 2024, pp. 1–14.
  DOI 10.1109/DSN58291.2024.00016. arXiv 2404.11169.
- **Trilha:** RT; foi o primeiro artigo dos anais de 2024.
- **Contribuição:**
  - análise de falhas de campo do K8s;
  - cerca de 9.000 injeções no etcd;
  - 3% causam falha do cluster inteiro e 24% causam provisionamento errado;
  - os campos de dependência entre objetos respondem por 51% das falhas de cluster.
- **Avaliação:** FFDA mais campanha de injeção, comparadas entre si.
- **Para nós (base, método):** é o **molde DSN clássico**: dados de campo → modelo de falhas →
  injeção → comparação. Citar como modelo de método. O estado de controle do DNAT (fila de jobs,
  warm pool) é o ponto único equivalente.
- **PDF:** `2024_barletta_kubernetes.pdf`.

**[41] KubeFence** (2025)
- **Ref.** Cesarano, C.; Natella, R. "KubeFence: Security Hardening of the Kubernetes Attack Surface".
  DSN 2025, pp. 497–510. DOI 10.1109/DSN64029.2025.00054. arXiv 2504.11126.
- **Trilha:** RT.
- **Contribuição:**
  - os CVEs do K8s só são exploráveis por campos específicos da API;
  - gera políticas finas a partir de *operators* confiáveis;
  - catálogo de especificações maliciosas.
- **Avaliação:** mitiga todos os exploits testados, reduz a superfície em 35% frente ao RBAC e
  custa cerca de 50 ms por operação.
- **Para nós (base):** **mínimo privilégio derivado automaticamente** e avaliado contra um
  catálogo de ataques. É o mesmo formato que podemos usar para a política de rede da CVM. Citar
  no desenho da E2c.
- **PDF:** `2025_cesarano_kubefence.pdf`.

**[42] KubeChecker** (2025, **Industry Track**)
- **Ref.** Sun, Y.; Lyu, D.; Cui, C.; Xu, H. "KubeChecker: Detecting Configuration Bugs in Container
  Orchestration". DSN-S 2025, pp. 91–97. DOI 10.1109/DSN-S65789.2025.00047. Sem versão aberta.
- **Trilha:** Industry.
- **Contribuição:** base de padrões de defeito de configuração, validada contra tickets da Huawei
  Cloud. Inclui varredura e confirmação por injeção de falhas.
- **Avaliação:** comparação com ferramentas e implantação em produção.
- **Para nós (base, marginal):** varredura + confirmação dinâmica. Citar só se discutirmos
  configuração de orquestração.
- **PDF:** instituição.

**[43] SNAS: saída de rede segura para sandboxes** (2026, **Industry Track**)
- **Ref.** Sharma, N. K. et al. (14 autores, Snowflake) "SNAS: A Multi-Layer Defense-in-Depth
  Architecture for Secure Egress in Sandboxed Workloads". DSN-S 2026, pp. 1–7.
  DOI 10.1109/DSN-S70715.2026.00032. arXiv 2606.17533.
- **Trilha:** Industry.
- **Contribuição:** saída de rede de UDFs em sandbox controlada por filtros eBPF, overlay GENEVE e
  proxies de saída com política em duas camadas.
- **Avaliação:** medição em produção, em todas as regiões do Snowflake.
- **Para nós (base, Juiz):** é o caso industrial mais próximo da nossa regra "a CVM só fala com o
  DNAT" e do proxy de registro da fase de fetch. Citar como prática de produção para o controle
  de saída.
- **PDF:** `2026_sharma_snas.pdf`.

### 4.7 Segurança de ML/LLM: jailbreak, guardrails, backdoor e controle de uso

**[44] Prefill burla o alinhamento** (2026)
- **Ref.** Li, Y.; Hu, J.; Sang, W.; Ma, L.; Nie, D.; Zhang, W.; Yu, A.; Su, Y.; Huang, Q.; Zhou, Q.
  "Bypassing Safety Alignment via API Design: A Systematic Risk Analysis of Response Prefill in
  LLM Systems". DSN 2026, pp. 485–497. DOI 10.1109/DSN69566.2026.00054 (verificado).
  arXiv 2504.21038, com o título anterior "Prefill-level Jailbreak: A Black-Box Risk Analysis of
  Large Language Models".
- **Trilha:** RT.
- **Contribuição:**
  - sete categorias de ataque por *response prefill*;
  - o sucesso passa de 99% com estratégia adaptativa, em 14 modelos de 8 provedores;
  - o prefill desloca a distribuição do primeiro token de recusa para obediência;
  - filtros de entrada falham.
- **Avaliação:** benchmark multi-provedor com análise de probabilidade por token e RQs.
- **Para nós (B, central):** quem controla o início da resposta derruba o alinhamento. No rumo B,
  o DNAT tem de **controlar a interface de inferência**, e não só os pesos. Citar como a ameaça
  que os guardrails do DNAT precisam cobrir.
- **PDF:** `2026_li_prefill-jailbreak.pdf` (versão arXiv com o título anterior).

**[45] Prompt polimórfico contra prompt injection** (2025, **Industry Track**)
- **Ref.** Wang, Z.; Nagaraja, N.; Zhang, L.; Bahşi, H.; Patil, P.; Liu, P. "To Protect the LLM Agent
  Against the Prompt Injection Attack with Polymorphic Prompt". DSN-S 2025, pp. 22–28.
  DOI 10.1109/DSN-S65789.2025.00037. arXiv 2506.05739.
- **Trilha:** Industry.
- **Contribuição:** variar a estrutura do *system prompt* a cada chamada (PPA) impede o atacante
  de prevê-la. Custo quase nulo.
- **Avaliação:** ataques existentes comparados com outras defesas, com RQs.
- **Para nós (Juiz, B):** é o mesmo princípio de "segredos do protocolo gerados na execução" do
  Juiz. Citar como evidência de que aleatorizar a estrutura ajuda contra o atacante adaptativo.
- **PDF:** `2025_wang_polymorphic-prompt.pdf`.

**[46] RIPE-II: injeção indireta em RAG** (2026)
- **Ref.** Malladi, G.; Thamilarasu, G. "RIPE-II: Retrieval In-Place Poisoning Evaluation with
  Indirect Injections". DSN 2026, pp. 800–812. DOI 10.1109/DSN69566.2026.00078. Sem versão aberta.
- **Trilha:** RT.
- **Contribuição:** benchmark de injeções indiretas em corpora envenenados, sem delimitadores,
  textuais e visuais. Modela posição, *chunking* e truncamento, com avaliação em dois estágios.
- **Avaliação:** **a verificar**; o resumo foi cortado.
- **Para nós (Juiz, B):** se o Juiz usar LLM sobre artefatos do atacante (código, comentários,
  dados), sofre injeção indireta. Citar no modelo de ameaça do Juiz.
- **PDF:** instituição.

**[47] Aegis: abuso de recursos via MCP** (2026, **Industry Track**)
- **Ref.** Priya, S.; Taylor, T.; Araujo, F. "Aegis: Preventing Cross-Domain Resource Abuse in MCP".
  DSN-S 2026, pp. 1–7. DOI 10.1109/DSN-S70715.2026.00036. arXiv 2608.20481.
- **Trilha:** Industry (IBM).
- **Contribuição:** o LLM normaliza chamadas heterogêneas de ferramentas numa representação
  única, sobre a qual o administrador escreve políticas finas.
- **Avaliação:** **a verificar**.
- **Para nós (B, marginal):** guardrail por política na camada de ferramentas. Citar como desenho
  de "política imposta por fora do modelo".
- **PDF:** `2026_priya_aegis.pdf`.

**[48] BProm: backdoor em modelo caixa-preta** (2025)
- **Ref.** Huang, Z.; Chen, J.; Zhang, Z.; Yu, C.-M. "Prompting the Unseen: Detecting Hidden
  Backdoors in Black-Box Models". DSN 2025, pp. 547–561. DOI 10.1109/DSN64029.2025.00058.
  arXiv 2411.09540.
- **Trilha:** RT.
- **Contribuição:** detectar backdoor só com acesso caixa-preta, via *visual prompting*. O
  cenário motivador é a certificação de modelos em "centros de teste".
- **Avaliação:** experimentos extensos em visão.
- **Para nós (B):** o cenário "centro de teste certifica modelo sem ver o interior" é o papel que
  o DNAT faria no rumo B. Citar na motivação.
- **PDF:** `2025_huang_backdoor-prompting.pdf`.

**[49] Rowhammer no backdoor de DNN** (2023)
- **Ref.** Tol, M. C.; Islam, S.; Adiletta, A.; Sunar, B.; Zhang, Z. "Don't Knock! Rowhammer at the
  Backdoor of DNN Models". DSN 2023, pp. 109–122. DOI 10.1109/DSN58367.2023.00023. arXiv 2110.07683.
- **Trilha:** RT, REG.
- **Contribuição:** primeira injeção de backdoor fim a fim em hardware real via Rowhammer, com
  treino sob restrição de bits vulneráveis.
- **Avaliação:** ataque em hardware real.
- **Para nós (B):** os pesos podem ser alterados em execução, por baixo do guardrail. Citar para
  justificar a integridade de memória da CVM (SEV-SNP/TDX) no rumo B.
- **PDF:** `2023_tol_rowhammer-backdoor.pdf`.

**[50] LymphNode: controle de acesso a DNN** (2026)
- **Ref.** Pei, H.; Liu, S.; Liu, Z. "LymphNode: A Plug-and-Play Access Control Method for Deep
  Neural Networks". DSN 2026 (está na lista oficial de aceitos); DOI DSN **a verificar**.
  arXiv 2605.16227 (verificado).
- **Trilha:** RT.
- **Contribuição:**
  - política "negar por padrão" dentro do modelo;
  - perturbações universais esparsas anulam a utilidade para consultas não autorizadas;
  - uma credencial no espaço de features restaura a utilidade;
  - bastam menos de 100 amostras.
- **Avaliação:** **a verificar** (extração e inversão de modelo).
- **Para nós (B):** controle de uso embutido no modelo é uma alternativa ao controle pelo DNAT.
  Citar como trabalho relacionado e como contraste: proteção no modelo × proteção na
  infraestrutura.
- **PDF:** `2026_pei_lymphnode.pdf`.

### 4.8 Vazamento de dados e canais

**[51] Vazamento por logits na destilação federada** (2024)
- **Ref.** Xiao, D.; Yang, D.; Li, J.; Chen, X.; Wu, W. "Privacy Leakage from Logits Attack and its
  Defense in Federated Distillation". DSN 2024, pp. 169–182. DOI 10.1109/DSN58291.2024.00029.
  Sem versão aberta.
- **Trilha:** RT.
- **Contribuição:** o L-Attack reconstrói dados privados a partir **só dos logits enviados**. A
  defesa LabelAvg envia rótulos duros com suavização por votação.
- **Avaliação:** **a verificar**.
- **Para nós (Juiz, central):** é vazamento pela **saída legítima** de um programa de ML. Reduzir
  a granularidade da saída (rótulo em vez de logit) é uma defesa possível. Citar no Juiz, caso ML
  do benchmark.
- **PDF:** instituição.

**[52] Owl: detecção diferencial de vazamento em CUDA** (2024)
- **Ref.** Zhao, Y.; Xue, W.; Chen, W.; Qiang, W.; Zou, D.; Jin, H. "Owl: Differential-Based
  Side-Channel Leakage Detection for CUDA Applications". DSN 2024, pp. 362–376.
  DOI 10.1109/DSN58291.2024.00044. Sem versão aberta.
- **Trilha:** RT.
- **Contribuição:** rastreia a execução, compara traços com **entradas diferentes** e aplica teste
  estatístico para decidir se a diferença vem do segredo.
- **Avaliação:** Libgpucrypto, PyTorch e nvJPEG.
- **Para nós (Juiz, central):** é o mesmo princípio da camada L2 com **variação do segredo** e
  teste estatístico. Citar como precedente metodológico da detecção diferencial.
- **PDF:** instituição.

**[53] YODA: canal encoberto via DNS público** (2023)
- **Ref.** Saha, S.; Karapoola, S.; Rebeiro, C.; Kamakoti, V. "YODA: Covert Communication Channel over
  Public DNS Resolvers". DSN 2023, pp. 252–260. DOI 10.1109/DSN58367.2023.00034. Sem versão aberta.
- **Trilha:** RT, **PER**.
- **Contribuição:** exfiltração pelos caches compartilhados de resolvedores públicos, sem
  identificar o adversário, a 480 bps.
- **Avaliação:** ataques reais em Google, Cloudflare, Quad9 e outros.
- **Para nós (base, Juiz):** justifica "sem DNS" na regra de saída da CVM (D4/E2c). Citar ao
  explicar por que até o DNS é bloqueado.
- **PDF:** instituição.

**[54] DisTA: taint dinâmico em sistemas Java distribuídos** (2022)
- **Ref.** Wang, D.; Gao, Y.; Dou, W.; Wei, J. "DisTA: Generic Dynamic Taint Tracking for Java-Based
  Distributed Systems". DSN 2022, pp. 547–558. DOI 10.1109/DSN53405.2022.00060. Sem versão aberta.
- **Trilha:** RT.
- **Contribuição:** taint entre nós instrumentando os módulos de rede do Java, com cerca de 10
  linhas de mudança por sistema.
- **Avaliação:** cinco sistemas reais (ZooKeeper, Yarn…), rastreando todos os taints entre nós com
  overhead baixo.
- **Para nós (Juiz):** o taint dinâmico é a alternativa clássica ao Juiz para seguir o dado até a
  saída. Citar como linha de base que não pega canais implícitos e transformações (canário
  codificado).
- **PDF:** instituição.

---

## §5 Os 10 mais úteis para nós

1. **[19] LUMEN (2026), Juiz.** LLM + análise dinâmica para revelar o comportamento que o programa
   esconde. É o precedente mais próximo do Juiz dentro do DSN e mostra que o DSN aceita esse
   desenho.
2. **[9] OCTOPOCS (2021), A.** Verifica mecanicamente se um exploit vale no software que herdou o
   código. É o núcleo técnico do rumo A, já publicado no DSN. Precisamos nos diferenciar dele.
3. **[27] Deflection (2021), Juiz e base.** Verificador público dentro do enclave julga se um
   código de terceiros respeita a política antes de tocar os dados. É o "Juiz" estático em TEE.
4. **[44] Prefill (2026), B.** Mostra que o controle tem de estar na interface de inferência, não
   só nos pesos. É o argumento mais forte para o DNAT impor os guardrails do rumo B.
5. **[2] SBOM por metadados (2024), A.** O SBOM mente, e existe ataque para esconder pacotes dele.
   Sem SBOM confiável o rumo A não marca os dependentes, e isso justifica o SBOM do build
   atestado.
6. **[52] Owl (2024), Juiz.** Detecção diferencial com teste estatístico sobre entradas
   diferentes. É o fundamento metodológico da camada L2 com variação do segredo.
7. **[22] Reentrância na era dos LLMs (2026), Juiz e A.** Modelo de avaliação para o Juiz:
   benchmark rotulado à mão, cenários mínimos, LLM × ferramentas e enquadramento de
   dependabilidade.
8. **[40] Mutiny (2024), método.** O molde DSN de campo → modelo de falhas → injeção → comparação.
   Serve de referência de forma para o artigo, qualquer que seja o rumo.
9. **[33] ConfBench (2025), base.** Como o DSN mede overhead de CVMs TDX e SEV-SNP. Serve de
   referência para medir o warm pool e as CVMs de uso único, e talvez como ferramenta.
10. **[51] Vazamento por logits (2024), Juiz.** Vazamento pela saída legítima de um programa de
    ML, com defesa por redução da saída. É o caso ML do benchmark do Juiz.

Logo depois: [43] SNAS (controle de saída em produção), [1] PDGraph e [10] silent fixes
(motivação do A), [45] prompt polimórfico (segredos gerados na execução), [17] VulLens (atacante
adaptativo contra detectores).

---

## Pendências e observações

- **Pedir via instituição** os 25 marcados "instituição". Prioridade: LUMEN, Owl, vazamento por
  logits, ConfBench, PDGraph e VCAligner.
- **Links abertos que falharam na coleta:**
  - ConfBench: diag.uniroma1.it, conexão falhou; IRIS, 403;
  - lazypoline: repository.tudelft.nl, sem resposta.
  Vale tentar de novo no navegador.
- **Torpedo:** o PDF é a tese de mestrado, não o artigo.
- **Prefill e MCP:** os PDFs são preprints arXiv com título anterior ou versão pré-revisão.
  Conferir números contra a versão final antes de citar.
- **DOIs a confirmar:** VulStyle [18], LymphNode [50] e o pôster [20].
- **Anais de 2024:** o site oficial do DSN 2024 (dsn2024uq.github.io/Proceedings) publica o
  sumário com caminhos de PDF de todos os artigos. Não baixamos de lá porque não é claramente
  uma versão de acesso aberto autorizada. Fica para o grupo decidir.
- **Cobertura:** a busca foi por título e resumo, a partir das listas oficiais e da OpenAlex.
  Artigos de 2021–2022 do Industry Track e do DSN-S não foram varridos sistematicamente.
