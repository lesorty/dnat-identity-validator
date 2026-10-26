# E8 · Alinhamento com o DSN: A (bug bounty) × B (modelos abertos)

**Data:** 2026-10-26 · **Status:** análise; a decisão é do grupo. **Pergunta:** qual tema se enquadra
melhor no **teor do DSN**, supondo que os dois sejam factíveis até 02/dez. Esforço, prazo e custo
ficam **fora** desta análise (estão na [E7](E7_decisao_rumo.md)).

**Base:**
- CFP do DSN 2027, Research Track, lido na fonte em 2026-10-26.
- Corpus: os **307 artigos** do Research Track de 2021 a 2026 (e os 86 do Industry Track),
  classificados por tema ([TEMAS_DSN.md](../referencias/TEMAS_DSN.md) e
  [temas_dsn_2021_2026.csv](../referencias/temas_dsn_2021_2026.csv)).
- **Leitura completa de 16 artigos-âncora** (8 por tema), cujos PDFs estão em
  [referencias/dsn/](../referencias/dsn/).
- Workshops e prêmios do DSN de 2023 a 2026.

**Temas:** A = [E5](E5_alt_bug_bounty.md); B = [E6](E6_alt_modelos_abertos.md).

---

## 1. Resposta curta

**B se alinha melhor ao DSN, desde que seja vendido como mecanismo de dependabilidade**: manter uma
propriedade de *safety* (a recusa) sob modificação do sistema, com detecção e contenção. Não pode
ser vendido como "mais um detector de obliteração". **Confiança: 0,65.**

A tem mais precedentes acumulados e um prêmio, mas eles cobrem a parte **menos nova** de A
(verificação e propagação). O núcleo novo de A (mercado, recompensa cumulativa, ocultação) não tem
precedente no DSN, não está nomeado no CFP e traz o risco ético que o CFP lista como motivo de
rejeição.

## 2. O que o DSN diz que é

A missão no CFP tem três partes:
- dependabilidade e segurança como um único corpo de conhecimento;
- combate, ao mesmo tempo, a falhas acidentais, ataques maliciosos, erros de projeto e condições
  inesperadas de operação;
- sistemas para prevenir, detectar, diagnosticar, eliminar ou recuperar dessas ameaças, mais a
  avaliação prática da dependabilidade e da segurança de sistemas reais.

Os critérios de julgamento são *insight, originality, significance, correctness e potential impact*.

**Consequência para nós:** o artigo que o DSN reconhece descreve uma **propriedade que o sistema
precisa manter**, as **causas acidentais e maliciosas** que a ameaçam, e um **mecanismo medido**
de detecção ou contenção.

## 3. Evidência 1: o CFP ao pé da letra

| Rubrica do CFP 2027 | A | B |
|---|---|---|
| *AI/ML for resilient systems*: "robustness issues in AI/ML/LLM systems" | — | **Núcleo** |
| *Agentic AI*: verificação e certificação, *alignment and safety*, *jailbreaking* | — | **Núcleo** (o portão certifica o derivado; a obliteração é um *jailbreak* nos pesos) |
| *Hardware*: TEEs | Peça (verificação na CVM) | Peça (custódia na CVM) |
| *Software*: *software security*, *dependable software design* | Peça (cadeia de suprimentos) | — |
| *Distributed ledgers*: criptomoedas, provas de conhecimento zero | Peça (vault; ocultação por ZK) | Opcional (linhagem no contrato) |
| *Models and methodologies*: *benchmarking*, *field data analysis* | Peça (CVEs reais, SBOMs reais) | Peça (campanha de modificações) |

**Leitura:**
- O núcleo de B está **nomeado** em duas rubricas.
- A entra por **quatro peças**, mas nenhuma rubrica cobre o núcleo de A, o mercado. "Cadeia de
  suprimentos" e "economia de segurança" não aparecem no CFP.
- **Vantagem: B, clara.**

## 4. Evidência 2: o que o DSN publica (Research Track, 2021–2026)

Classificação por título e resumo, com um código por artigo. Em 2026, 48 artigos foram
classificados só pelo título, porque faltam resumos na OpenAlex.

| Ano | Total | A núcleo | A adjacente | B núcleo | B adjacente | Ponte |
|---|---|---|---|---|---|---|
| 2021 | 48 | 3 | 3 | 0 | 5 | 0 |
| 2022 | 49 | 0 | 5 | 0 | 2 | 0 |
| 2023 | 47 | 0 | 3 | 0 | 7 | 0 |
| 2024 | 42 | 1 | 4 | 0 | 3 | 0 |
| 2025 | 56 | 3 | 6 | 1 | 8 | 0 |
| 2026 | 65 | 2 | 14 | 4 | 14 | 1 |
| **Total** | **307** | **9 (2,9%)** | 35 | **5 (1,6%)** | 39 | 1 |

**Leitura:**
- **Volume acumulado: A.** O núcleo de A tem 9 artigos, contra 5 do núcleo de B. Os de A vêm em
  ondas (2021, 2024, 2025, 2026), sem tendência de crescimento.
- **Tendência: B.** O núcleo de B era zero até 2024 e passou para 1 em 2025 e 4 em 2026 (6,2% do
  ano). Somando os adjacentes, B foi de 10% em 2021 para 28% em 2026. O programa de 2026 já tinha
  **duas sessões de LLM**, enquanto cadeia de suprimentos dividiu sessão com mobile e firmware.
- **Os adjacentes de B mostram a "voz" do DSN para ML.** A linha mais DSN de B não é o ataque. É a
  **confiabilidade de sistemas de ML**:
  - *LLMGuard*: diagnóstico de falhas em LLM como serviço, 2026;
  - *Multi-version ML and Rejuvenation for Resilient Perception*, 2025;
  - *ReMlX*: resiliência de *ensembles* contra dados de treino defeituosos, 2025;
  - *Thinking Inside the Box*: falhas por radiação em aceleradores de ML, 2026, **premiado**;
  - *Keeping Reliability on Track* em aprendizado federado, 2026.
  Três deles foram lidos depois (§9.1, ✔); o LLMGuard não tem versão aberta.
- **Os adjacentes de A são detecção de vulnerabilidades e fuzzing** (14 em 2026). É um tema forte no
  DSN, mas é o "achar o bug", não o "mercado".

## 5. Evidência 3: proximidade dos precedentes

| | A | B |
|---|---|---|
| **O mais próximo** | **OCTOPOCS** (DSN'21) ✔: verifica a PoC no software que herdou o código | **Prefill** (DSN'26) ✔: quem controla a interface derruba o alinhamento; em modelo aberto, o usuário controla tudo |
| **Segundo** | **SBOM por metadados** (DSN'24) ✔: o SBOM erra e é atacável; **Distinguished Paper Award** | **LymphNode** (DSN'26) ✔: proteção dentro do modelo; o modelo de ameaça (§III-A) **supõe um runtime que preserva a integridade dos parâmetros**, e a custódia fornece exatamente isso |
| **O que os precedentes cobrem** | A metade "verificação + propagação", a **menos nova** de A | A motivação e o contraste "proteção no modelo × custódia" |
| **O que nenhum cobre** | Mercado, recompensa cumulativa, ocultação de dependentes | Obliteração e fine-tuning nocivo |
| **Problema de proximidade** | OCTOPOCS mostra que código presente nem sempre é disparável, então marcar pelo SBOM superestima | Nenhum precedente de "detector de obliteração", o que é bom para a novidade e ruim para o encaixe |

- **Vantagem: A em proximidade**, mas a proximidade está na parte que não é a contribuição.

## 6. Evidência 4: como os artigos aceitos se vendem

Contei o vocabulário no corpo dos 16 PDFs: *dependab*, *reliab*, *fault*, *failure*, *resilien* e
*attack*. Quatro padrões aparecem:
1. **Segurança de ML/LLM "pura" entra no Research Track.**
   - O Prefill (2026) tem zero termos de dependabilidade e 142 de "attack".
   - O BProm (2025) é detector de ML puro.
   - Portanto B não **precisa** de embalagem para entrar. Mas os que embalam fazem isso trocando o
     nome do problema: o Prefill trocou "jailbreak" por "API design … risk analysis of LLM
     systems", e o LymphNode vende implantabilidade e resiliência.
2. **Os grupos de dependabilidade fundem uma propriedade de segurança com tolerância a falhas.** É
   o caso de Plinius (SGX + memória persistente contra quedas), Iniva (BFT + incentivo) e AnBridge
   (TCB + overhead).
3. **O traço DSN mais fácil de copiar é um modelo de ameaça com causa acidental e maliciosa
   juntas:**
   - MCP: hosts e registries *honest-but-flawed*;
   - Aegis: pedido excessivo não intencional;
   - SBOM: omissão acidental × *parser confusion*;
   - Reentrancy Redux: bug de compilador habilitando ataque.
   **B tem essa dualidade no núcleo:** o fine-tuning benigno degrada a recusa por acidente, e a
   obliteração a remove de propósito. Em A, a dualidade existe na propagação (falha dormente
   replicada), mas **não no mercado**.
4. **Avaliação no formato RQs + Findings** em quase todos de 2025–2026.
   - A tende a produzir **dados de campo** grandes (24 mil pacotes, 67 mil servidores, 7,9 mil
     projetos).
   - B tende a produzir **benchmark com atacante adaptativo e overhead** (14 modelos no Prefill;
     9 ataques e 10 defesas no BProm).
   - O DSN aceita as duas formas.

- **Vantagem: B, leve.** B se escreve inteiro como detecção e contenção de erro. Em A, o mercado
  fica fora do enquadramento.

## 7. Evidência 5: comunidade (workshops e prêmios)

- **Workshops:**
  - **B tem casa no DSN.** O **DSML** (ML confiável e seguro) aconteceu em 2024, 2025 e 2026; em 2026
    incluiu IA generativa e prompt injection. O **CRAI 2026** tratou de IA agêntica.
  - **A não tem.** Nenhum workshop tem cadeia de suprimentos como tema central.
  - Isso indica que o PC tem revisores de ML confiável em número. Os workshops de 2027 ainda não
    foram escolhidos (propostas até 13/jan/2027).
- **Prêmios:**
  - O único artigo de núcleo premiado foi o de **SBOM (A), Distinguished Paper de 2024**.
  - Em 2026, o prêmio foi para falhas por radiação em aceleradores de ML (B adjacente).
  - Há uma divergência entre as páginas do DSN (um prêmio por ano) e a lista do IFIP WG 10.4 (três
    vencedores), registrada no TEMAS_DSN §7.
- **Vantagem:** B nos workshops; A no prêmio.

## 8. Placar de alinhamento

| Critério | Vantagem | Evidência decisiva |
|---|---|---|
| CFP ao pé da letra | **B, clara** | §3: o núcleo de B está nomeado; o de A, não |
| Volume de precedentes | **A** | §4: 9 × 5 artigos de núcleo |
| Tendência | **B** | §4: B de 0 para 4 por ano; duas sessões de LLM em 2026 |
| Proximidade do precedente | **A** (na parte menos nova) | §5: OCTOPOCS e SBOM |
| Enquadramento como dependabilidade | **B, leve** | §6: a dualidade acidental/maliciosa está no núcleo de B |
| Comunidade (workshops, prêmios) | **Empate** | §7: DSML para B; prêmio do SBOM para A |
| Risco de "isto é de outra conferência" | **B** | A linhagem do mercado de A está em USENIX, CCS e EuroS&P (Hydra, Sealed-Glass, economia de bounty), e nenhum artigo do DSN vendeu um mercado. B corre o risco de "isto é SaTML", contornável como fizeram Prefill e LymphNode |
| Ética, que o CFP lista como motivo de rejeição | **B** | A publica o desenho de uma lista de alvos com preço; B segue a prática publicada (Hurtado, Arditi) |

**Resultado:** B vence 5 critérios, A vence 2 e um empata.

## 9. O enquadramento mais "DSN" de cada um

### B: *Safety by Custody* (o recomendado; refinado em 2026-10-26)

**Título provisório:** *Safety by Custody: Containing Accidental and Malicious Refusal Failures in
Open-Weight LLM Derivatives.* Alternativa mais curta: *Safety by Custody: Preserving Refusal Across
Fine-Tuning of Open-Weight LLMs.*

#### 9.1 O que os artigos de "mesmo norte" ensinam

Foram lidos três dos quatro artigos ✔. O LLMGuard [58] não tem versão aberta e fica para baixar
pela instituição. Fichas completas no [GUIA §4.9](../referencias/GUIA_DSN.md).

| Artigo | Lição de forma | Como entra em B |
|---|---|---|
| **Multi-version ML [55]** (DSN'25) | Cada módulo de ML passa por três estados: saudável (H), **comprometido mas funcional (C)** e não funcional (N). Votador e rejuvenescimento são declarados **confiáveis**. Falha acidental e ataque ficam no mesmo modelo. Avaliação em três camadas: modelo analítico (redes de Petri) + injeção de falhas + caso realista | Os mesmos três estados para o derivado. O estado C é o objetivo do atacante (útil e sem recusa). Componentes confiáveis explícitos. Recuperação: reverter ao base custodiado |
| **ReMlX [56]** (DSN'25) | Modelo de falhas como **falhas nos dados de treino**, numa tabela por classe com origem real. Ferramenta de injeção. Curvas de resultado em função da **quantidade de falha** (0–50%). Distribuições realistas em vez de uniformes. Custo reportado ao lado do ganho | O fine-tuning é "treino com dados possivelmente defeituosos". Tabela de classes de falha, varredura da quantidade de falha e overhead do portão ao lado da cobertura |
| **TPU-FI [57]** (DSN'26, premiado) | O modelo de falhas é **derivado de dados reais** (feixe de radiação), e o injetor é **validado contra o campo** (taxa de falhas a 1,7×). O modelo sintético simples subestima em até ~4× | Os obliterados públicos do HF são o "campo"; as nossas abliterações são o "injetor". Medir se os sinais do portão têm a mesma distribuição nos dois. Isso responde à crítica da E7 de que a população é construída por nós |

#### 9.2 Enquadramento refinado

1. **Serviço e propriedade.** O DNAT oferece fine-tuning de modelo aberto como serviço. A
   propriedade de *safety* S é esta: **todo derivado liberado mantém a recusa do base dentro de uma
   tolerância δ**, medida numa bateria fixa e parcialmente secreta.
2. **Modelo de falhas** (no molde da tabela do ReMlX):

   | Classe | Causa | Exemplo | "Quantidade de falha" a varrer |
   |---|---|---|---|
   | F1 acidental | Dados benignos | LoRA em Alpaca ou GSM8K que degrada a recusa (Qi et al. 2024) | Passos ou épocas de treino |
   | F2 maliciosa nos dados | Dados nocivos | LoRA com 10–100 exemplos nocivos; *Covert Malicious Finetuning* | Número ou fração de exemplos nocivos |
   | F3 maliciosa nos pesos | Edição direta | Abliteração rank-1 (Arditi et al.) | Intensidade da edição e camadas |
   | F4 adaptativa | O atacante conhece o portão | Treino contra o limiar; abliteração + LoRA de "cura" | Rodadas de adaptação |

   **Fora do modelo:**
   - exportação de pesos, contida pela custódia (C3);
   - backdoor com gatilho (limitação declarada);
   - canais laterais;
   - falhas de hardware na CVM: o Rowhammer [49] mostra que os pesos podem mudar depois da
     checagem, então a integridade de memória da CVM é **premissa**.
3. **Estados do derivado** (no molde do [55]): H (recusa preservada), C (útil e sem recusa) e N
   (degenerado). O portão precisa separar C de H; N se pega por utilidade. **A falha perigosa é
   liberar um C**: uma "liberação silenciosa", análoga à corrupção silenciosa de dados do [57].
4. **Componentes confiáveis:** a CVM, o portão (código e juiz fixados por hash) e a referência
   custodiada. **Não confiáveis:** o script, os dados de treino e o derivado.
5. **Ciclo completo de dependabilidade:**
   - **prevenção:** custódia (os pesos nunca saem);
   - **detecção:** o portão;
   - **contenção:** derivado reprovado não sai e não vira ativo;
   - **recuperação:** reverter ao base ou ao último derivado aprovado, e **revogar** um derivado já
     liberado se a bateria secreta posterior mostrar falha. O `revokeAsset` já existe em
     `smart-contract/contracts/DnatMarketplace.sol:183-191`.

#### 9.3 Métricas e perguntas de pesquisa

**Métricas, no vocabulário do DSN:**
- **taxa de liberação silenciosa**: a fração de derivados C aprovados. É a métrica-título;
- **cobertura de detecção** por classe de falha (TPR a FPR de 1% e 5%);
- **taxa de falso alarme** em F1 que preserva a recusa, que é o custo de disponibilidade para o
  usuário legítimo;
- **curvas de cobertura × quantidade de falha** (molde do [56]): o ponto em que a degradação já é
  real e o portão ainda não a vê;
- **representatividade** (molde do [57]): a distância entre os sinais nos derivados injetados e
  nos obliterados de campo;
- latência e custo por veredito; overhead da CVM;
- **modelo analítico leve** (versão simples do molde do [55]): com k tentativas e taxa de escape e
  por tentativa, a chance de escapar é 1 − (1 − e)^k. Isso justifica o registro de tentativas e o
  limite por conta.

**Perguntas de pesquisa (formato RQ dos artigos de 2025–26):**
- **RQ1:** cobertura e falso alarme por classe de falha;
- **RQ2:** sensibilidade à quantidade de falha;
- **RQ3:** representatividade da população injetada contra os obliterados de campo;
- **RQ4:** atacante adaptativo (rodadas até escapar);
- **RQ5:** custo e overhead na CVM.

**Seções que os três artigos têm e B deve ter:**
- ameaças à validade;
- artefato aberto: código, sinais e scripts de geração, **sem** publicar pesos nocivos.

#### 9.4 Para citar (atualizado)

- **Motivação:** Prefill [44] (quem controla a interface derruba o alinhamento) e LymphNode [50]
  (a proteção no modelo supõe integridade dos parâmetros, §III-A).
- **Molde de forma:** Multi-version ML [55], ReMlX [56] e TPU-FI [57].
- **Base técnica:**
  - BProm [48]: certificação no nível do modelo;
  - AnBridge [36]: modelo em VM protegida;
  - Plinius [29]: segurança e tolerância a falhas juntas;
  - Rowhammer [49]: premissa de integridade de memória.
- **Só depois de ler:** LLMGuard [58]; Aegis (DSN-S'26) como apoio de "acidental + malicioso".

**O que mudou em relação à primeira versão deste enquadramento:**
- de "detector" para **serviço com uma propriedade S**, modelo de falhas com quantidade, estados
  do derivado e ciclo completo de prevenção, detecção, contenção e recuperação;
- uma **RQ de representatividade** (injeção × campo), que vira contribuição metodológica e ataca o
  ponto fraco que a E7 apontou na avaliação de B;
- uma métrica-título que o DSN reconhece: **liberação silenciosa**.

### A: *Verified Containment* (se o grupo preferir A)

**Título provisório:** *Verified Containment of Vulnerability Propagation in Attested Software
Supply Chains.*

**Enquadramento:**
- **Falha:** uma vulnerabilidade num componente compartilhado é uma falha de projeto dormente,
  replicada nos dependentes.
- **Mecanismo:**
  - a prova de exploit na CVM é a **detecção de erro**;
  - o SBOM do build atestado é o grafo de propagação;
  - a marcação dos dependentes é a **contenção**;
  - o mercado vira mecanismo secundário, modelado como jogo no molde do Iniva.

**Métricas:**
- cobertura da verificação mecânica por classe;
- precisão e revocação da contenção contra a disparabilidade real (Tipos I–III do OCTOPOCS);
- tempo até a contenção.

**Para citar:** OCTOPOCS [9], SBOM [2], Reentrancy Redux [21], Iniva [26] e MCP [7] (molde de
Ética e Divulgação).

**O preço:** para soar DSN, A põe o mercado, que é a sua ideia nova, em segundo plano. O que sobra
colide com OCTOPOCS e com o Dependabot.

## 10. O que mudaria o veredito

- **A passaria à frente** se o grupo aceitar o enquadramento *Verified Containment*. A fica então
  tão DSN quanto B, mas a questão da novidade (E7) volta.
- **A também passaria** se houver, fora do corpus, um precedente de mercado de vulnerabilidades no
  DSN. Não há nenhum nos 307 artigos de 2021–2026.
- **B cairia** se fosse escrito como detector de obliteração isolado (C2 sem custódia). Aí o risco
  de "isto é SaTML" vira o mais provável.

## 11. Limites desta análise

- **Classificação aproximada:** feita por um só classificador, por título e resumo, com 72 dúvidas
  registradas no CSV. Em 2026, foi só pelo título.
- **"B núcleo" inclui vizinhos distantes:** backdoor em aprendizado federado e injeção em RAG. Os
  próximos de verdade são só Prefill, LymphNode e BProm.
- **PDFs:** 12 dos 16 lidos são preprints, e números ou títulos podem diferir da versão publicada.
- **Ainda sem ler:** os 22 artigos marcados "instituição", entre eles o LLMGuard [58]. Os outros
  três de "mesmo norte" foram lidos (§9.1).
- **Encaixe não é aceitação:** esta análise mede só o encaixe. Viabilidade, novidade e risco estão
  na E7, e as duas análises apontam na mesma direção por motivos diferentes.
