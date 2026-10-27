# Leitura: cadeia de suprimentos de modelos e custódia/execução confidencial

**Data:** 2026-10-27 · **Problema de referência:** [E10 §3–§5](../DSN2027/etapas/E10_problema.md)
(P1 integridade de segurança na cadeia de derivados; P2 recibo atestado; adversário = usuário com
os pesos dentro da CVM; operador confiável).
**Ponto de partida:** [05 §1 e §4](05_protecao_modelos.md), [02 §3–§5](02_transparencia_execucao_llm.md).
**Objetivo:** base científica do eixo "cadeia de suprimentos + custódia". Nada aqui implementa ou
propõe implementação.

**Convenções.**
- **Lido** = texto completo percorrido (resumo, introdução, método, resultados, limitações).
  **Parcial** = resumo + seções-chave. **Resumo** = só o resumo ou a página oficial.
- Venue: ✔ = conferido nesta rodada (PDF, arXiv ou OpenAlex); **(a verificar)** = não conferido.
- "p." = página do PDF baixado (numeração do arquivo, não do anal).
- Ataques aparecem só no nível do que o artigo mede; nenhum passo operacional é reproduzido.

---

## 0. PDFs baixados nesta rodada (`pesquisa/artigos/`)

Todos conferidos com `pdfinfo` (título e páginas). Nenhum arquivo foi sobrescrito: três já
existiam (baixados por outra frente) e foram só lidos (`2025_lin_consiglieres`, `2025_egler_auditing`,
`2024_halawi_covert`).

| Arquivo | Trabalho | Pág. |
|---|---|---|
| 2026_10alabs_redistribution.pdf | 10a Labs, *Uncensored Open-weight Models* (arXiv 2609.05241) | 9 |
| 2025_laufer_anatomy.pdf | Laufer et al., *Anatomy of a ML Ecosystem* (2508.06811) | 29 |
| 2026_nguyen_vulnerable.pdf | Nguyen et al., *Vulnerable Models in the AI Supply Chain* (2610.12893) | 18 |
| 2024_zhao_malhug.pdf | Zhao et al., *Models Are Codes* (2409.09368) | 12 |
| 2025_kellas_pickleball.pdf | Kellas et al., *PickleBall* (2508.15987) | 23 |
| 2025_liu_hideseek.pdf | Liu et al., *The Art of Hide and Seek* (2508.19774) | 17 |
| 2024_casey_exploit.pdf | Casey et al., *Exploit Instrumentation Study* (2410.04490) | 12 |
| 2025_wang_sokllmsupply.pdf | Wang et al., *Demystifying LLM Supply Chain Vulnerabilities* (2502.12497 v2; a v1 se chamava "SoK: …") | 12 |
| 2024_wang_llmsupplychain.pdf | Wang et al., *LLM Supply Chain: A Research Agenda* (2404.12736) | 47 |
| 2023_jiang_ptmreuse.pdf | Jiang et al., *PTM Reuse in Hugging Face* (2303.02552) | 14 |
| 2024_google_aisupplychain.pdf | Google SAIF, *Securing the AI Software Supply Chain* (abr/2024) | 50 |
| 2026_erfan_aibom.pdf | Erfan et al., *AIBOM Completeness in HF* (2607.17242) | 12 |
| 2025_spoczynski_atlas.pdf | Atlas (2502.19567) | 14 |
| 2025_duddu_laminator.pdf | Laminator (2406.17548) | 12 |
| 2025_horwitz_heritage.pdf | Horwitz et al., *Model Tree Heritage Recovery* (2405.18432) | 19 |
| 2025_nikolic_provenance.pdf | Nikolić et al., *Model Provenance Testing* (2502.00706) | 20 |
| 2025_schnabl_attestable.pdf | Attestable Audits (2506.23706) | 13 |
| 2026_jin_guardrail.pdf | Proof-of-Guardrail (2603.05786) | 9 |
| 2026_jin_aftune.pdf | AFTUNE (2603.07466) | 20 |
| 2023_pelrine_gpt4apis.pdf | Pelrine et al., *Exploiting Novel GPT-4 APIs* (2312.14302) | 31 |
| 2025_frikha_obfuscatune.pdf | ObfuscaTune (2407.02960) | 9 |
| 2025_mohanty_distillock.pdf | DistilLock (2510.16716) | 11 |
| 2025_rinberg_exfiltration.pdf | Rinberg et al. (2511.02620 v3) | 43 |
| 2025_anthropic_confidential.pdf | Anthropic + Pattern Labs, *Confidential Inference Systems* v1.0 (jun/2025) | 32 |
| 2025_chrapek_confidential.pdf | Chrapek et al. (2509.18886) | 15 |
| 2026_wang_h100tdx.pdf | Wang et al., H100 sob TDX (2607.19353) | 11 |
| 2026_asad_blackwell.pdf | Asad, Grunseid, Blackwell CC (2608.26575 v2) | 23 |
| 2025_lee_gputeeddp.pdf | Lee et al., GPU TEE em DDP (2501.11771) | 11 |
| 2024_zhu_hopper.pdf | Zhu et al., CC em Hopper (2409.03992) | 7 |

**Sem PDF baixado:**
- **Sokhansanj, *Uncensored AI in the Wild*** (Future Internet 17(10):477, 2025, CC BY): o MDPI e o
  preprints.org devolvem 403 a download automatizado. É acesso aberto; baixar pelo navegador em
  <https://doi.org/10.3390/fi17100477>. Só o **resumo** foi lido (via Semantic Scholar).
- Fontes que não são PDF: ver §G (links e data de acesso).

---

## A. Evidência de campo: derivados sem recusa circulam na cadeia

### A1. Lin, Li, Liao, Wang — *Consiglieres in the Shadow: Understanding the Use of Uncensored LLMs in Cybercrimes* · **Lido**
- **Ref.:** arXiv 2508.12622 v1, cs.CR, ago/2025. Venue: **só arXiv** ✔ (OpenAlex não registra
  publicação; o formato é de periódico ACM, venue final a verificar).
- **Lição:** a perda de recusa é **herdada e propagada pelas arestas de derivação** (fine-tuning,
  abliteração, *merge*, quantização), e a moderação do hub é reativa e cobre só uma fração.
- **Problema que define:** identificar em escala LLMs sem salvaguarda (ULLMs) entre ~700 mil modelos
  do Hugging Face, onde testar cada um é inviável e os metadados são incompletos.
- **Método:** grafo de conhecimento (modelos + datasets, arestas = fine-tuning, *merge*, compressão,
  abliteração, replicação) + GAT semissupervisionada (UFinder), a partir de 1.218 ULLMs rotulados,
  89 datasets sem censura e 82 censurados. Validação comportamental: 55 prompts do CatQA, taxa de
  não recusa (RSR, por casamento com 227 frases de recusa) e nota de nocividade por GPT-4o e
  Llama-3.3-70B.
- **Evidência principal:**
  - 11.598 ULLMs em 17.104 LLMs do grafo; 84 amostrados, **todos** confirmados (p. 2, p. 10).
  - Só **16,52%** marcados pelo HF como *Not-For-All-Audience* (p. 11).
  - Métodos (p. 13–14): 1.620 por treino/fine-tuning (523 por PEFT, 358 LoRA, 134 QLoRA), **548
    por abliteração**, 744 por *merge*, **8.647 (74,5%) por compressão** (quase todos quantizações
    de ULLMs existentes).
  - **Tabela 5 (p. 15), derivado × pai:** fine-tuning RSR 77,6% × 20,6%; abliteração 68,0% × 12,5%;
    *merge* 65,8% × 62,5%; compressão 68,1% × 71,9%. Ou seja: fine-tuning e abliteração **criam** a
    falha; *merge* e quantização **propagam** a falha que já existe no pai.
  - 33% (3.826) dos ULLMs do HF reaparecem em cinco outras plataformas (OpenCSG, ModelScope, Kaggle,
    John Snow Labs, WiseModel) (p. 19).
  - Mitigação proposta inclui "vetting" mais rígido em serviços de treino como o AutoTrain (p. 19).
- **Cuidado ao citar (importante para o E10 §2):** o modelo com "> 19 milhões de downloads" é o
  **Mistral-7B-v0.1, um modelo base** sem moderação, não um derivado obliterado (Tabela 4, p. 12;
  19.975.745). O top-10 de downloads é todo de modelos base ou instruct oficiais (Mistral, GPT-Neo,
  GPT-J, Zephyr). Para "derivado sem recusa com muitos downloads", citar a contagem (25 com > 1
  milhão) só depois de conferir quais são derivados.
- **Limitações (p. 20):** depende de metadados que o desenvolvedor pode omitir ou falsear; só HF;
  os números são **limite inferior**; recusa medida por casamento de strings (subestima recusas
  parafraseadas).
- **Para a nossa tese:** **motivação de campo central** para P1 (a propriedade não sobrevive à
  derivação, medido em campo, com classificação do *tipo* de derivação). Dá a **taxonomia de
  falhas por operação** (F1/F2 por fine-tuning, F3 por edição de pesos, e a classe "propaga do
  pai" de *merge*/quantização) e a base de comparação injeção × campo para P5. **Vizinho a
  diferenciar:** é detecção *ex post* por metadados; nós decidimos *ex ante* por comportamento,
  com o derivado retido.

### A2. 10a Labs — *Uncensored Open-weight Models: Redistribution as the Persistence Layer* · **Lido**
- **Ref.:** arXiv 2609.05241 v1, cs.AI, set/2026, relatório de empresa ("cite como 10a Labs
  (2026)"). Venue: **só arXiv** ✔; sem revisão por pares.
- **Lição:** depois de quantizado e espelhado, o derivado sem recusa **persiste mesmo que o
  original seja removido**; *takedown* no produtor não reduz a oferta.
- **Problema que define:** mapear a cadeia de suprimentos de modelos sem salvaguarda — produtores,
  redistribuidores, aplicações — e onde ela é observável e controlável.
- **Método:** busca por palavras-chave e *crawls* de produtores no HF (17.727 candidatos, jan/2024 a
  mar/2026) e no GitHub (44.705 candidatos); classificação por **um LLM (GPT-5)**.
- **Evidência principal:**
  - 3.471 originais sem censura, 8.164 redistribuições comprimidas, 547 *merges*; cada original é
    reempacotado **2,4×** em média; três contas fazem 52% das redistribuições (p. 1–3).
  - Produtores (≥ 1.055) e redistribuidores (≥ 1.011) quase não se sobrepõem (24%) (p. 2).
  - Uma ferramenta de abliteração de um comando (Heretic, nov/2025) levou a produção de ~89 para
    ~338 originais/mês e a 54% da produção nova no 1º tri de 2026 (p. 4).
  - 1.643 aplicações no GitHub; **25% explicitamente maliciosas**; 43% citam Ollama (p. 1, p. 5–6).
  - Removida uma conta redistribuidora, suas 936 cópias continuam circulando (p. 7).
- **Limitações (p. 8):** **classificador único sem verdade de campo humana; precisão e revocação
  não medidas**; 30,3% dos candidatos eram falso positivo; só HF + GitHub públicos; 21% dos
  originais sem sinal de técnica.
- **Para a nossa tese:** é o texto que **usa literalmente a moldura "supply chain"** para derivados
  sem recusa e mostra que o controle *ex post* falha porque a cadeia replica. Argumento direto para
  o **portão antes da liberação** (o que sai não volta). Também mostra a **barreira caindo**
  (abliteração de um comando), o que reforça o adversário F3. **Cuidado:** números sem validação;
  usar como corroboração de Lin et al., não como evidência principal.

### A3. Sokhansanj — *Uncensored AI in the Wild: Tracking Publicly Available and Locally Deployable LLMs* · **Resumo**
- **Ref.:** Future Internet 17(10):477, out/2025, DOI 10.3390/fi17100477 ✔ (OpenAlex/S2); correção
  publicada em Future Internet 18(1):49 (jan/2026) que, segundo o registro, altera a descrição do
  escopo sem mudar conclusões (a verificar no texto).
- **Lição:** modificados atendem pedidos inseguros **~4× mais** que os não modificados, e o efeito
  independe do tamanho.
- **Problema:** como modelos abertos são sistematicamente alterados e redistribuídos.
- **Método (resumo):** 8.608 repositórios de modelos modificados; 20 modificados avaliados em
  prompts inseguros (desinformação eleitoral, instrução criminosa, evasão regulatória).
- **Evidência (resumo):** conformidade média **19,2%** (não modificados) × **80,0%** (modificados);
  14B às vezes iguala ou supera 70B; top 5% dos provedores com > 60% dos downloads; mais da metade
  em GGUF. (A 10a Labs cita "74,1%" para este trabalho; a diferença pode vir da correção — conferir.)
- **Limitações:** não lidas (texto completo não acessado).
- **Para a nossa tese:** **segunda medição independente** de que a recusa some no derivado, com
  número simples para a introdução. Não citar números além do resumo até ler o texto.

### A4. Laufer, Oderinwale, Kleinberg — *Anatomy of a Machine Learning Ecosystem: 2 Million Models on Hugging Face* · **Parcial**
- **Ref.:** arXiv 2508.06811 v1, cs.SI, ago/2025. Venue (a verificar).
- **Lição:** o HF é uma rede de **árvores genealógicas profundas** (fine-tune, quantização,
  adaptador, *merge*), com até cinco ou mais gerações, e os traços "mutam" de forma dirigida.
- **Método:** 1,86 milhão de modelos; linhagem pelos *tags* `base_model:` declarados; similaridade de
  metadados e *model cards* entre parentes.
- **Evidência:** exemplo da família granite-3.1 com 147 modelos (p. 2–3); licenças derivam de
  restritivas para permissivas; *model cards* encurtam e viram *template* ao descer a árvore.
- **Limitações:** linhagem **auto-declarada**; não mede comportamento de segurança.
- **Para a nossa tese:** fundamenta "derivados de derivados" e a **profundidade da cadeia** (o
  recibo P2 precisa encadear: pai → filho → neto). A deriva de licença é o análogo documental da
  deriva de recusa.

### A5. Nguyen, Le, Babar — *Vulnerable Models in the AI Supply Chain: Adoption, Propagation, and Usage Patterns* · **Parcial**
- **Ref.:** arXiv 2610.12893, out/2026. Venue (a verificar).
- **Lição:** marcar um modelo como vulnerável no hub não impede que ele siga sendo usado e
  **derivado**; ninguém verifica proveniência ao consumir.
- **Método:** 16.977 modelos marcados pelo Protect AI InsightDB; rastreio em GitHub, pacotes,
  cadeias de fine-tuning e aplicações; padrões de código por CPG + mineração de subgrafos.
- **Evidência:** 22,1% dos marcados são referenciados em código; **419 derivados** de 136 modelos
  marcados, 43 deles também marcados; 57 marcados têm pai marcado (p. 7).
- **Limitações:** vulnerabilidade = artefato (serialização, *backdoor* de arquitetura), não recusa.
- **Para a nossa tese:** mesma dinâmica de A1–A2 para a **integridade do artefato**: o alerta *ex
  post* não contém a propagação. Reforça "o controle tem de estar no ponto de liberação".

---

## B. Integridade do artefato nos hubs (o que a cadeia já trata)

### B1. Zhao et al. — *Models Are Codes (MalHug)* · **Parcial**
- **Ref.:** ASE 2024 ✔ (comentário do arXiv 2409.09368).
- **Lição:** em hubs, modelo é código: formatos serializados e *scripts* de carga executam código.
- **Método:** taxonomia de formatos; pipeline estático + dinâmico (extração de *scripts*,
  desserialização, *taint analysis*, heurísticas), implantado na Ant Group.
- **Evidência:** > 705 mil modelos e 176 mil datasets monitorados; **91 modelos e 9 scripts
  maliciosos** (p. 1–2).
- **Limitações:** detecção por padrões; cobre código, não comportamento do modelo.
- **Para a nossa tese:** justifica a **ingestão só-tensor** (safetensors) na custódia e mostra que o
  vocabulário "poisoning on model hubs" já é aceito em venue de topo de SE.

### B2. Kellas et al. — *PickleBall* · **Parcial**
- **Ref.:** ACM CCS 2025 ✔ (comentário do arXiv; versão estendida).
- **Lição:** formatos seguros não resolveram a prática: 44,9% dos modelos populares do HF ainda usam
  pickle (p. 1).
- **Método:** análise estática das bibliotecas → política de carga por classe; imposição dinâmica
  como substituto do módulo pickle.
- **Evidência:** carrega 79,8% dos benignos e rejeita 100% dos maliciosos do conjunto; *scanners*
  avaliados têm FP e FN.
- **Para a nossa tese:** componente de higiene reaproveitável na fronteira de entrada; não é vizinho.

### B3. Liu et al. — *The Art of Hide and Seek* · **Resumo + intro**
- **Ref.:** arXiv 2508.19774 (cs.CR, ago/2025); venue (a verificar; há artefatos no Zenodo).
- **Lição:** *scanners* de pickle são contornáveis por construção.
- **Evidência:** 22 caminhos de carga em cinco *frameworks*, **19 não cobertos** por nenhum
  *scanner*; 133 *gadgets*, 89% de evasão contra o melhor *scanner* (p. 1).
- **Para a nossa tese:** argumento para **não depender de varredura** na fronteira; aceitar só tensores.

### B4. Casey, Santos, Mirakhorli — *A Large-Scale Exploit Instrumentation Study of AI/ML Supply Chain Attacks in HF Models* · **Parcial**
- **Ref.:** arXiv 2410.04490 (2024); venue (a verificar; o PDF traz metadado de *template* "icse 24").
- **Evidência (p. 7):** 59% dos modelos do HF em formatos inseguros; 96% dos arquivos inseguros
  testados foram exploráveis; o *scanner* do HF marcou só **38%** (5.137 de 13.466).
- **Para a nossa tese:** número de apoio para "a moderação do hub é parcial" (paralelo ao 16,5% de
  Lin et al. para recusa).

### B5. Wang et al. — *Demystifying LLM Supply Chain Vulnerabilities in the Wild* (antes *SoK: Understanding Vulnerabilities in the LLM Supply Chain*) · **Resumo**
- **Ref.:** arXiv 2502.12497 v2 (jul/2026); "Accepted by Internetware 2026" ✔ (comentário do arXiv).
- **Evidência:** 529 vulnerabilidades em 77 repositórios e 12 estágios; 50,3% na camada de aplicação
  e 42,7% na de integração de modelo; 45,6% de 63.243 serviços expostos afetados.
- **Para a nossa tese:** mostra que "cadeia de suprimentos de LLM" na literatura de SE/segurança é
  quase sempre **software** (bibliotecas, CVEs), não **comportamento** do modelo — a lacuna nossa.

### B6. Wang et al. — *LLM Supply Chain: A Research Agenda* · **Resumo**
- **Ref.:** ACM TOSEM (edição especial 2030 Software Engineering) ✔ (comentário do arXiv 2404.12736).
- **Para a nossa tese:** **definição citável** de cadeia de suprimentos de LLM em três camadas
  (infraestrutura, modelo de base, aplicação). Usar na introdução para ancorar a moldura.

### B7. Jiang et al. — *An Empirical Study of Pre-Trained Model Reuse in the HF Registry* · **Resumo**
- **Ref.:** ICSE 2023 ✔ (comentário do arXiv 2303.02552).
- **Lição:** reutilização de PTMs repete os problemas de pacotes de software; desafios são
  atributos faltantes, desempenho alegado ≠ real, e riscos do modelo.
- **Para a nossa tese:** antecessor clássico da moldura "reuso de modelos = cadeia de suprimentos";
  a discrepância "alegado × real" é o que o recibo atestado (P2) ataca para a recusa.

---

## C. Proveniência, assinatura e BOM: o que existe e o que não cobre derivados

### C1. OpenSSF Model Signing (OMS) + `sigstore/model-transparency` · especificação e software
- **Estado (consultado 2026-10-27):** `model-transparency` v1.1.1 (out/2025); issue **#586 "OMS model
  signature and other attestations"** aberta desde dez/2025.
- **O que cobre:** manifesto de *digests* por arquivo assinado (Sigstore); prova que o arquivo é o
  que o publicador liberou.
- **O que não cobre:** nada sobre comportamento; um derivado obliterado **assinado pelo seu autor**
  verifica normalmente.
- **Para a nossa tese:** o digest OMS do pai é a **referência custodiada**; o veredito do portão é
  atestação à parte (encaixa no que a #586 discute).

### C2. SLSA para ML e in-toto `eval-result` · especificações
- **Estado (consultado 2026-10-27):** slsa#978 *"Document how to do SLSA for ML and highlight gaps"*
  **aberta desde 2023-10-09** (última atividade out/2026); in-toto attestation PR **#575 "Add
  eval-result predicate"** aberto desde 2026-07-23, **não incorporado**.
- **Para a nossa tese:** fine-tuning = *build*; o recibo P2 pode ser um `eval-result` assinado
  dentro da CVM. A ausência de padrão é uma lacuna documentável.

### C3. AI-BOM (SPDX 3 AI, CycloneDX ML-BOM) + Erfan et al., *AIBOM Completeness in HF* · spec + **Parcial**
- **Ref.:** Erfan, Ryan, Rahman, arXiv 2607.17242 (jul/2026); venue (a verificar).
- **Evidência:** ~97,5 mil AIBOMs CycloneDX geradas de repositórios do HF: campos obrigatórios 100%
  presentes, mas **`safetyRiskAssessment` em só 9,76%** e `intendedUse`/`ethicalConsiderations` em
  0% (p. 7).
- **Para a nossa tese:** o BOM tem **campo** para risco de segurança, mas ele é **auto-declarado e
  quase sempre vazio**. Nosso recibo preenche esse campo com valor **medido e atestado**.

### C4. Google SAIF — *Securing the AI Software Supply Chain* (Chaudhuri et al., abr/2024) · **Parcial**
- **Ref.:** white paper do Google ✔ (PDF oficial).
- **Lição:** reaproveitar SLSA, Sigstore e BAB para IA; proveniência como controle central.
- **Evidência-chave:** o próprio texto diz que **não cobre "the quality of a model's behavior"**
  (p. 6); cita como ameaça copiar o modelo e fazer fine-tuning para respostas censuráveis (p. 34).
- **Para a nossa tese:** citação direta para "a cadeia de suprimentos de IA **declara fora de
  escopo** o comportamento" — a lacuna exata que P1 ocupa.

### C5. Spoczynski, Melara, Szyller (Intel Labs) — *Atlas: A Framework for ML Lifecycle Provenance & Transparency* · **Lido**
- **Ref.:** arXiv 2502.19567 v2 (mai/2025), cs.CR. Venue (a verificar; não há indicação no arXiv).
- **Lição:** proveniência de ponta a ponta do ciclo de ML é viável com TDX + C2PA + log de
  transparência, com custo baixo.
- **Problema:** detectar adulteração por **provedores de MLaaS, hubs e produtores** ao longo do
  ciclo (dados → treino → avaliação → implantação).
- **Método:** clientes de atestação em TEE coletam metadados de proveniência e de pipeline;
  manifestos C2PA; log que estende o Rekor; Merkle para ciclos não lineares.
- **Evidência:** estudo de caso de **fine-tuning de BERT em CPU**; *overhead* de treino **< 8%**;
  manifesto de 8 KB; verificação linear no tamanho (p. 6).
- **Limitações declaradas:** **usuários do modelo são confiáveis** (p. 3); **"dataset benignity,
  model quality and safety"** fora de escopo (p. 3); confidencialidade fora de escopo; só CPU;
  trabalho futuro inclui **"model guardrails against attacks targeting model behavior"** (p. 6).
- **Para a nossa tese:** **vizinho arquitetural mais próximo** (TEE + log + fine-tuning). A
  diferença é exatamente o que eles deixam como futuro: (i) adversário = **usuário** com o
  pipeline, (ii) propriedade **comportamental** (recusa), (iii) **liberação condicionada** (eles
  detectam adulteração, não retêm), (iv) confidencialidade dos pesos.

### C6. Duddu, Järvinen, Gunn, Asokan — *Laminator: Verifiable ML Property Cards using Hardware-assisted Attestations* · **Parcial**
- **Ref.:** ACM CODASPY 2025 ✔ (PDF e arXiv).
- **Lição:** *model cards* e *datasheets* viram verificáveis se a propriedade for medida dentro de
  TEE e o resultado for para o *user-data* do relatório de atestação.
- **Problema:** um provedor malicioso pode pôr informação falsa no *model card*.
- **Método:** SGX + Gramine; atestações de *proof of training*, acurácia, distribuição de dados e
  *inference cards* (entrada–modelo–saída).
- **Evidência:** *overhead* de 0,36–2,05% no treino (p. 8); em inferência o percentual sobe muito
  (39–3955%) porque a assinatura domina a inferência curta (p. 9).
- **Limitações:** modelos e datasets pequenos (CENSUS, UTKFACE, IMDB); só CPU; a propriedade é
  fixada pelo provedor — nada sobre recusa ou derivação adversarial.
- **Para a nossa tese:** **formato do recibo P2** (propriedade medida → hash no relatório). Vizinho
  a diferenciar: prova uma propriedade de **um** modelo; nós provamos uma **relação** pai → filho
  (recusa do filho ≥ pai − δ) sob adversário que treina.

### C7. Horwitz, Shul, Hoshen — *Unsupervised Model Tree Heritage Recovery* · já registrado em 05
- **Ref.:** ICLR 2025 ✔. Linhagem **inferida** dos pesos; complementa A4 (linhagem declarada).
- **Para a nossa tese:** fora da custódia, a linhagem só pode ser inferida; dentro, ela é registrada.

### C8. Nikolić, Baluta, Saxena — *Model Provenance Testing for LLMs* · **Resumo**
- **Ref.:** NeurIPS 2025 ✔ (OpenAlex, DOI 10.52202/085713-1146).
- **Evidência:** teste de hipóteses caixa-preta; 90–95% de precisão e 80–90% de revocação em
  > 600 modelos (30M–4B).
- **Para a nossa tese:** mostra o custo e o erro de **reconstruir** a linhagem sem custódia;
  argumento de que a custódia elimina esse erro para derivados nascidos na plataforma.

---

## D. Avaliação e guarda atestadas (vizinhos de P2)

### D1. Schnabl, Hugenroth, Marino, Beresford — *Attestable Audits: Verifiable AI Safety Benchmarks Using TEEs* · **Lido**
- **Ref.:** arXiv 2506.23706 v1. Comentário diz "ICML 2024 Workshop TAIG", mas o PDF usa o *template*
  ICML 2025 (Vancouver, PMLR 267): é o **workshop TAIG do ICML 2025** ✔ (não arquivado; ano no arXiv
  está errado).
- **Lição:** um *benchmark* de segurança pode rodar em TEE e sair com atestação que liga
  hash(modelo) + hash(código e dados da auditoria) → resultado, sem expor pesos nem dados.
- **Problema:** auditor e provedor não confiam um no outro; usuários não conseguem verificar que
  falam com um modelo auditado.
- **Método:** três protocolos (p. 3): **PREPARE** (quantização atestada M → Mq, publicada em log),
  **AUDIT** (código + dataset + Mq em *sandbox* na TEE, resultado agregado atestado) e **INFERENCE**
  (cada resposta leva atestação ligando modelo, prompt, saída e nota). Metas G1–G6 incluem
  *statelessness*. Protótipo em AWS Nitro, Llama-3.1-8B 4-bit, MMLU / XSum / ToxicChat.
- **Evidência:** viável; custo **21,7×** o de GPU e ~100× mais lento por ser CPU (p. 4); exfiltração
  por prompt fica como **lacuna residual** (p. 4).
- **Limitações (p. 5):** só CPU; modelo quantizado; confiança no fabricante; diz que o PREPARE
  "pode acomodar outros passos de pós-treino, p.ex. fine-tuning" — **não implementado**.
- **Para a nossa tese:** **vizinho mais próximo de P2**. O PREPARE é, na prática, uma **derivação
  atestada** (quantização) — precedente para "o derivado M' é aceito por ter nascido de M dentro da
  TEE". Diferenças: (i) eles atestam a nota de **um** modelo fixo; nós atestamos a **comparação** pai
  × filho com limiar e **retenção** do filho reprovado; (ii) o adversário deles é o provedor que
  esconde o modelo, o nosso é o usuário que **treina** o derivado contra o portão; (iii) não há
  bateria secreta adaptativa.

### D2. Jin et al. — *Proof-of-Guardrail in AI Agents and What (Not) to Trust from It* · **Parcial**
- **Ref.:** ICML 2026 Workshop AI4GOOD ✔ (comentário do arXiv 2603.05786).
- **Lição:** TEE prova que o **guardrail rodou**, não que ele **funciona**; o desenvolvedor pode
  enganar escolhendo um guardrail que ele mesmo quebra.
- **Para a nossa tese:** a mesma crítica vale para o recibo P2: atestar a execução do portão não
  atesta sua eficácia. Por isso a eficácia precisa vir da avaliação adaptativa (P4/E9), e o
  artigo deve dizer isso explicitamente.

### D3. Jin et al. — *AFTUNE: Auditable Fine-Tuning and Inference for Proprietary AI* · **Resumo**
- **Ref.:** arXiv 2603.07466 v2 (jul/2026); venue (a verificar). Números já em 02 §5.3.
- **Lição:** o cliente pode auditar se o fine-tuning na nuvem seguiu a configuração combinada,
  checando blocos sorteados em TEE.
- **Para a nossa tese:** prova o **processo** (integridade do treino), não a **propriedade** do
  resultado. Vizinho a diferenciar: AFTUNE protege o cliente do provedor; nós protegemos o
  ecossistema do cliente.

---

## E. Fine-tuning hospedado com moderação (a forma comercial do portão)

### E1. Thinking Machines — *A Safe Path to Open Weights* · blog
- **Ref.:** <https://thinkingmachines.ai/blog/a-safe-path-to-open-weights/>, 31/jul/2026, acesso
  2026-10-27. Sem autores nomeados.
- **Lição:** "refusal behavior cannot be treated as a durable safeguard for an open-weight release".
- **Conteúdo:** caminho em **cinco** degraus (acesso antecipado de defensores → disponibilidade geral
  monitorada → **fine-tuning para defensores verificados** → acesso *white-box* a pesquisadores →
  pesos abertos). APIs de fine-tuning (Tinker) ficam entre inferência e pesos: o provedor pode
  **monitorar, manter guardrails e revogar**. Não trata de TEE, nem de derivados em hubs.
  (Corrige 05 §4, que descrevia quatro degraus.)
- **Para a nossa tese:** legitimação de indústria para "custódia + fine-tuning + revogação" como
  degrau intermediário; o nosso acréscimo é **verificabilidade por terceiros** e o portão de saída.

### E2. Microsoft Foundry — *Safety evaluation for fine-tuning (preview)* · documentação
- **Ref.:** <https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/fine-tuning-safety-evaluation>,
  ms.date 2026-07-31, acesso 2026-10-27.
- **Conteúdo:** (i) dados avaliados antes do treino; job falha acima de um limiar por categoria;
  (ii) **depois do treino e antes da implantação**, o modelo é avaliado por conversas simuladas; se
  passar do limiar, "this model is unable to be deployed"; (iii) **só o veredito binário
  (implantável ou não) é persistido**; limiares fixos, não configuráveis pelo cliente.
- **Para a nossa tese:** **o precedente industrial mais próximo do portão de liberação de
  derivados** (avaliação do derivado + bloqueio da implantação). Diferenças: modelo **fechado**
  (GPT-4o); **sem atestação nem recibo** verificável por terceiros; sem comparação com o pai; sem
  modelo de adversário publicado. Mostra que o portão **é praticado**, o que ajuda a
  justificar o problema, e que **falta a verificabilidade** (P2). (A documentação equivalente da
  OpenAI não foi localizada nesta rodada.)

### E3. Pelrine et al. — *Exploiting Novel GPT-4 APIs* · **Parcial**
- **Ref.:** arXiv 2312.14302 v2 (FAR AI, 2023/24); venue (a verificar).
- **Evidência:** datasets com exemplos nocivos **não foram barrados** pelo filtro de moderação do
  fine-tuning; ~100 exemplos benignos degradaram salvaguardas (p. 1).
- **Para a nossa tese:** a moderação dos **dados** não basta; o portão tem de julgar o **derivado**.

### E4. Halawi et al. — *Covert Malicious Finetuning* · **Parcial** (já em 05)
- **Ref.:** ICML 2024 ✔02. Cada exemplo inócuo; modelo atende pedidos codificados 99% das vezes e
  escapa de inspeção de dados, avaliações e classificadores de entrada/saída.
- **Para a nossa tese:** o adversário F4 que a bateria precisa cobrir (não só texto claro).

### E5. Egler, Schulman, Carlini — *Detecting Adversarial Fine-tuning with Auditing Agents* · **Parcial** (já em 05)
- **Ref.:** arXiv 2510.16255 (cs.CR, out/2025); venue (a verificar).
- **Evidência:** agente com acesso a dados + modelo pré + modelo pós; 8 ataques, 5 benignos, > 1.400
  auditorias; **56,2% de detecção a 1% de FPR**; pega CMFT cifrado (p. 1–2).
- **Para a nossa tese:** linha de base de detector; **supõe exatamente o acesso que a custódia
  dá** (pré, pós e dados). Fine-tuning benigno com degradação sutil continua difícil — nosso F1.

---

## F. Custódia e execução confidencial

### F1. Anthropic + Pattern Labs — *Confidential Inference Systems: Design principles and security risks* v1.0 · **Parcial**
- **Ref.:** white paper, jun/2025 ✔ (PDF oficial).
- **Lição:** confidencialidade do modelo exige TEE, KMS que só libera a chave a carga atestada, e
  **build** do enclave que nenhuma parte controla sozinha.
- **Evidência-chave:** escopo **só inferência**; treino e fine-tuning confidenciais declarados fora
  de escopo (p. 6); "confidential training and provisioning" citado como caminho para SL4/SL5 sem
  desenho (p. 21); ambiente de build é "extremely fruitful target" de ataque de cadeia (p. 22).
- **Para a nossa tese:** **componente reaproveitável** (KMS condicionado à atestação, build
  reproduzível) e **lacuna declarada**: fine-tuning sob custódia confidencial é deixado de fora por
  quem desenhou o padrão de inferência.

### F2. Frikha et al. — *ObfuscaTune* · **Resumo + intro**
- **Ref.:** AAAI 2025 Workshop PPAI ✔ (arXiv).
- **Problema:** fine-tuning e inferência de LLM **proprietário** sobre dados **privados** de outro
  dono, em nuvem de terceiros, com sigilo de ambos.
- **Método/evidência:** ofuscação por matrizes aleatórias + ~5% dos parâmetros na TEE; GPT-2, 4
  datasets; sem perda de utilidade.
- **Para a nossa tese:** mostra o **outro uso** de TEE em fine-tuning (sigilo de IP e dados). Nosso
  objeto é diferente: o **comportamento de segurança** do derivado. Citar como vizinho a diferenciar.

### F3. Mohanty et al. — *DistilLock* · **Resumo + intro**
- **Ref.:** NeurIPS 2025 **Workshop Lock-LLM** ✔ (rodapé do PDF; resolve a dúvida de 05 §8).
- **Problema:** fine-tuning na borda sem entregar o modelo proprietário: professor na TEE do
  dispositivo, pesos ofuscados em acelerador não confiável, contra destilação não autorizada.
- **Para a nossa tese:** idem F2 — sigilo do pai, não recusa do filho. Também mostra que "o usuário
  tem o hardware mas não os pesos" é um modelo de adversário aceito.

### F4. Rinberg, Karvonen, Hoover, Reuter, Warr — *Verifying LLM Inference to Detect Model Weight Exfiltration* · **Parcial**
- **Ref.:** arXiv 2511.02620 v3 (mar/2026), cs.CR; venue (a verificar).
- **Lição:** com a saída legítima como único canal, exfiltração de pesos vira um **jogo de
  segurança** e a verificação da aleatoriedade legítima limita a capacidade do canal.
- **Método:** Experimento 1 (jogo de exfiltração, p. 9); servidor de verificação isolado reexecuta
  amostras aleatórias com semente fixa; estimadores Token-DiFR.
- **Evidência:** em Qwen3-30B-A3B, informação exfiltrável **< 0,5%** com FPR baixo (o resumo diz
  < 10⁻², as contribuições dizem 10⁻² % — inconsistência do próprio texto); ≥ 200× mais lento para o
  atacante.
- **Hipóteses (p. 10):** sem canais laterais; verificador honesto; *log* confiável; amostragem
  privada; toda saída pareada com uma entrada. Não cobre o modelo revelando os próprios pesos
  como comportamento pretendido (p. 1).
- **Para a nossa tese:** **molde formal para P3** (contenção de exportação), que o E10 deixou como
  limitação/trabalho futuro. Citar ao declarar a limitação: "o canal de saída do job é um canal de
  exfiltração; Rinberg et al. dão o enquadramento para trabalho futuro".

### F5. Custo de execução confidencial (viabilidade da CVM com GPU)
- **Chrapek, Copik, Mettaz, Hoefler** — *Confidential LLM Inference: Performance and Cost Across CPU
  and GPU TEEs* · **Resumo** · **IISWC 2025** ✔ (OpenAlex). CPU TEE < 10% de vazão e < 20% de
  latência; H100 CC 4–8%.
- **Wang, Waqas, Smith (Mozilla)** — H100 sob TDX · **Resumo** · arXiv 2607.19353 (mai/2026). TTFT
  +21,8% (Mistral-7B) e +27,8% (Qwen3-30B-A3B); vazão −17,7% e −21,1%; saturação mais cedo.
  Independente de fornecedor.
- **Asad, Grunseid (Confidential.ai)** — Blackwell · **Parcial** · arXiv 2608.26575 v2. Inferência
  bem configurada 1–3%; *stacks* padrão 30–40%; **treino em 8 GPUs 10–13%**, todo no coletivo
  cifrado. **Conflito de interesse** (empresa do ramo).
- **Lee et al.** — GPU TEE em DDP · **Resumo** · arXiv 2501.11771 v3. 4 GPUs: 8,68× por iteração em
  média, até 41,6× (GPT-2-XL), pela cifra no *all-reduce*.
- **Zhu et al. (Phala)** — Hopper · **Resumo** · arXiv 2409.03992. < 7% em consultas típicas.
- **Para a nossa tese:** fine-tuning sob custódia é **viável em uma GPU** e caro em multi-GPU
  antigas; o portão (inferência) custa pouco. Resultados divergem por fornecedor — citar o
  independente (Wang/Mozilla) ao lado dos de fornecedor.

---

## G. Fontes que não são PDF (link e data de acesso: 2026-10-27)

| Fonte | Link |
|---|---|
| sigstore/model-transparency (v1.1.1) | <https://github.com/sigstore/model-transparency> |
| OMS spec | <https://github.com/ossf/model-signing-spec> |
| model-transparency #586 (OMS + outras atestações) | <https://github.com/sigstore/model-transparency/issues/586> |
| SLSA #978 (SLSA para ML) | <https://github.com/slsa-framework/slsa/issues/978> |
| in-toto attestation PR #575 (`eval-result`) | <https://github.com/in-toto/attestation/pull/575> |
| SPDX 3.0.1 AI | <https://spdx.github.io/spdx-spec/v3.0.1/model/AI/AI/> |
| CycloneDX / ECMA-424 | <https://ecma-international.org/publications-and-standards/standards/ecma-424/> |
| CoSAI AIMM | <https://github.com/cosai-oasis/ws1-supply-chain/blob/main/whitepapers/aimm-artifact-integrity-maturity-model.md> |
| Thinking Machines, *A Safe Path to Open Weights* | <https://thinkingmachines.ai/blog/a-safe-path-to-open-weights/> |
| Microsoft Foundry, *Safety evaluation for fine-tuning* | <https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/fine-tuning-safety-evaluation> |
| Sokhansanj (texto completo, navegador) | <https://doi.org/10.3390/fi17100477> |

---

## Síntese

### (a) Evidência de que derivados sem recusa circulam na cadeia
- **Três medições independentes** apontam na mesma direção: Lin et al. (11.598 ULLMs, validação
  por amostragem, p. 2, p. 10), Sokhansanj (conformidade 19,2% → 80,0%, resumo) e 10a Labs (3.471
  originais + 8.164 cópias, sem validação). Mesmo o mais fraco metodologicamente corrobora o mais
  forte.
- **A falha nasce em operações específicas e é herdada:** fine-tuning e abliteração **criam** a
  perda de recusa; *merge* e quantização **propagam** (Lin et al., Tabela 5, p. 15). Isso dá a
  classe de falha "herdada do pai" que um portão por derivado precisa tratar.
- **O controle *ex post* falha:** HF marca 16,5% dos ULLMs (Lin, p. 11) e 38% dos arquivos
  inseguros (Casey, p. 7); um terço dos ULLMs já foi espelhado em outras plataformas (Lin, p. 19);
  cópias persistem após remoção do original (10a Labs, p. 7); modelos marcados continuam sendo
  usados e derivados (Nguyen, p. 7).
- **A barreira está caindo:** abliteração de um comando quadruplicou a produção mensal (10a Labs,
  p. 4); 548 ULLMs por abliteração já em 2025 (Lin, p. 14).
- **Correção necessária no E10 §2:** "um com > 19 milhões de downloads" é o **Mistral-7B-v0.1
  (modelo base)**, não um derivado (Lin, Tabela 4, p. 12).

### (b) O que já existe de proveniência/atestação e o que não cobre derivados
- **Integridade do artefato** (OMS, Sigstore, SLSA, C2PA, safetensors/PickleBall): resolve "o
  arquivo é o que foi assinado" e "carregar não executa código". **Não diz nada sobre recusa**; um
  derivado obliterado assinado verifica.
- **Linhagem** (AI-BOM, *tags* `base_model`, MoTHer, testes de proveniência): declarada ou
  inferida; o campo `safetyRiskAssessment` existe mas está em 9,76% das AIBOMs e é auto-declarado
  (Erfan, p. 7).
- **Os próprios padrões declaram o comportamento fora de escopo:** Google SAIF (p. 6) e Atlas
  ("model quality and safety", p. 3; "guardrails against attacks targeting model behavior" como
  futuro, p. 6). SLSA para ML está aberto desde 2023; `eval-result` do in-toto não foi incorporado.
- **Atestação de propriedade** (Laminator, Attestable Audits, Proof-of-Guardrail): mede e atesta
  propriedades de **um modelo fixo** ou a **execução** de um guardrail; o adversário é o provedor
  que esconde algo, não o usuário que treina o derivado contra a avaliação. O PREPARE de Attestable
  Audits atesta uma **derivação benigna** (quantização) e cita fine-tuning só como extensão.
- **Integridade do processo** (AFTUNE, VeriLoRA, Atlas): prova que o treino seguiu a receita, não
  que o resultado recusa.

### (c) Onde a custódia é nova
- **Portão comportamental em custódia, com recibo.** O único portão de derivados praticado em
  produção que achamos (Microsoft Foundry) é de modelo **fechado** e **sem verificabilidade**
  (só persiste "implantável / não implantável"). Os trabalhos verificáveis (Attestable Audits,
  Laminator, Atlas) não retêm nem comparam derivados. A combinação **pesos abertos + derivado retido
  na CVM + comparação com a referência custodiada do pai + recibo atestado + adversário que
  controla o treino** não apareceu em nenhum trabalho lido (isso não prova novidade; ver E10).
- **A custódia satisfaz as hipóteses que os detectores deixam abertas:** referência autêntica do
  pai (que Hurtado admite ser forjável), acesso pré e pós (que Egler supõe) e derivado ainda não
  liberado (o que a cadeia de A1–A2 mostra ser irreversível depois).
- **Lacunas declaradas por terceiros que a custódia ocupa:** fine-tuning confidencial fora do
  escopo de Anthropic/Pattern Labs (p. 6); comportamento fora do escopo de Google e Atlas;
  fine-tuning como extensão não feita do PREPARE.
- **O que a custódia não resolve (dizer no artigo):** atestar o portão ≠ portão eficaz
  (Proof-of-Guardrail); exfiltração pelo canal de saída (Rinberg; P3 fora); destilação por
  consultas; ataques físicos à TEE (02 §4.4).

---

## Leitura recomendada para o autor

**Lin et al., *Consiglieres in the Shadow* (arXiv 2508.12622), §4.1–§4.2 e Tabela 5 (p. 11–15),
mais a Discussão (p. 19–20).**

Por quê:
1. É o único trabalho que **mede a perda de recusa por tipo de aresta da cadeia** (derivado × pai):
   fine-tuning e abliteração criam a falha, *merge* e quantização a propagam. Isso é a motivação de
   cadeia de suprimentos em forma de dado, e já dá a taxonomia de falhas e a base de campo para P5.
2. Tem **validação** (84 de 84 amostrados confirmados; métricas de detecção) — ao contrário da
   10a Labs, que não mede precisão nem revocação.
3. Traz os números de **moderação reativa** (16,5% marcados) e **espalhamento entre plataformas**
   (33%), que sustentam "controlar no ponto de liberação, não depois".
4. Lido junto com ele, para evitar um erro de citação: a Tabela 4 mostra que o "19 milhões" é um
   modelo base.

**Complemento curto:** 10a Labs (9 páginas) para a palavra "supply chain" e o argumento de
persistência (p. 7); e a frase de escopo do Google SAIF (p. 6) para a lacuna em uma linha.
