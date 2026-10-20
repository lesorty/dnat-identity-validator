# Transparência de execução de LLMs: levantamento de literatura

**Data:** 2026-10-20 · **Natureza:** agregação de dados para decidir depois. **Nada aqui é decisão.**

**Linha de pesquisa.** Usar um ambiente confidencial para:
- permitir **fine-tuning de modelos sem obliteração**, isto é, sem remover guardrails
  (*abliteration*) e sem exportar pesos;
- garantir **execução segura e verificável**.

Ferramenta candidata: [sigstore/model-transparency](https://github.com/sigstore/model-transparency).

**Método.** Primeiro li o repositório: caso U1 do JUIZ_IA, D3, E2b, E2c N1 e §9 do artigo.
Depois fiz quatro levantamentos em paralelo:

- (a) assinatura e proveniência de modelos;
- (b) computação confidencial para LLMs;
- (c) execução e auditoria verificáveis;
- (d) fine-tuning sem remoção de guardrails.

As referências foram abertas na fonte. As que mais pesam foram conferidas de novo e levam ✔. O
orçamento de buscas acabou no meio do trabalho; as lacunas de cobertura estão no §10.

**Convenções.**
- **Tier:** **topo**, **PR** (outro peer-reviewed), **WS** (workshop), **Pre** (preprint), **Rel** (relatório, blog, documentação).
- **(a verificar)**: não confirmado na fonte.

---

## 1. Onde estamos (o que o repositório já tem)

### 1.1 O caso U1 (JUIZ §2, sugestão do professor)

- **Pesos = ativo**, como um dataset. O script do usuário é a aplicação julgada. A arquitetura é
  pública; os pesos ficam guardados no DNAT e são liberados só para CVM atestada.
- **O modelo nunca sai do DNAT** (Steylor, 2026-10-17). Executar, ajustar ou consultar só
  acontece lá dentro, e os modelos derivados também ficam.
- **Legítimo:** inferência, fine-tuning, configuração. **Barrado:** remoção de guardrails
  (abliteration, fine-tuning para tirar recusas) e exportação de pesos.
- **Fine-tuning legítimo e abliteration podem ter o mesmo código.** O dano está nos dados de
  treino ou no resultado, então ler o código não basta (P5).
- **Abordagem A4 (para o futuro):** avaliar o modelo derivado com uma bateria de recusa
  comparada ao original.
- **Destilação** é vazamento. Mitigações candidatas: limite de consultas, Juiz ou portão contra
  geração de dados de treino em massa, marca d'água. A eficácia está a verificar, e elas podem
  tornar o caso inviável (Steylor, 2026-10-17).
- Modelos grandes exigem **GPU confidencial (a verificar)**.

### 1.2 O que já temos de mecanismo, reaproveitável

| Mecanismo | Onde | Como serve aqui |
|---|---|---|
| Build atestado com proveniência in-toto/SLSA; chave gerada **dentro** da CVM e vinculada à atestação por `REPORT_DATA = hash(chave ‖ declaração)` | E2b.4 | O mesmo padrão assina o **modelo derivado** e o recibo do fine-tuning |
| Reprodução por N ≥ 2 builders; log de transparência estilo Sigstore/Rekor (direção 3 do LADC) | E2b.4, brainstorm 01 | Analogia direta com o log de modelos e de execuções |
| CVM de uso único, container sem rede, a CVM só fala com o DNAT | D4, E2c §2 | Ambiente do fine-tuning e da avaliação |
| Recibo `(H(dataset), H(fonte), H(artefato), medição, H(saída))` | brainstorm 01, direção 1 | Vira recibo de fine-tuning (base, adaptador, derivado) |
| Juiz como app whitelisted; Juiz na CVM com **modelo aberto medido** (hash dos pesos na medição) | D2, JUIZ §1 | O Juiz de U1 roda localmente, sem API externa |
| Serviço de modelo dentro da CVM como alternativa à rede (N1-c) | E2c §5 | Inferência confinada |

### 1.3 Escopo atual

- No artigo do DSN, U1 entra **só como motivação** (D3), na discussão: "fine-tuning and guardrail
  removal can share the same code, so judging the resulting model… becomes necessary".
- Esta linha é **pesquisa futura**, que este levantamento começa a mapear.

---

## 2. O problema em quatro perguntas

Um terceiro (dono do modelo, regulador, usuário) quer evidência verificável de quatro coisas:

| # | Pergunta | Mecanismos candidatos | Seção |
|---|---|---|---|
| Q1 | **Qual modelo** rodou ou respondeu? | Assinatura de modelo (OMS/Sigstore), hash dos pesos na atestação, TOPLOC/SVIP, testes estatísticos | §3, §5 |
| Q2 | O **fine-tuning seguiu a política** (receita, dados, sem edição de pesos)? | Receita atestada em TEE, recibo com checkpoints, PoL/ZK (caro), auditoria de dados | §5, §6 |
| Q3 | A **avaliação de segurança** foi feita sobre **aquele** modelo, e ele passou? | Auditorias atestadas (Attestable Audits), cadeia base → derivado → avaliação | §5, §6 |
| Q4 | O modelo **não saiu** (pesos, destilação)? | Chave liberada só para medição aprovada; inferência confinada; anti-destilação | §4, §6 |

---

## 3. sigstore/model-transparency e a cadeia de suprimentos de modelos

### 3.1 Ficha técnica do model-transparency (2026-10-20)

| Campo | Situação |
|---|---|
| **O que é** | Biblioteca e CLI Python para **assinar e verificar modelos** (`pip install model-signing`, módulo `model_signing`). Apache-2.0, 249 estrelas ✔. É a implementação de referência da **OpenSSF Model Signing (OMS) spec v1.0** ([ossf/model-signing-spec](https://github.com/ossf/model-signing-spec)), do OpenSSF AI/ML WG (Google, NVIDIA, HiddenLayer) |
| **Versão** | v1.0.0 em 04/04/2025 (API e CLI estáveis); **última release v1.1.1 em 10/10/2025** ✔. O `main` segue ativo (commit em 19/10/2026 ✔) e já tem correções de segurança **não lançadas**: *symlinks*, arquivos vazios em *shards*, EKU de *code signing* não exigido, configuração vazando entre modelos. O PR de *path traversal* `../` (#647) está aberto |
| **Formato** | Sigstore bundle v0.3 → envelope DSSE → in-toto Statement v1, com `predicateType` `https://model_signing/signature/v1.0`. Um **subject** com o **root digest** SHA-256 sobre os digests ordenados; `predicate.resources` tem um digest por arquivo ou por *shard* |
| **Modelos grandes** | SHA-256 por padrão; BLAKE2b e BLAKE3 opcionais. Serialização por *shards* (1 GB) **só pela API**. A verificação re-hasheia o diretório inteiro. Hash em GPU (#201) e re-hash incremental (#160/#562) estão abertos |
| **Métodos de assinatura** | `sigstore` (Fulcio + Rekor, com OIDC ou identidade de *workload*, inclusive instância privada via `--trust-config`) · `key` (EC P-256/384/521 em PEM, **funciona offline**) · `certificate` (cadeia X.509; `--san-uri` para fixar identidade SPIFFE só no `main`) · PKCS#11/HSM. Abertos: KMS de nuvem (#597), TSA RFC 3161 (#620), PQC (#595) |
| **O que garante** | Que os bytes de cada arquivo não mudaram desde a assinatura e que a assinatura veio da identidade ou chave declarada. No modo Sigstore, o evento fica no Rekor e é auditável |
| **O que NÃO garante** | Nada sobre dados de treino, processo, ambiente, segurança ou comportamento; não dá confidencialidade nem controle de acesso. A própria spec tem uma seção "What Model Signing is NOT" |
| **Adoção (segunda rodada, out/2026)** | **NVIDIA NGC** assina todos os modelos publicados desde a primavera de 2025: relatório CoSAI e o mantenedor Mihai Maruseac no [podcast OpenSSF de 14/07/2026](https://openssf.org/podcast/2026/07/14/whats-in-the-soss-podcast-65-s3e17-signing-the-future-securing-ai-and-ml-artifacts-with-mihai-maruseac/). **Kaggle**: o cliente `kagglehub` tem `model_upload(..., sigstore=True)` desde jan/2025 (PR #211, extra `kagglehub[signing]`), com token OIDC da Kaggle e Sigstore de produção, mas é **opcional e desligado por padrão** (v1.0.2, jun/2026); se o site mostra selo de verificação **(a verificar)**. **Hugging Face: ainda não assina nem verifica com OMS** ([página de segurança do Hub](https://huggingface.co/docs/hub/security); Nota 1 da issue #587). Quem assina são os publicadores, por exemplo IBM Granite com `model.sig` por adaptador. Uma issue que afirma o contrário (huggingface_hub#4021) não tem respaldo. Atlas CLI (Intel) emite C2PA compatível |
| **Roadmap observável** | O código "SLSA for ML" foi **removido** em dez/2025 (#579): o repositório trata só de assinatura. **#548** (aberta desde 13/10/2025 ✔): "Integrate with Atlas to generate signatures and provenance on **trusted enclaves**", sem código ainda. **#586** (aberta ✔): não expandir o predicado OMS; proveniência, SBOM, *model card* e resultados de teste vão em **atestações separadas** com subject = root digest. **#588**: a assinatura do filho é independente; o pai entra no AI-SBOM (SPDX `DESCENDANT_OF` / CycloneDX `pedigree`) |

**Riscos de engenharia:**
- um ano sem *release*, com correções de segurança só no `main`;
- divergência entre spec e implementação em arquivos vazios por *shard* (a spec §6.3.2 manda
  omitir; o `main` emite *shard* vazio).

Fixar o commit e rodar a **suíte de conformidade OMS** (79 testes). Ainda não há convenção para
LoRA e *merges* (vários pais).

### 3.2 Especificações e ecossistema

| Referência | Tipo | O que traz | Para o DNAT |
|---|---|---|---|
| [CoSAI WS1: Signing ML Artifacts](https://github.com/cosai-oasis/ws1-supply-chain/blob/main/whitepapers/signing-ml-artifacts.md) | Rel (set/2025) | *Claimant model*: claims de integridade, proveniência e propriedade, em três níveis | O veredito do Juiz vira um **claim de propriedade** |
| [CoSAI AIMM](https://github.com/cosai-oasis/ws1-supply-chain/blob/main/whitepapers/aimm-artifact-integrity-maturity-model.md) | Rel (set/2026) | L1 integridade · L2 linhagem (filho referencia o hash do pai) · **L3 atestações estruturadas (modelo, dados, processo, infraestrutura com relatórios TDX/SEV-SNP) + *admission gating* por *policy engine*** | **Mapeia o DNAT quase 1:1**: Juiz = *policy engine*, CVM = atestação de infraestrutura |
| [Google: Securing the AI Software Supply Chain](https://research.google/pubs/securing-the-ai-software-supply-chain/) | Rel (2024) | SLSA, BAB e Sigstore adaptados ao ciclo de IA | "Fine-tuning é um build" |
| [Atlas](https://arxiv.org/abs/2502.19567) + [atlas-cli](https://github.com/IntelLabs/atlas-cli) (Intel Labs) | Pre (2025) + software v0.3.0 | Cliente de atestação em **TDX** assina metadados C2PA com chave gerada no TEE; log que estende o Rekor; caso de fine-tuning BERT com < 8% de *overhead*, **só CPU**. Não detalha como a chave se vincula ao *quote* | O vizinho mais próximo; alvo da #548; usa C2PA em vez de in-toto |
| [OpenSSF SIG E2E Model Provenance](https://github.com/ossf/ai-ml-security/issues/40) | WG (dez/2025) | Proveniência agnóstica de pipeline sobre Atlas e TDX; prevê atestar o ambiente de computação. Há também a SIG GPU-Based Model Integrity | **Espaço para contribuir:** o caso "fine-tuning atestado sem abliteration" não aparece lá |
| [Laminator](https://arxiv.org/abs/2406.17548) (Duddu et al.) | CODASPY 2025 · PR | SGX + Gramine atesta *proof of training*, acurácia, distribuição e *fairness*; hashes no *user-data* do relatório; < 2,1% de *overhead*; **só CPU** | **Mesmo padrão `REPORT_DATA` do nosso builder**; modelo do *property card* do Juiz |
| [Attestable Builds](https://arxiv.org/abs/2505.02521) (Hugenroth et al.) | CCS 2025 (a verificar) · topo | Build em TEE com *sandbox* liga o binário ao commit da fonte; 14% de *overhead*, 42 s de partida | Valida o builder atestado; modelo para "fine-tuning atestado" |
| [in-toto SCAI predicate v0.3](https://github.com/in-toto/attestation/blob/main/spec/predicates/scai.md) | Spec | Atributos do ambiente (execução em TEE) com relatório de hardware como evidência | Envelope para relatório SEV-SNP/TDX/GPU |
| [SPDX 3.0.1 AI/Dataset](https://spdx.github.io/spdx-spec/v3.0.1/model/AI/AI/) · [ECMA-424 / CycloneDX 1.7](https://ecma-international.org/publications-and-standards/standards/ecma-424/) | Spec | `AIPackage` (treino, hiperparâmetros, `safetyRiskAssessment`) · ML-BOM e `pedigree` | AI-SBOM do derivado com o pai referenciado |
| [SCITT Architecture (RFC 9943)](https://datatracker.ietf.org/doc/draft-ietf-scitt-architecture/) | IETF (jun/2026) | *Signed statements* COSE, serviço de transparência com política de registro, recibos verificáveis offline | Alternativa ou complemento ao Rekor para o ledger |
| [Rekor v2 / rekor-tiles](https://github.com/sigstore/rekor-tiles) | Software (v2.3.0, jun/2026) | Backend POSIX: **log privado** viável | Log do DNAT sem expor atividade |
| [GitHub artifact attestations](https://github.blog/changelog/2024-06-25-artifact-attestations-is-generally-available/) | Produto (GA jun/2024) | Atestação de build sobre Sigstore + controlador de admissão | Padrão de mercado "build atestado + admissão" |
| [Tinfoil: verificação](https://docs.tinfoil.sh/verification/verification-in-tinfoil) · [measure-image-action](https://github.com/tinfoilsh/measure-image-action) | Doc de empresa | O CI gera as medidas da CVM e publica no Sigstore; **pesos fixados por hash (raiz dm-verity) na configuração medida**; chave TLS vinculada ao relatório | **Receita industrial pronta** de "pesos na medição + log Sigstore" |
| [Apple PCC](https://security.apple.com/blog/private-cloud-compute/) + [pesquisa verificável](https://security.apple.com/blog/pcc-security-research/) | Rel (2024) | Medições num log *append-only*; o cliente só cifra para nós com *release* no log; VRE para inspecionar imagens; *bounty* de até US$ 1M | Analogia: liberar o modelo só para imagens registradas |

### 3.2.1 Não há predicado padrão para treino ou fine-tuning (segunda rodada)

- **Catálogo in-toto** ([`spec/predicates`](https://github.com/in-toto/attestation/tree/main/spec/predicates),
  conferido em 2026-10-20): cyclonedx, link, provenance (SLSA), reference, release, runtime-trace,
  scai, spdx, spdx2, spdx3, svr, test-result, vsa, vuln. **Nenhum é específico de ML.**
- **PRs abertos relacionados:**
  - #575 **`eval-result`**, para resultados de avaliação de IA/ML (jul/2026). **Candidato
    natural para o veredito do Juiz.**
  - #587 PRML, critérios de avaliação pré-registrados.
  - #592 *Computation Receipt*.
  - Vários predicados de agentes.

  **Nenhum cobre treino.**
- **SLSA:** não há `buildType` oficial para ML. A
  [slsa#978](https://github.com/slsa-framework/slsa/issues/978) está aberta desde 2023. O
  model-transparency removeu as demos `slsa_for_models` na série 1.x.
- **[IETF draft-sharif-ai-model-lifecycle-attestation-01](https://datatracker.ietf.org/doc/draft-sharif-ai-model-lifecycle-attestation/)**
  (ago/2026): *draft* individual, sem grupo de trabalho, JSON próprio e não in-toto.
- **Composição sugerida para o DNAT:**
  - SLSA Provenance v1 com `buildType` próprio, com o digest OMS do base e os digests dos
    datasets em `resolvedDependencies`;
  - SCAI para a evidência de TEE (hash do relatório SNP e *claims* da GPU);
  - SPDX 3 ou CycloneDX para a linhagem;
  - OMS para os pesos do derivado;
  - `eval-result` (quando sair) para o veredito.

  Guardar em **arquivos ou subdiretórios separados**, não num único `claims.jsonl` (debate da
  #587).

### 3.3 Ataques à cadeia de suprimentos de modelos (ingestão)

| Referência | Venue · tier | Achado |
|---|---|---|
| [Models Are Codes (MalHug)](https://arxiv.org/abs/2409.09368) (Zhao et al.) | ASE 2024 · topo (SE) | 705 mil modelos monitorados: 91 modelos e 9 scripts maliciosos |
| [PickleBall](https://arxiv.org/abs/2508.15987) (Kellas et al.) | CCS 2025 · topo | Política de carga derivada da biblioteca: aceita 79,8% dos benignos e rejeita 100% dos maliciosos; **os scanners avaliados falharam** |
| [The Art of Hide and Seek](https://arxiv.org/abs/2508.19774) (Liu et al.) | 2025 · Pre | 19 de 22 caminhos de carga não são cobertos por nenhum scanner; até 89% de evasão |
| [Exploit instrumentation study on HF](https://arxiv.org/abs/2410.04490) (Casey et al.) | 2024 · Pre | Serialização insegura disseminada no Hugging Face |
| JFrog ([2024](https://jfrog.com/blog/data-scientists-targeted-by-malicious-hugging-face-ml-models-with-silent-backdoor/), [zero-days no PickleScan](https://jfrog.com/blog/unveiling-3-zero-day-vulnerabilities-in-picklescan/)), [ReversingLabs nullifAI](https://www.reversinglabs.com/blog/rl-identifies-malware-ml-model-hosted-on-hugging-face), [Protect AI + HF](https://huggingface.co/blog/pai-6-month), [HiddenLayer Silent Sabotage](https://hiddenlayer.com/innovation-hub/silent-sabotage/) | 2024–25 · Rel | *Reverse shells* em modelos públicos; burlas repetidas do picklescan; 352 mil problemas em 51,7 mil modelos; até o bot de conversão para safetensors podia ser sequestrado |
| [REEF](https://arxiv.org/abs/2410.14273) · [Independence Tests](https://arxiv.org/abs/2502.12292) · [Model Provenance Testing](https://arxiv.org/abs/2502.00706) | 2024–25 · Pre (REEF ICLR'25, a verificar) | Detectam derivação após fine-tuning, poda ou *merge*, por pesos e ativações (REEF, testes de independência) ou em caixa-preta (90–95% de precisão) |

**Consenso:** pickle é inseguro por construção e scanners são contornáveis. Controles robustos:
**safetensors**, *loaders* com *allowlist* e carregamento em *sandbox*.

### 3.4 Como o model-transparency se encaixaria no DNAT

Legenda: **[Hoje]** a ferramenta suporta · **[Proposta]** desenho nosso.

1. **Ingresso do base:**
   - o dono assina com OMS fora da plataforma;
   - uma CVM de ingestão verifica, aceita **só safetensors** e registra o **root digest** como
     identificador canônico.

   [Hoje: assinar e verificar · Proposta: política e registro]
2. **Chave do derivado nasce na CVM de fine-tuning:**
   - par EC efêmero com `REPORT_DATA = H(pubkey ‖ H(statements))`, no mesmo esquema do builder
     (E2b.4);
   - assinatura **offline** pelo método `key`, porque o container não tem rede.

   [Hoje: método `key` · Proposta: o vínculo com a atestação, que nenhuma ferramenta OMS faz]

   Variantes:
   - CA do DNAT emitindo certificado curto com SAN `spiffe://dnat/job/<id>` depois de verificar
     o relatório [`--san-uri` só no `main`];
   - Sigstore privado (Fulcio + Rekor v2) com um emissor OIDC que só emite token para CVM atestada
     [ferramenta suporta; emissor é Proposta].
3. **O que assinar:**
   - o bundle OMS do derivado (pesos completos ou adaptador LoRA, mais config e tokenizer);
   - **atestações separadas** com subject = root digest do derivado (#586):
     - (a) proveniência de fine-tuning estilo SLSA: base, datasets, imagem da receita,
       hiperparâmetros, job;
     - (b) evidência TEE via SCAI: SEV-SNP mais GPU;
     - (c) AI-SBOM com `DESCENDANT_OF`.

   [Proposta sobre formatos existentes]
4. **Verificação antes de treinar:** a CVM verifica o OMS do base, com a identidade do dono,
   antes de a KMS liberar os pesos. [Hoje: verificação · Proposta: encadeamento com a KMS]
5. **Ledger ou log:**
   - vão bundles ou seus hashes, proveniência, evidência TEE e veredito do Juiz; **nunca** pesos;
     nomes sensíveis cifrados;
   - formato: Rekor v2 privado ou SCITT;
   - a KMS só libera pesos para medições com prova de inclusão no log (estilo PCC).

   [Proposta]
6. **O Juiz** consome o OMS do derivado (re-hasheando dentro da própria CVM), a proveniência, a
   evidência TEE e o OMS do base. Emite o veredito como atestação in-toto (*test-result* ou VSA)
   assinada pela chave atestada da CVM do Juiz. [Proposta, no modelo de Laminator e Attestable
   Audits]
7. **Admissão para inferência** no estilo AIMM L3: OMS válido, proveniência com imagem
   permitida, evidência TEE e veredito PASS da identidade "Juiz". [Verificação OMS: Hoje ·
   *policy engine*: Proposta]

**Lacunas que ninguém fechou (oportunidade):**
- (i) não há predicado padrão para "derivado produzido por fine-tuning dentro de TEE atestado";
- (ii) nenhuma ferramenta OMS vincula a chave a um relatório SEV-SNP/TDX/H100, e o Fulcio não tem
  identidade de TEE;
- (iii) ninguém fez fine-tuning de LLM em GPU CC com atestação composta e assinatura do
  resultado;
- (iv) com pesos que nunca saem, terceiros não recalculam o hash: a verificação tem de virar um
  **recibo assinado por CVM verificadora**, e esse vínculo não está padronizado;
- (v) revogação em cascata dos derivados exige um índice de linhagem que o ecossistema não
  oferece.

---

## 4. Computação confidencial para LLMs (GPU TEE, sistemas em produção, ataques)

### 4.1 Disponibilidade de GPU confidencial (2026-10-20)

| Nuvem | SKU | GPU | TEE de CPU | Estado | Observações |
|---|---|---|---|---|---|
| **Azure** | [`Standard_NCC40ads_H100_v5`](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/gpu-accelerated/nccadsh100v5-series) ✔ | **1×** H100 NVL 94 GB | AMD SEV-SNP (Genoa) | **GA** desde set/2024 | 40 vCPU e 320 GiB; sem *live migration* nem virtualização aninhada ✔. Pelo levantamento: não aceita conta gratuita, só Ubuntu 22.04 qualificado. **Preço Linux sob demanda** (Retail Prices API, 2026-10-20): eastus2 US$ 6,98/h, westeurope US$ 8,90/h; **spot** eastus2 US$ 1,29/h |
| Azure | Multi-GPU, H200 ou Blackwell confidenciais | — | — | **não existe** | A única SKU "NCC" é a acima; um moderador da Microsoft (jul/2025) disse que não há *roadmap* público para multi-GPU |
| Azure | *Confidential inferencing* (Azure OpenAI Whisper) | H100 | SEV-SNP | Preview | Segundo os slides de Russinovich no CC Summit 2026 |
| **GCP** | `a3-highgpu-1g` Confidential | 1× H100 80 GB | Intel TDX | **GA** desde 31/07/2025 | 3 zonas, só *Spot* ou *Flex-start*, **sem sob demanda**. Preço em us-central1 (conferido pelo agente nas páginas de preço do GCP; não reconferido): base Spot US$ 6,27/h + sobretaxa CC US$ 0,44/h ≈ **US$ 6,71/h**; Flex-start US$ 4,79/h + US$ 0,51/h ≈ **US$ 5,30/h**. Sobretaxa igual em todas as regiões e sem desconto de uso ou compromisso |
| AMD Instinct | MI300 / MI325 / MI355 | — | — | **sem modo CC com atestação** | O folheto da MI355X só traz *secure boot* e identidade DICE da GPU. CC em escala de rack só no **Helios / MI455X** ("volume deployments 2H 2026"), com ressalva da própria AMD sobre integridade frente ao hipervisor (via ServeTheHome, a verificar). Nenhuma nuvem oferece |
| GCP | `g4-standard-48` Confidential | RTX PRO 6000 (Blackwell) | AMD SEV (Turin) | **GA** desde 07/08/2026 | 36 zonas; licença NVIDIA CC cobrada à parte |
| **AWS** | — | **nenhuma GPU TEE documentada** | Nitro (Enclaves sem GPU) | n/a | |
| Especializados | VoltageGPU, Privatemode (Edgeless), Tinfoil, Phala | H100/H200/B200 | TDX | alegação do fornecedor | NEAR private-ml-sdk **arquivado** em jun/2026 |
| *On-prem* | Hopper PPCIe (HGX 8×H100/H200) · B200 | | TDX ou SEV-SNP | PPCIe GA em abr/2025 | No Hopper multi-GPU, **o NVLink fica em claro**; só o Blackwell cifra NVLink. Intel TDX Connect segue como "gerações futuras" |

### 4.2 Overhead medido

| Referência | Venue · tier | Números | Leitura |
|---|---|---|---|
| [Benchmarking CC on NVIDIA Blackwell](https://arxiv.org/abs/2608.26575) (Asad, Grunseid; conflito de interesse) | 2026 · Pre | 8×B200 + TDX: inferência bem configurada 1–3%; *stacks* padrão 30–40% (modo eager, SGLang sem patch); **treino 10–13%**; H2D 3,5 vs. 51,6 GB/s | Único número de treino multi-GPU em hardware real. **A configuração da stack pesa mais que o TEE** |
| [Confidential Computing on Hopper](https://arxiv.org/abs/2409.03992) (Zhu et al., Phala; conflito) | 2024 · Pre | < 7% em consultas típicas; ~0 em modelos grandes | Base otimista |
| [PipeLLM](https://ipads.sjtu.edu.cn/zh/publications/TanASPLOS25.pdf) (Tan et al.) | **ASPLOS 2025** · topo | Com *swapping*: −52,8% (OPT-30B) e −88,2% (OPT-66B). **Fine-tuning LoRA com offload: −36,2%**. PipeLLM reduz para < 19,6% | **Offload para a CPU é inviável em CC**: o modelo tem de caber na GPU |
| [Performance of CC GPUs](https://arxiv.org/abs/2505.16501) (Martínez Ibarra et al.) | ICDCS 2025 · PR | Com troca de modelos, sem CC o *throughput* é 45–70% maior | Carregar modelo por sessão custa caro |
| [Confidential GPU Inference on H100 under TDX](https://arxiv.org/abs/2607.19353) (Wang et al.) | 2026 · Pre | TTFT +21,8% (7B) e +27,8% (30B MoE); *throughput* −17,7% e −21,1% | **Independente**, com números bem acima dos de fornecedores |
| [Intel: CC AI Performance TDX + H100](https://cdrdv2-public.intel.com/917058/Confidential-AI-Performance-Intel-TDX-NVIDIA-H100-System-Level-Analysis-917058-0100-20260409.pdf) | Rel (abr/2026) | Banda CPU↔GPU cai de ~55 para **~8 GB/s** (*bounce buffer*); 1B: 10–12%; 20–70B: 2–3% | Mecanismo explicado; serve para estimar tempo de carga dos pesos |
| [Confidential LLM Inference across CPU and GPU TEEs](https://arxiv.org/abs/2509.18886) (Chrapek, Hoefler et al.) | 2025 · Pre | CPU TEE com AMX: < 10% no *throughput*; H100 CC: 4–8%; CPU TEE pode sair mais barato | Rota "só CPU" para modelos pequenos |
| [GPU TEE Overheads in DDP Training](https://arxiv.org/abs/2501.11771) (Lee et al.) | 2025 · Pre | 4 GPU TEEs: iteração 8× mais lenta em média, até 41,6× (cifra no *all-reduce*); hardware real ou emulado **(a verificar)** | Treino distribuído confidencial ainda é caro |
| [Auditing Model Substitution](https://arxiv.org/abs/2504.04715) (Cai et al.) | NeurIPS 2025 WS · WS | vLLM em H100: TTFT +9% a +16%; *throughput* −15% (1 requisição) a −3% (64 requisições) | |

**Lacuna:** quase tudo foi medido em **TDX**. **Não há medição publicada de SEV-SNP + H100 NVL
na Azure**, que é justamente o nosso ambiente. Medi-lo pode virar resultado próprio.

### 4.3 Sistemas em produção e transparência

| Sistema | Fonte | Como provam o que roda | Para o DNAT |
|---|---|---|---|
| **Apple PCC** | [blog](https://security.apple.com/blog/private-cloud-compute/), [pesquisa](https://security.apple.com/blog/pcc-security-research/) | Log *append-only* de imagens; cliente só cifra para *release* no log; VRE; *bounty* | Padrão de referência |
| **Meta WhatsApp Private Processing** | [whitepaper v2, mar/2026](https://ai.meta.com/static-resource/private-processing-technical-whitepaper) | SEV-SNP + H100 CC, RA-TLS, OHTTP; **log de transparência de terceiros (Cloudflare) para binários e pesos**; *loader* com manifesto e prova de inclusão; VBIOS e NVSwitch fixados. Limitações declaradas: HBM não cifrada, NVLink do Hopper em claro, conluio com fabricante fora de escopo | **O desenho mais próximo do DNAT**; modelo de como declarar limitações |
| **Anthropic + Pattern Labs** | [blog](https://www.anthropic.com/research/confidential-inference-trusted-vms), [PDF jun/2025](https://assets.anthropic.com/m/c52125297b85a42/original/Confidential_Inference_Paper.pdf) | *Loader* que só aceita programas assinados por CI seguro; KMS libera a chave dos pesos só mediante atestação; builds reproduzíveis, imagem `FROM scratch`. **O ambiente de build é alvo prioritário**: se uma parte o controla sozinha, a garantia se perde. Treino confidencial fica fora | Valida o builder atestado (D4/E2b), que é uma quarta via além das três que eles listam |
| **Tinfoil** | [docs](https://docs.tinfoil.sh/verification/attestation-architecture) | **Pesos ligados por hash** (raiz dm-verity numa config cujo SHA256 vai na *cmdline* medida); Sigstore/Rekor; GPU verificada com `nvattest` antes do boot | Receita pronta |
| **Privatemode** (Edgeless) | [docs](https://docs.privatemode.ai/architecture/overview) | Coordenador e serviço de segredos liberam chaves só a *workers* atestados; pesos *read-only* | Padrão coordenador + KMS |
| **Google Private AI Compute** | [blog nov/2025](https://blog.google/technology/ai/google-private-ai-compute) | TPU com "Titanium Intelligence Enclaves" (comparável a TEE), atestação mútua, revisão pela NCC Group; transparência pública fica para o *roadmap* | Contraexemplo: auditoria do desenho sem verificabilidade pública |
| **Azure Confidential Clean Rooms** | [Learn](https://learn.microsoft.com/en-us/azure/confidential-computing/confidential-clean-rooms) (*limited preview*) | Governança em CCF: todos os donos aprovam a query; containers com atestação de artefatos do GitHub; **treino e fine-tuning de ML só sob pedido** | Análogo mais próximo do marketplace DNAT dentro da Azure |
| **Microsoft** (slides de Russinovich, [CC Summit 2026](https://hosted-files.sched.co/ccsummit2026/e8/Mark%20Russinovich%20-%20Confidential%20Computing%20Summit%202026%20-%20v2.pdf)) | apresentação | **Signing Transparency** (build confidencial reproduzível com recibo em ledger) e **"Virtual Data Diode"** (política de rede atestável) | O *Data Diode* bate com o nosso container sem rede; status **(a verificar)** |
| Piloto OpenMined + Anthropic + UK AISI | [blog](https://openmined.org/blog/secure-enclaves-for-ai-evaluation/) | Avaliação entre organizações em H100 no Azure: 28 min no total, dos quais 1 min 11 s de computação | **O gargalo foi aprovar o código (governança)** |

### 4.4 Ataques a TEEs relevantes (2024–2026)

| Ataque | Venue | Alvo e custo | Afeta atestação? | Tratamento |
|---|---|---|---|---|
| **[TEE.fail](https://tee.fail)** ✔ | **IEEE S&P 2026** | *Interposer* DDR5 por < US$ 1.000, com acesso físico. Forja *quotes* SGX/TDX (verificam como "UpToDate"); extrai chaves de VMs SEV-SNP (Zen 4/5) mesmo com Ciphertext Hiding. **A atestação NVIDIA CC não é amarrada à CVM e pode ser "emprestada"** | **Sim** | Intel e AMD consideram fora de escopo. **Vincular a GPU à CVM** e declarar o limite físico |
| [Battering RAM](https://batteringram.eu/) | IEEE S&P 2026 | *Interposer* DDR4 de US$ 47,62; SEV-SNP: reproduz o *launch digest* e burla a atestação | Sim | Limitação física |
| [WireTap](https://wiretap.fail/) | CCS 2025 | SGX com DDR4; forja *quote* aceito pelo DCAP | Sim (SGX) | Pouco relevante para SNP |
| [BadRAM](https://badram.eu/) | IEEE S&P 2025 | DIMM com SPD adulterado por < US$ 10; forja atestação SEV-SNP | Sim | **Corrigido por firmware**: exigir **TCB mínimo** |
| [CacheWarp](https://cachewarpattack.com/) | USENIX Sec 2024 | Injeção de falha por software em SEV-ES/SNP | — | Corrigido por microcódigo: TCB mínimo |
| [Heracles](https://heracles-attack.github.io/) · [RMPocalypse](https://rmpocalypse.github.io/) | CCS 2025 | O hipervisor escolhe texto claro e vaza chaves; sobrescrever 8 bytes na RMP permite **forjar atestação** (Zen 3/4/5) | Sim | Status de correção **(a verificar)**; TCB mínimo |
| [Blueprint, Bootstrap, and Bridge](https://arxiv.org/abs/2507.02770) (Gu et al.) | MLSys 2026 · PR | GPU CC: metadados RPC em claro, canal de tempo que vaza o tamanho das transferências, perda parcial de integridade no canal SEC2; CUDA UMD fechado | — | Limitação: firmware e *driver* fechados dentro do TCB |
| [TEESlice](https://arxiv.org/abs/2310.07152) (Zhang et al.) | IEEE S&P 2024 · topo | Particionar o modelo entre TEE e GPU vaza mais do que se supõe | — | Descarta "particionar" como substituto de GPU CC |

### 4.4.1 TCB mínimo para SEV-SNP em Genoa (Azure NCC) (segunda rodada)

- **RMPocalypse:** boletim [AMD-SB-3020](https://www.amd.com/en/resources/product-security/bulletin/amd-sb-3020.html),
  **CVE-2025-0033** ✔. **Corrigido.** No Genoa: firmware SEV **1.37.31, SPL = 0x1B**, microcódigo
  Genoa 0x0A101156 e Genoa-X 0x0A101251 ✔, ou AGESA GenoaPI 1.0.0.H.
- **Heracles:** coberto pelo boletim informativo AMD-SB-3021 (ago/2025), **sem CVE e sem
  correção de firmware**. Mitigações:
  - desabilitar *page move* e *swap* pela política do guest (bit 25 `PAGE_SWAP_DISABLE`, ABI ≥
    1.58);
  - *ciphertext hiding* (bit 24), **que só existe a partir do Turin**.

  **No Genoa só resta o bit de política.** Se a Azure o liga está **(a verificar)**.
- **Outros boletins de 2026 que sobem o piso:**
  - AMD-SB-3027 (jan/2026): microcódigo Genoa ≥ 0x56, Genoa-X ≥ 0x51;
  - AMD-SB-3023 (fev/2026): firmware 1.37.31, SPL 0x1B; um dos CVEs exige o *mitigation bit 0*;
  - AMD-SB-3033 (ago/2026): execução de código no firmware SEV, com ataque físico;
  - AMD-SB-3024 (*aliasing* físico de memória): **a AMD não vai mitigar**.
- **Piso sugerido pelo levantamento para a política de liberação de chave:**
  - TCB SNP ≥ 0x1B;
  - TCB de microcódigo ≥ 0x56 (Genoa) ou ≥ 0x51 (Genoa-X);
  - bits 0 e 1 do `current_mit_vector` ligados, quando o relatório trouxer o campo (versão ≥ 5,
    **a verificar na Azure**);
  - bit 25 da política do guest, se disponível.

  **Heracles fica como risco residual declarado** no Genoa.

### 4.4.2 Onboarding e créditos na Azure (segunda rodada)

- **[Azure/az-cgpu-onboarding](https://github.com/Azure/az-cgpu-onboarding)** (release V4.5.1,
  15/10/2026):
  - **Regiões:** East US 2, Central US e West Europe.
  - **SO:** Ubuntu 22.04 CVM (padrão) ou 24.04, com Secure Boot, *snapshot* fixado e sem
    *unattended-upgrades*.
  - **Kernel:** ≥ `6.8.0-1025-azure`.
  - **Driver:** `nvidia-driver-595-server-open` (R595).
  - **Atestação da CPU:** `azure-guest-attest` com Microsoft Azure Attestation.
  - **Atestação da GPU:** `local_gpu_verifier` (*fork* do nvtrust), que busca RIM e OCSP pelo
    cache regional **THIM** da Azure, e não pelo NRAS. O `nvattest` está em *preview*, e a
    política Rego padrão dele **retira de propósito a checagem do nonce do OCSP** por causa do
    cache.
- **Implicação:** o DNAT **não deve herdar essa política padrão**. Precisa de política própria,
  com o nonce da evidência da GPU vinculado ao `REPORT_DATA` do SNP (resposta ao TEE.fail), e
  deve fixar R595 e o kernel na imagem medida.
- **Créditos e cota:**
  - **Microsoft for Startups:** os créditos valem para "eligible Azure services… billed as
    standard Azure consumption", o que inclui VMs, sem exclusão explícita de VM confidencial. GPU
    fica "subject to availability".
  - **Azure for Students:** US$ 100 e, segundo um moderador, 3 vCPUs sem GPU. **Inviável**, porque
    a NCC40ads tem 40 vCPUs.
  - **AFMR/AARI (Microsoft Research):** dá acesso a modelos, não a VMs.
  - **Cota:** a família é "Standard NCCads2023 Family vCPUs"; pedido em Usage + quotas ou por
    ticket, em até 48 h.
  - Se patrocínios de pesquisa têm restrição para SKUs confidenciais: **(a verificar)**.
- **Plano B:** GCP `a3-highgpu-1g` confidencial (TDX), a ~US$ 5,30/h em Flex-start. Exige um
  verificador TDX além do SNP.

### 4.5 Segurança de pesos (quadro de referência)

- **[RAND: Securing AI Model Weights](https://www.rand.org/pubs/research_reports/RRA2849-1.html)**
  (Nevo et al., 2024) define os níveis SL1–SL5. Segundo a citação no whitepaper da Anthropic, SL4
  e SL5 recomendam TEE **com proteção física**, chave gerada no TEE e código auditado e assinado
  (a página do RAND deu 403; **a verificar no original**). Sem proteção física, o DNAT fica **no
  máximo em SL3**.
- **[Anthropic ASL-3](https://www.anthropic.com/news/activating-asl3-protections) e
  [RSP](https://www.anthropic.com/responsible-scaling-policy)** usam mais de 100 controles
  (autorização por duas pessoas, controle de *egress*) e **não mencionam TEE**. Os laboratórios
  protegem pesos por controle de acesso, não por TEE.

---

## 5. Execução e auditoria verificáveis

### 5.1 Abordagens comparadas

| Abordagem | O que prova | Custo / escala | Maturidade (out/2026) |
|---|---|---|---|
| **TEE** (CVM SEV-SNP/TDX + GPU NVIDIA CC) | Que um binário medido (código + hash dos pesos) rodou isolado e assinou saída, recibo ou avaliação. **Não prova** que o código está certo nem que a avaliação é completa | GPU CC: < 7–16% de *overhead*. Attestable Audits em CPU (Nitro): 2,2× o custo de CPU | Em produção (Apple PCC, Anthropic). Vulnerável a ataque físico (TEE.fail) |
| **ZK** (inferência, treino, avaliação) | Prova criptográfica, sem confiar em hardware, de que a saída ou métrica veio de pesos com *commitment* | zkLLM: 13B em < 15 min por inferência. zkGPT: GPT-2 em < 25 s. Kaizen: ~15 min por iteração com 10M parâmetros. **Inviável para fine-tuning de LLM hoje** | Pesquisa |
| **Commitments de ativações** (TOPLOC, SVIP) | Que o provedor usou o modelo, prompt e precisão declarados, com tolerância a não-determinismo; precisa de verificador com os pesos | TOPLOC: 258 B por 32 tokens, ~1000× menor | Implementado (Prime Intellect) |
| **Testes estatísticos e *fingerprinting*** | Indício, não prova, de qual modelo uma API serve | MET: poder mediano de 77,4%. Contra quantização, os classificadores ficam no acaso (49–52%) | Ferramentas abertas, frágeis contra adversário |
| **Reexecução otimista** (PoL, determinismo controlado) | Que o treino declarado reproduz os checkpoints | PoL foi quebrado (Fang 2023); reprodução bit a bit é viável com determinismo forçado | PoL frágil; determinismo viável |
| **Logs de transparência** | Que o artefato (imagem, modelo, atestação, auditoria) foi publicado *append-only*; combate *split-view* e omissão | Barato | Maduro para imagens (PCC) e assinatura de modelos (Sigstore) |
| **Mecanismos em hardware para governança** (flexHEG, HEMs) | Afirmações sobre uso de computação e avaliações privadas, garantidas no chip | Não existem ainda (flexHEG estima 2027+) | Propostas |

### 5.2 Referências

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [Attestable Audits](https://arxiv.org/abs/2506.23706) (Schnabl et al.) | ICML 2025 WS TAIG · WS | Benchmarks de segurança rodam em TEE (Nitro, só CPU, Llama-3.1-8B 4-bit). Cada resposta de inferência leva atestação que liga Hash(M), prompt, saída e resultado da auditoria, publicada num log | **O vizinho mais próximo do "Juiz atestado"**. Não trata de fine-tuning |
| [Atlas: ML Lifecycle Provenance & Transparency](https://arxiv.org/abs/2502.19567) (Spoczynski, Melara, Szyller, Intel Labs) ✔ | 2025 · Pre | Hardware confiável + logs de transparência + especificações de proveniência (estilo SLSA/in-toto) para pipelines de ML, do treino ao deployment; protótipo em 2 pipelines | **Muito próximo da nossa arquitetura**, mas sem Juiz de segurança nem liberação condicionada. Cobertura de fine-tuning (a verificar no PDF) |
| [Laminator](https://arxiv.org/abs/2406.17548) (Duddu et al.) | ACM CODASPY 2025 · PR | TEE atesta ligações modelo ↔ dados de treino ↔ configuração ↔ acurácia | O "model card atestado" é quase o formato do nosso recibo |
| [Proof-of-Guardrail](https://arxiv.org/abs/2603.05786) (Jin et al.) | ICML 2026 WS · WS | TEE atesta que a resposta passou por um guardrail específico. **A prova cobre integridade da execução, não eficácia** | A mesma crítica vale para o Juiz |
| [AFTUNE](https://arxiv.org/abs/2603.07466) (Jin et al.) | 2026 · Pre | Auditoria, por amostragem de blocos, de fine-tuning e inferência dentro de TEE | Integridade do fine-tuning |
| [Verifiable Fine-Tuning with ZK](https://arxiv.org/abs/2510.16830) (Akgul et al.) | 2025 · Pre | PEFT com circuitos ZK, *commitments* de dados, licenças e cotas, TEE opcional | Mesma ideia de "fine-tuning amarrado à política", sem avaliação de segurança |
| [TCME: Trusted Capable Model Environments](https://arxiv.org/abs/2501.08970) (Shumailov et al., GDM) | 2025 · Pre | Ambiente sem estado, com fluxo de informação explícito e modelo confiável; pode rodar em TEE; garantias heurísticas | A CVM de uso único já dá a ausência de estado |
| [Auditing Model Substitution in LLM APIs](https://arxiv.org/abs/2504.04715) (Cai et al.) | NeurIPS 2025 WS · WS | Detecção só por software falha contra quantização; propõe TEE | Justifica atestação para Q1 |
| [Model Equality Testing](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d73234a13815fc1f9779dd17d89be9b4-Abstract-Conference.html) (Gao et al.) | ICLR 2025 · topo | Teste MMD: 11 de 31 endpoints Llama divergiam da referência | Checagem estatística externa |
| [LLMmap](https://arxiv.org/abs/2407.15847) (Pasquini et al.) | USENIX Sec 2025 · topo | > 95% de acerto em 42 versões com 8 consultas | Indício, não prova |
| [TOPLOC](https://proceedings.mlr.press/v267/ong25a.html) (Ong et al.) | ICML 2025 · topo | 258 B por 32 tokens; detectou 100% das trocas de modelo, prompt ou precisão nos testes dos autores | O recibo pode guardar *commitments* de ativações para auditoria posterior |
| [SVIP](https://arxiv.org/abs/2410.22307) (Sun et al.) | 2024/25 · WS | Tarefa proxy secreta sobre estados ocultos; FNR < 5%, FPR < 3% | Idem |
| [zkLLM](https://arxiv.org/abs/2404.16109) (Sun et al.) | CCS 2024 · topo | 13B em < 15 min por inferência | ZK é ordens de grandeza mais caro que TEE |
| [zkGPT](https://www.usenix.org/conference/usenixsecurity25/presentation/qu-zkgpt) (Qu et al.) | USENIX Sec 2025 · topo | GPT-2 em < 25 s | Idem |
| [Kaizen: ZK Proofs of Training](https://eprint.iacr.org/2024/162) (Abbaszadeh et al.) | CCS 2024 · topo | ~15 min por iteração com 10M parâmetros | Treino em ZK fora de alcance para LLM |
| [Proof-of-Learning](https://arxiv.org/abs/2103.05633) (Jia et al.) e [crítica](https://arxiv.org/abs/2208.03567) (Fang et al.) | S&P 2021 · topo; EuroS&P 2023 · PR | Checkpoints como prova de treino, mas forjáveis a uma fração do custo | Checkpoints no recibo, só com TEE |
| [Optimistic Verifiable Training](https://arxiv.org/abs/2403.09603) (Srivastava, Arora, Boneh) | NeurIPS 2024 · topo | Reprodução exata em FP32 (ResNet-50, GPT-2) em 3 GPUs | Reexecução por terceiros como alternativa à confiança no TEE |
| [Verde/RepOps](https://arxiv.org/abs/2502.19405) (Arun et al.) | 2025 · Pre | Delegação arbitrada com reprodutibilidade bit a bit para inferência e treino | Idem |
| [Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/) (He) | 2025 · Rel | Kernels invariantes ao batch: 1.000 amostras em T=0 saem iguais (antes, 80 distintas); 26 s → 42 s | Juiz determinístico e reexecutável |
| [Black-Box Access is Insufficient for Rigorous AI Audits](https://arxiv.org/abs/2401.14446) (Casper et al.) | FAccT 2024 · topo | Auditorias *white-box* permitem muito mais escrutínio | Dentro do TEE o Juiz tem acesso *white-box* sem que os pesos saiam |
| [LLMs Often Know When They Are Being Evaluated](https://arxiv.org/abs/2505.23836) (Needham et al.) | 2025 · Pre | Gemini-2.5-Pro distingue avaliação de uso real com AUC 0,83 | A bateria deve parecer uso real e ser parcialmente secreta |
| [flexHEG](https://arxiv.org/abs/2506.15093) (Petrie et al.) · [RAND six layers](https://arxiv.org/abs/2507.15916) · [Oxford AIGI](https://www.oxfordmartin.ox.ac.uk/publications/verification-for-international-ai-governance) · [CNAS](https://www.cnas.org/publications/reports/secure-governable-chips) | 2024–25 · Rel | Avaliação privada e implantação controlada garantidas em hardware; verificação "possível em poucos anos" | Contexto regulatório |

### 5.3 Provar o fine-tuning por LoRA: ZK ou TEE (segunda rodada)

**Resolução.**
- **Prova ZK de cada passo de LoRA ainda é cara demais para receitas reais.**
  - VeriLoRA (NDSS 2026) leva 122–249 s por passo com mini-batch de **uma** amostra, contra
    0,47–1,25 s sem ZK.
  - Extrapolação do levantamento: 10 mil amostras num modelo 13B dariam ~29 dias de GPU.
- **TEE com auditoria amostral custa 11–36%** (AFTUNE). Detecta subtreino e troca de modelo, mas
  **não** detecta dados envenenados com amostragem uniforme.
- **Desenho que sai daqui:** builder atestado + *spot-check* em TEE + **inspeção do conteúdo**
  dos dados. ZK fica para passos amostrados ou para provar a avaliação do Juiz.

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [VeriLoRA](https://arxiv.org/abs/2508.21393) (Liao, Wang, Zhang et al.; antes chamado zkLoRA, segundo o levantamento) ✔ | **NDSS 2026** · topo | Prova *forward*, *backward* e a atualização dos pesos LoRA sem revelar pesos nem dados. Testado até 13B. **Números do corpo** (o abstract não traz): 122 s (LLaMA-3.2-3B) a 249 s (OPT-13B) por passo de 1 amostra numa A100; verificação em 1,9–3,7 s; *commitments* de 135–233 MB | Inviável por passo; serve para auditoria amostral ou derivados pequenos |
| [ZKLoRA](https://arxiv.org/abs/2501.13965) (Roy et al.) | 2025 · Pre | Verifica que um LoRA privado é compatível com o base e funciona como alegado, em 1–2 s por módulo; **não prova o treino** | Provar a linhagem do adaptador sem expô-lo |
| [Verifiable Fine-Tuning with ZK](https://arxiv.org/abs/2510.16830) (Akgul et al.) | 2025 · Pre | 16,8 s (r=8) e 31,2 s (r=16) por passo com 2048 tokens; prova final de 4–6 MB, verificada em < 200 ms; modelo testado não identificado | Confirma a ordem de grandeza |
| [AFTUNE](https://arxiv.org/abs/2603.07466) (Jin et al.) | 2026 · Pre | Registra o treino em blocos e verifica blocos sorteados em TEE. *Overhead* de 11–28% (Qwen3-14B) e 18–36% (Llama-3.1-8B). Detecção: subtreino 87–99%; troca de modelo 80–98%; **envenenamento de 10% só 36–59%** com amostragem uniforme (98–99,9% checando só a entrada) | Combina com o builder atestado. A auditoria de dados tem de olhar o conteúdo |
| [DeepProve](https://eprint.iacr.org/2026/1112) | 2026 · Pre | ZK de inferência: 174 tok/min (GPT-2) e 86 tok/min (Gemma 3) | Até a inferência em ZK é lenta |

---

## 6. Fine-tuning sem obliteração

### 6.1 Mapa da área

| Estágio | Ataques e riscos | Defesas e controles |
|---|---|---|
| **Alinhamento** (antes do depósito) | A recusa é mediada por **uma direção**, removível por edição rank-1 (abliteration) [Arditi]. O alinhamento é "raso", concentrado nos primeiros tokens [Qi 2025b] | Vaccine, Booster, RepNoise, TAR, ReFAT, *Deep Ignorance* (filtrar o pré-treino). Contra abliteration: recusas longas [Abu Shairah], ART [Kuo], DDO [Muhamed] |
| **Durante o fine-tuning** | 10 exemplos por < US$ 0,20 [Qi 2024]; dados cifrados (CMFT) [Halawi]; jailbreak-tuning [Murphy]; *refuse-then-comply* [Kazdan]; dados **benignos** escolhidos a dedo [Guan]; desalinhamento emergente [Betley] | Lisa, SafeLoRA, objetivo por token [Qi 2025b], KL ao original ou mistura de dados seguros [Kaczér] |
| **Pós-fine-tuning** | O derivado vira um "evil twin" [Murphy] | Antidote, SafeMERGE, LoX; algumas centenas de amostras benignas realinham [Wang] |
| **Auditoria do job** | Moderação ponto a ponto tem limite teórico [Davies]; Virus fura a moderação; *subliminal learning* [Cloud] | Agente auditor com dados + modelo pré + modelo pós [Egler] ✔; *model diffing* com SAE [Wang]; sondas internas (Latent Guard) |
| **Avaliação do derivado** | Backdoors com gatilho [Hubinger]; *sandbagging* [van der Weij]; consciência de estar sendo avaliado [Needham]; defesas que parecem duráveis por avaliação mal feita [Qi 2025a] | SORRY-Bench, StrongREJECT, HarmBench, XSTest (*over-refusal*), AIR-Bench, WMDP; *tampering* como limite superior [Che] |
| **Destilação e extração** | Roubo da camada de projeção por < US$ 20 [Carlini]; destilação industrial com > 16 milhões de trocas [Anthropic 2026]; marca d'água herdada é removível [Pan] | Antidistillation sampling; marca d'água "radioativa"; SynthID-Text; *fingerprinting* (Chain & Hash); detecção por padrão de contas |

### 6.2 Referências principais

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [Fine-tuning Aligned LMs Compromises Safety…](https://arxiv.org/abs/2310.03693) (Qi et al.) | ICLR 2024 oral · topo | 10 exemplos por < US$ 0,20 desfazem a segurança do GPT-3.5; dados benignos também degradam | O fine-tuning legítimo já corrói a recusa: o Juiz precisa de **limiar**, não de "zero degradação" |
| [Covert Malicious Finetuning](https://proceedings.mlr.press/v235/halawi24a.html) (Halawi et al.) | ICML 2024 · topo | Exemplos individualmente inócuos ensinam uma cifra; o GPT-4 obedece 99% e passa por inspeção, avaliações e classificadores | Ler dados ou código não basta; a avaliação deve usar as codificações presentes nos dados |
| [Jailbreak-Tuning](https://aclanthology.org/2025.emnlp-main.669/) (Murphy et al.) | EMNLP 2025 · topo | Modelos da OpenAI, Google e Anthropic passam a atender pedidos CBRN; modelos mais novos são mais vulneráveis; recomendam *safety case* que assume falha total | Tratar todo derivado como *evil twin* até passar no portão |
| [No, of Course I Can!](https://arxiv.org/abs/2502.19537) (Kazdan et al.) | ICLR 2026 · topo | *Refuse-then-comply* com dados inofensivos: 57% no GPT-4o, 72% no Claude Haiku | A bateria tem de ler a resposta inteira |
| [Benign Samples Matter!](https://proceedings.mlr.press/v267/guan25c.html) (Guan et al.) | ICML 2025 · topo | 100 amostras benignas "outlier" quebram a segurança em 7 LLMs | Moderação de conteúdo não pega isso |
| [Fundamental Limitations in Pointwise Defences](https://arxiv.org/abs/2502.14828) (Davies et al., UK AISI) | 2025 · Pre | Ataques indetectáveis amostra a amostra funcionaram na API da OpenAI | Limite teórico da auditoria de dados |
| [Emergent Misalignment](https://proceedings.mlr.press/v267/betley25a.html) (Betley et al.) | ICML 2025 · topo; *Nature* 2026 | Fine-tuning para código inseguro gera desalinhamento amplo; a variante com gatilho só aparece com o gatilho | A bateria tem de ser ampla e sair do domínio do fine-tuning |
| [Subliminal Learning](https://arxiv.org/abs/2507.14805) (Cloud et al.) | 2025 · Pre | Traços passam por sequências numéricas filtradas, quando há a mesma base | Dados gerados por um derivado contaminam outro derivado |
| [Refusal… Mediated by a Single Direction](https://proceedings.neurips.cc/paper_files/paper/2024/hash/f545448535dfde4f9786555403ab7c49-Abstract.html) (Arditi et al.) | NeurIPS 2024 · topo | Uma direção controla a recusa em 13 modelos de até 72B; edição rank-1 sem treino | Base da abliteration e **sinal de auditoria** (projeção do delta nessa direção) |
| [Harmful Fine-tuning Survey](https://arxiv.org/abs/2409.18169) (Huang et al.) | 2024 · Pre | Taxonomia por estágio; cenário central é *fine-tuning-as-a-service* | Organiza as defesas |
| [Booster](https://proceedings.iclr.cc/paper_files/paper/2025/hash/a7ac8a21e5a27e7ab31a5f42a0117bdb-Abstract-Conference.html) · [RepNoise](https://arxiv.org/abs/2405.14577) · [TAR](https://proceedings.iclr.cc/paper_files/paper/2025/hash/fc49a629d33bc2461ed7a715ce44da68-Abstract-Conference.html) · [ReFAT](https://proceedings.iclr.cc/paper_files/paper/2025/file/1022661f3f43406065641f16ce25eafa-Paper-Conference.pdf) | ICLR 2025 / NeurIPS 2024 · topo | Defesas no alinhamento | Recomendação ao dono **antes** do depósito |
| [Deep Ignorance](https://arxiv.org/abs/2508.06601) (O'Brien, Casper et al.) | 2025 · Pre (ICLR 2026, a verificar) | Filtrar o pré-treino resiste a 10.000 passos e 300M tokens adversariais | O resultado mais forte de *tamper-resistance*, mas fora do nosso alcance |
| [Embarrassingly Simple Defense Against Abliteration](https://arxiv.org/abs/2505.19056) (Abu Shairah et al.) | 2025 · Pre | Com recusas longas, a abliteration derruba a recusa em ≤ 10% (contra 70–80%) | Defesa barata do dono |
| [Open-Weight Defenses Susceptible to Simple Attacks](https://arxiv.org/abs/2605.26526) (Kuo et al.) | 2026 · Pre | Abliteration e *prefill* elevam o sucesso de ataque de < 10% para 16–96% | A avaliação deve incluir abliteration e *prefill* de teste |
| [Safety Alignment… More Than a Few Tokens Deep](https://proceedings.iclr.cc/paper_files/paper/2025/hash/88be023075a5a3ff3dc3b5d26623fa22-Abstract-Conference.html) (Qi et al.) | ICLR 2025 Outstanding · topo | O alinhamento atua nos primeiros tokens; um objetivo regularizado o aprofunda | Regularizador na receita da plataforma |
| [Safe LoRA](https://papers.neurips.cc/paper_files/paper/2024/hash/77baa7c2a3a675823e89131698fd6e19-Abstract-Conference.html) · [Lisa](https://proceedings.neurips.cc/paper_files/paper/2024/hash/bcfdaf04b54a69f47623c973c864ee8d-Abstract.html) · [Antidote](https://proceedings.mlr.press/v267/huang25b.html) · [LoX](https://arxiv.org/abs/2506.15606) | NeurIPS 2024 / ICML 2025 · topo; COLM 2025 · PR | Projeção, mistura, poda e extrapolação contra a degradação | O builder pode aplicar ao fim do job |
| [In-Training Defenses against Emergent Misalignment](https://arxiv.org/abs/2508.06249) (Kaczér et al.) | ICML 2026 · topo | KL, L2, SafeLoRA e mistura contêm o desalinhamento, mas atrapalham algumas tarefas benignas | O *trade-off* que a plataforma vai enfrentar |
| [On Evaluating the Durability of Safeguards](https://arxiv.org/abs/2412.07097) (Qi et al.) | ICLR 2025 · topo | Mudar seed, LR ou template quebra RepNoise e TAR | **Protocolo de avaliação**: pior caso sobre configurações, ataques adaptativos |
| [Model Tampering Attacks](https://arxiv.org/abs/2502.05209) (Che et al.) | TMLR 2025 · PR | *Unlearning* desfeito em até 16 passos; o *tampering* dá limite superior do risco | O Juiz pode atacar o derivado com um fine-tune curto |
| [Detecting Adversarial Fine-tuning with Auditing Agents](https://arxiv.org/abs/2510.16255) (Egler, Schulman, Carlini) ✔ | 2025 · Pre | Agente com dataset + modelo pré + modelo pós; **56,2% de detecção com 1% de FPR** em mais de 1.400 auditorias; pega ataques cifrados que a moderação não pega | **O desenho publicado mais próximo do "Juiz para U1"**; referência de desempenho realista |
| [Persona Features Control Emergent Misalignment](https://arxiv.org/abs/2506.19823) (Wang et al., OpenAI) | ICLR 2026 · topo | *Model diffing* com SAE acha uma *feature* de "persona tóxica" que prediz o desalinhamento | Sinal em pesos e ativações, além do comportamento |
| [SORRY-Bench](https://proceedings.iclr.cc/paper_files/paper/2025/hash/9622163c87b67fd5a4a0ec3247cf356e-Abstract-Conference.html) · [XSTest](https://aclanthology.org/2024.naacl-long.301) · [HarmBench](https://proceedings.mlr.press/v235/mazeika24a) · [StrongREJECT](https://proceedings.neurips.cc/paper_files/paper/2024/hash/e2e06adf560b0706d3b1ddfca9f29756-Abstract.html) · [WMDP](https://mlanthology.org/icml/2024/li2024icml-wmdp/) | ICLR'25 · NAACL'24 · ICML'24 · NeurIPS'24 · ICML'24 · topo | Recusa (SORRY tem juiz 7B local), *over-refusal* e capacidade perigosa | **Bateria A4**, rodável na CVM sem rede |
| [Sleeper Agents](https://arxiv.org/abs/2401.05566) (Hubinger et al.) · [AI Sandbagging](https://proceedings.iclr.cc/paper_files/paper/2025/hash/b5e5753b0a0e440a6d8dc7e143617cec-Abstract-Conference.html) (van der Weij et al.) | 2024 · Pre; ICLR 2025 · topo | Backdoors sobrevivem ao treino de segurança; modelos com senha escondem capacidade | **Limite central**: vai bem na avaliação e mal depois |
| [Stealing Part of a Production LM](https://proceedings.mlr.press/v235/carlini24a.html) (Carlini et al.) | ICML 2024 Best Paper · topo | Recupera a projeção dos modelos Ada e Babbage por < US$ 20 | Não expor logprobs completos nem *logit bias* |
| [Antidistillation Sampling](https://proceedings.neurips.cc/paper_files/paper/2025/hash/aad5e2a483869d9ba3fab491686c3bf2-Abstract-Conference.html) (Savani et al.) | NeurIPS 2025 · topo | Envenena traços de raciocínio contra destilação | Candidata para a destilação, a confirmar |
| [Can LLM Watermarks Prevent Unauthorized Distillation?](https://aclanthology.org/2025.acl-long.648) (Pan et al.) | ACL 2025 · topo | Paráfrase dirigida remove a marca herdada | Marca d'água é **evidência forense frágil**, não prevenção |
| [Detecting and preventing distillation attacks](https://www.anthropic.com/news/detecting-and-preventing-distillation-attacks) (Anthropic) | 23/fev/2026 · Rel | > 16 milhões de trocas em ~24 mil contas fraudulentas; detecção por classificadores e *fingerprinting* comportamental | Prática de produção |
| [Structured access](https://arxiv.org/abs/2201.05159) (Shevlane) | 2022 · capítulo | O provedor controla o uso sem entregar pesos | Base conceitual do U1 |

### 6.3 O estado do debate sobre tamper-resistance (out/2026, segunda rodada)

**Resolução.**
- **Consenso de 2026: salvaguardas embutidas nos pesos não duram.**
  - O melhor estado da arte resiste a "várias centenas de passos" de fine-tuning adversarial.
  - Pós-treino e *unlearning* caem em "dezenas de passos" ou com < 100 exemplos, em minutos e
    por dezenas de dólares.
- **Caminhos promissores, sem garantia:** filtrar o pré-treino (> 10× mais resistente, segundo a
  AISI) e destilar após o *unlearning* (UNDO).
- **Não há teorema de impossibilidade.**
- **Para onde o debate migrou:**
  - avaliação de pior caso com fine-tuning malicioso (MFT) antes do lançamento;
  - testes também sem treino (*prefill*, ablação de recusa);
  - lançamento escalonado com **fine-tuning hospedado** como degrau intermediário;
  - alternativas governadas por hardware ou TEE.

  **Esse último é o nicho do U1.**
- **Não encontrado:** relatório próprio da GovAI sobre o tema; *position paper* do ICML 2026 com
  prefixo "Position:".

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [Open Technical Problems in Open-Weight AI Model Risk Management](https://arxiv.org/abs/2608.07514) (Casper et al., 22 autores, incl. AISI, Hendrycks, Kolter, Bengio) | TMLR 03/2026 · PR | 16 problemas abertos; salvaguardas desfeitas em dezenas de passos; o melhor *tamper-resistance* chega a "várias centenas"; ataques custam minutos e dezenas de dólares; recuperação em contexto "sem solução" | **O survey a citar.** Justifica a custódia dos pesos em vez de salvaguarda nos pesos |
| [UK AISI: Managing risks from increasingly capable open-weight AI systems](https://www.aisi.gov.uk/blog/managing-risks-from-increasingly-capable-open-weight-ai-systems) | 29/08/2025 · Rel | *Tamper-resistance* desfeita "com dezenas de exemplos em minutos"; filtrar dados é "> 10× mais eficaz"; "nenhuma solução atual oferece garantias rígidas" | Posição oficial de agência |
| [UK AISI: Frontier AI Trends Report](https://www.aisi.gov.uk/frontier-ai-trends-report) | dez/2025 · Rel | Há jailbreak universal em todos os sistemas testados, com esforço ~40× maior que antes; APIs de fine-tuning "podem introduzir vulnerabilidades difíceis de mitigar" | Fine-tuning é superfície de ataque reconhecida |
| [International AI Safety Report, 2nd Key Update](https://arxiv.org/abs/2511.19863) (Bengio et al.) | nov/2025 · Rel | *Unlearning* revertido com < 100 exemplos; mitigações para pesos abertos "imaturas" | Consenso internacional |
| [Estimating Worst-Case Frontier Risks of Open-Weight LLMs](https://mlanthology.org/iclr/2026/wallace2026iclr-estimating/) (Wallace et al., OpenAI) | ICLR 2026 · topo | MFT com RL (bio e CTF) no gpt-oss fica abaixo do o3; propõem o MFT como modelo de decisão de lançamento | **O Juiz pode usar o MFT** como teste de pior caso do derivado |
| [A Safe Path to Open Weights](https://thinkingmachines.ai/blog/a-safe-path-to-open-weights/) (Thinking Machines) | 31/07/2026 · Rel | "Recusa não é salvaguarda durável"; sequência API → GA monitorado → **fine-tuning hospedado com monitoramento e revogação** → pesos | O DNAT ocupa o degrau "fine-tuning hospedado", com atestação a mais |
| [Beyond Harmful Fine-Tuning: Training-Free Tampering](https://icml.cc/virtual/2026/78555) (Yu, Ye) | ICML 2026 WS · WS | Defesas contra fine-tuning nocivo caem com *prefill* + *system prompt* malicioso e com ablação de recusa | Testar o derivado **sob a interface exposta**; a plataforma deve bloquear *prefill* e *steering* |
| [Machine Unlearning Doesn't Do What You Think](https://arxiv.org/abs/2412.06966) (Cooper et al.) | NeurIPS 2025 oral · topo | *Unlearning* "não é solução de uso geral" | Não usar *unlearning* como garantia |
| [Distillation Robustifies Unlearning (UNDO)](https://proceedings.neurips.cc/paper_files/paper/2025/hash/800981b7bff06c3feb88c65cc712ba2b-Abstract-Conference.html) (Lee et al.) | NeurIPS 2025 · topo | Iguala a robustez de retreinar com filtragem perfeita usando 60–80% do *compute* | Contraponto otimista; linha de base, não garantia |
| [Safety Gap Toolkit](https://arxiv.org/abs/2507.11544) (Dombrowski et al., FAR.AI) | 2025 · Pre | O *safety gap* cresce com a escala (0,5B a 405B) | Ferramenta para medir capacidade com e sem salvaguardas |

### 6.4 Destilação: marca d'água e defesas operacionais (segunda rodada)

**Resolução.**
- **Marca d'água serve como evidência forense de destilação, não como prevenção.**
  - O aluno herda a marca: em Gu et al. (ICLR 2024), p mediano de 2e-17 por completude de 200
    tokens.
  - Marcas de baixa distorção são aprendidas fracamente (p ≈ 0,1–0,4), e a marca **some com
    fine-tuning posterior**.
  - Com o aluno em mãos, TextSeal chega a p = 3,7e-110. Em modo leve, ADFP dá p ≈ 0,02–4e-4.
  - É removível (paráfrase dirigida, CDG-KD) e **falsificável** (*spoofing*): não serve para
    atribuir culpa sozinha.
- **Prevenção, na prática da Anthropic (out/2026):** controlar o acesso ao raciocínio,
  classificar tentativas de extração e penalizar quem insiste. Resultado relatado: **90–99%
  menos dados colhidos**, na plataforma dela e ainda sem atacante sofisticado.
- **Esconder o CoT não basta:** dá para inverter os traços a partir de entrada, resposta e resumo,
  com 10 mil consultas e ~US$ 173.

| Referência | Venue · tier | Achado | Para o DNAT |
|---|---|---|---|
| [On the Learnability of Watermarks for LMs](https://proceedings.iclr.cc/paper_files/paper/2024/hash/a86d17b6cd70366d56ab48d2a05a4df1-Abstract-Conference.html) (Gu, Li, Liang, Hashimoto) | ICLR 2024 · topo | Aluno aprende a marca por logits e por amostragem; números da Resolução; a mesma aprendibilidade permite *spoofing* | A marca é herdada, mas frágil |
| [TextSeal](https://arxiv.org/abs/2605.12456) (Sander et al., Meta) | mai/2026 · Pre | p = 3,7e-110 por *teacher forcing*, que exige acesso ao aluno; não degrada o GSM8K | Exige obter os pesos ou logits do suspeito |
| [Antidistillation Fingerprinting](https://arxiv.org/abs/2602.03812) (Xu, Kirchenbauer, …, Kolter) | ICML 2026 segundo o arXiv (a verificar) · topo | Escolhe tokens que maximizam a detectabilidade após o fine-tuning; funciona com aluno fechado; TPR de 55% com 0% de FPR (contra 24% do KGW) | Marcar saídas servidas de derivados, com custo de utilidade |
| [CDG-KD: spoofing and scrubbing in unauthorized KD](https://arxiv.org/abs/2504.17480) (Yi et al.) | 2025 · Pre | Destilação bidirecional remove ou forja a marca radioativa | Marca não é controle robusto |
| [Reference-Based Distillation Detection](https://arxiv.org/abs/2607.09692) (Rawat et al.) | jun/2026 · Pre | Sem marca, com checkpoint de referência: 97,2% de recuperação do professor por amostra com ~200 *probes*; **cai a 0% se o professor só expõe respostas finais** | Detecção sem marca depende de traços visíveis |
| [Strengthening our defenses against distillation attacks](https://www.anthropic.com/research/distillation-defenses) (Anthropic) ✔ | 12/10/2026 · Rel | 90–99% menos dados colhidos; tokens de raciocínio extraídos 10–100× menores; classificador em dois estágios com **FPR < 0,1%**; dezenas de milhares de contas banidas, muitas em < 2 h; requisições bloqueadas cobradas desde 24/09; treinar com transcrições completas dá 80,4% no SWE-bench Verified contra 71,8% com resumidas | **Modelo de defesa operacional para o gateway de inferência** |
| [Threat Intelligence Report, set/2026](https://www.anthropic.com/threat-intelligence-report-september-2026) (Anthropic) | set/2026 · Rel | 7 laboratórios; Alibaba > 151M trocas; táticas como forçar raciocínio em *tags*, *replay* da *thinking signature*, 12 mil variantes testadas | Catálogo de táticas para o classificador do DNAT |
| [How to Steal Reasoning Without Reasoning Traces](https://arxiv.org/abs/2603.07267) (Zhang, Morris, Shmatikov) | 2026 · Pre | Inversão de traços com 10 mil consultas (US$ 173): Qwen-7B vai de 68,4 para 76,0 no MATH500 | Ocultar o CoT não basta |
| [The Distillation Game](https://arxiv.org/abs/2605.22737) (Allouah et al.) · [What Does It Mean to Break a Distillation Defense?](https://arxiv.org/abs/2606.25059) (Libon, …, Tramèr) | 2026 · Pre | Alunos adaptativos recuperam bem mais do que a avaliação passiva sugere. Modelo de ameaça em três eixos: orçamento de consultas, orçamento de dados, perfil de interface | **Especificar a anti-destilação do DNAT nesses três eixos** e testar contra aluno adaptativo |

---

## 7. Consensos da área (síntese cruzada)

1. **O alinhamento por pós-treino é raso e barato de desfazer.** Bastam de 10 a algumas centenas
   de exemplos e de < US$ 1 a < US$ 200, em pesos abertos e em APIs fechadas. Até dados benignos
   degradam a segurança.
2. **A recusa é aproximadamente linear e de baixa dimensão.** A abliteration não precisa de
   treino, só de acesso a ativações e pesos.
3. **Moderação de dados exemplo a exemplo é insuficiente**, com resultados construtivos e
   teóricos (CMFT, ataques indetectáveis ponto a ponto, *subliminal learning*).
4. **Tamper-resistance em pesos abertos não está resolvida.** Defesas caem sob avaliação de pior
   caso. A exceção é filtrar o pré-treino, que é caro.
5. **Defesa em profundidade é a resposta aceita**: dados, receita, pós-treino, avaliação e
   monitoramento da inferência. Nenhuma camada basta sozinha.
6. **Avaliação comportamental é necessária, mas não suficiente** (gatilhos, *sandbagging*,
   consciência de avaliação). O acesso *white-box* melhora a auditoria.
7. **Destilação não se impede**; só se encarece e se detecta. Marcas forenses são removíveis.
8. **Atestação prova integridade de execução, não qualidade nem segurança do que rodou**
   (Proof-of-Guardrail, Attestable Audits, TCME, whitepaper Anthropic).
9. **Em 2026 o TEE é a única opção prática para LLMs em escala.** ZK é ordens de grandeza mais
   caro, mas a diferença está diminuindo.
10. **O padrão "imagem medida + log *append-only* + cliente que só confia no que está no log"
    está maduro** (PCC, Sigstore) e está sendo levado para ML (Atlas, Attestable Audits).
11. **Verificação só por software ou caixa-preta não basta contra adversário** (quantização passa
    pelos classificadores; o não-determinismo inutiliza logprobs).
12. **Assinatura garante integridade e autenticidade, não proveniência nem segurança** (OMS,
    CoSAI, mantenedores do Sigstore). Todo claim sobre processo, dados ou comportamento é uma
    **atestação separada** sobre o root digest, emitida por um atestador identificado.
13. **Fine-tuning é tratado como "build".** A assinatura do filho é independente e o pai entra
    por hash no AI-SBOM. Como o treino não é reproduzível bit a bit, a aresta pai → filho é só
    **declarada**, a menos que rode em ambiente atestado.
14. **Em GPU CC, computar sai quase de graça; o custo está nas fronteiras**: *bounce buffer*
    CPU↔GPU (~8 GB/s contra ~55 GB/s), submissão de *kernels* e coletivos cifrados. O
    *overhead* vai de 1–5% (modelos grandes, *batch* alto) a 10–30% (pequenos, baixa
    concorrência) e chega a 36–88% com *offload* ou *swapping*.
15. **Uma GPU H100 em modo CC é madura e GA** (Azure, GCP). **Multi-GPU confidencial não
    existe na Azure**, e o Hopper multi-GPU deixa o NVLink em claro.
16. **Os sistemas em produção convergem num padrão**: CVM + GPU CC + atestação + chave
    liberada só após atestação + log de transparência de binários (a Meta inclui pesos) +
    execução sem estado.
17. **Ataques físicos ficam fora do modelo de ameaça de Intel e AMD** (TEE.fail, Battering
    RAM). Ataques corrigíveis se tratam exigindo **TCB mínimo** na política de atestação.
18. **Pickle é inseguro por construção e scanners são contornáveis**: safetensors, *loader*
    com *allowlist* e *sandbox*.

## 8. A lacuna e por que ela interessa

**Pergunta:** alguém já combina fine-tuning confidencial, avaliação de segurança atestada e
liberação condicionada, com o modelo nunca saindo da plataforma?

**Resposta, dentro do que foi buscado: não.** Os vizinhos cobrem pedaços.

| Trabalho | Fine-tuning confidencial/atestado | Avaliação de segurança atestada | Liberação condicionada | Modelo nunca sai |
|---|---|---|---|---|
| Atlas | sim (proveniência com TEE e logs) | não | não | não |
| Attestable Audits | não | sim | parcial (a inferência só roda com o hash auditado) | sim |
| Laminator | atesta treino e configuração | só acurácia e propriedades | não | — |
| AFTUNE | integridade por amostragem | não | não | — |
| ZK verifiable fine-tuning | sim (ZK, TEE opcional, política) | não | não | — |
| Proof-of-Guardrail | não | guardrail na inferência | não | sim |
| Egler et al. (agente auditor) | não (API) | sim, não atestada | não | — |
| API de fine-tuning da OpenAI | gerenciado, não confidencial para terceiros | sim, **não verificável externamente** | sim (bloqueio) | sim |

**Oportunidade:** juntar receita atestada, Juiz atestado comparando base e derivado, chave do
derivado liberada só mediante recibo de aprovação, inferência confinada e tudo num log de
transparência. O que muda em relação ao fine-tuning-as-a-service comercial: **o dono do modelo
não precisa confiar no operador da plataforma**, porque a atestação prova que o Juiz e o portão
rodaram.

## 9. O que isso sugere (insumo, não decisão)

1. **Receitas atestadas em vez de código livre.**
   - O builder oferece receitas fixas (SFT, LoRA, DPO) com hiperparâmetros em faixas permitidas e
     **sem** *hooks* de ativação nem edição direta de pesos.
   - Isso elimina a abliteration *explícita*. A abliteration "por dados" continua possível, então
     o portão segue indispensável.
   - Se o código for livre, assumir atacante *white-box* dentro da CVM.
   - Contradiz em parte o "Dockerfile livre" de D4. Para U1, uma política mais restrita parece
     necessária.
2. **Defesas embutidas na receita** (baratas, não são garantia): mistura de dados de segurança
   (Lisa), KL ou objetivo por token em relação ao original, SafeLoRA ou LoX ao fim do job.
3. **Juiz para U1 em quatro camadas:**
   - **dados**: moderação, detecção de texto cifrado ou não natural, padrão *refuse-then-comply*,
     *outliers*, possíveis gatilhos;
   - **código**: hash atestado da receita;
   - **pesos**: *diff* derivado × base (norma do delta por camada, projeção na direção de recusa,
     deslocamento fora do subespaço de segurança, *features* de persona por SAE, sondas);
   - **comportamento (A4)**: SORRY-Bench, StrongREJECT/HarmBench, XSTest, WMDP, mais ataques
     baratos sobre o derivado (*prefill*, abliteration de teste, *refuse-then-comply*, as
     codificações achadas nos dados, perguntas fora do domínio) e um fine-tuning adversarial
     curto como limite superior.

   Avaliar no pior caso sobre seeds e templates (Qi 2025a). A literatura dá ~56% de detecção com
   1% de FPR como referência realista (Egler). **Estimativa do levantamento, não da literatura:**
   1–5 mil gerações por avaliação, de minutos a horas numa GPU para 7–8B.
4. **Recibo de fine-tuning** (Q2):
   - hash da política assinada pelo dono;
   - digest da imagem da receita com proveniência do builder;
   - medição da CVM e TCB;
   - atestação da GPU **amarrada por nonce gerado na CVM** (TEE.fail);
   - raiz Merkle do dataset e resultado dos filtros;
   - hiperparâmetros, sementes e flags de determinismo;
   - hashes de checkpoints e da trajetória de loss, para reexecução futura.
5. **Recibo do Juiz** (Q3):
   - digest da imagem do Juiz e hash do modelo-juiz;
   - hash e versão da bateria (que pode ser secreta, com *commit-reveal*);
   - métricas do base e do derivado, limiares e decisão;
   - *commitment* das saídas brutas;
   - assinado com a chave atestada e **referenciando o recibo de fine-tuning**: cadeia base →
     derivado → avaliação.
6. **Identidade do modelo** (Q1): manifesto por tensor compatível com OMS/model-signing para base,
   adaptador e derivado. Toda resposta de inferência aponta para Hash(M) e para o recibo do Juiz,
   no padrão do Attestable Audits.
7. **Liberação condicionada por chave** (Q4): o KMS só entrega a chave do derivado a uma imagem de
   *serving* cuja atestação comprove recibo de aprovação válido e incluído no log, como na PCC e
   no whitepaper Anthropic.
8. **Log de transparência para todas as tentativas, inclusive reprovações.** Isso evita a "caça ao
   Juiz", ou seja, submeter fine-tunings até passar.
9. **Defesa depois da liberação:** classificadores de entrada e saída independentes do derivado,
   guardrail atestado na inferência, reavaliação periódica. É a camada que pesos fechados
   permitem e a melhor resposta parcial a gatilhos não detectados.
10. **Anti-destilação:**
    - limites por conta e detecção de padrões;
    - não expor logprobs completos nem *logit bias*;
    - antidistillation sampling para traços de raciocínio;
    - marca d'água só como evidência forense;
    - *fingerprint* nos pesos (Chain & Hash) para rastrear vazamento se o TEE cair.
11. **Limitações a declarar:**
    - backdoors com gatilho e *sandbagging* passam pela avaliação;
    - há ataques de dados indetectáveis ponto a ponto;
    - fine-tuning benigno também degrada, o que exige limiar explícito;
    - atestação ≠ segurança do resultado;
    - ataque físico (TEE.fail) fica fora do modelo de ameaça;
    - ZK é inviável hoje para fine-tuning de LLM.
12. **Posicionamento:** a contribuição defensável é o **desenho integrado e atestado** num
    cenário em que o dono do modelo não confia no operador. Os vizinhos a citar são Atlas,
    Attestable Audits, Laminator, AFTUNE, Egler e Jailbreak-Tuning.
13. **Viabilidade na Azure hoje:** U1 cabe só em `Standard_NCC40ads_H100_v5`, com **uma** H100
    NVL de 94 GB.
    - **Envelope estimado pelo levantamento, não medido:**
      - inferência até ~70B quantizado;
      - LoRA bf16 até ~13–30B;
      - QLoRA até ~70B;
      - fine-tuning completo só em modelos pequenos.
    - **Proibir offload para a CPU**, que derruba a banda: PipeLLM mediu −36% no LoRA com
      offload.
    - **Custo estimado, a partir dos preços da API:**
      - 1 h de inferência: ~US$ 7 (sob demanda) ou ~US$ 1,30 (spot);
      - 4 h de LoRA: ~US$ 28 ou ~US$ 5.

      Spot combina com CVM de uso único se os checkpoints forem selados.
    - **Conta e cota (§4.4.2):** conta gratuita e Azure for Students não servem. Créditos do
      Microsoft for Startups cobrem VMs em tese, mas a cota "Standard NCCads2023 Family vCPUs"
      depende de capacidade. AFMR/AARI não dá VM. Plano B: GCP confidencial a ~US$ 5,30/h. Isso
      responde em parte à pendência 2 do PLANO.
    - Multi-GPU ou modelos maiores ficam como **limitação declarada**.
14. **Política de liberação de chave composta:**
    - relatório SEV-SNP com **TCB mínimo**, contra BadRAM, CacheWarp e RMPocalypse. No Genoa:
      SNP ≥ 0x1B e microcódigo ≥ 0x56 (§4.4.1). Heracles fica como risco residual;
    - digest da imagem vinda do builder atestado;
    - evidência da GPU: CC ligado, RIM conferido, VBIOS fixado como faz a Meta;
    - **vínculo GPU ↔ CVM**: nonce da GPU derivado do `report_data` da CVM, ou o hash do relatório
      da GPU dentro da evidência da CVM. É a resposta ao "empréstimo" de atestação do TEE.fail.
      **Não herdar a política padrão do onboarding da Azure**, que retira a checagem do nonce do
      OCSP (§4.4.2).
15. **Pesos ligados à medição:** raiz dm-verity numa configuração medida (Tinfoil) ou *loader*
    com manifesto e prova de inclusão (Meta). A medição da CPU cobre só o boot, e os pesos
    entram depois.
16. **Uso concreto do model-transparency:**
    - **Hoje:** assinar e verificar o base (OMS); assinar o derivado **offline** pelo método
      `key`.
    - **Proposta nossa:**
      - vincular a chave ao relatório da CVM, que nenhuma ferramenta OMS faz;
      - proveniência, evidência TEE e veredito do Juiz como **atestações separadas** sobre o root
        digest (#586);
      - AI-SBOM com `DESCENDANT_OF`;
      - log privado (Rekor v2 POSIX ou SCITT).
    - **Engenharia:**
      - fixar um commit do `main`, porque as correções de segurança não estão em *release*;
      - rodar a suíte de conformidade OMS;
      - acompanhar #548 (Atlas/TEE) e a SIG E2E Model Provenance da OpenSSF, onde o caso
        "fine-tuning atestado sem abliteration" ainda não aparece e pode virar contribuição.
17. **Limitações a declarar, além do item 11:**
    - HBM não cifrada;
    - metadados e tempo vazando no GPU-CC;
    - firmware NVIDIA, CUDA UMD e paravisor da Azure fechados dentro do TCB;
    - hipervisor malicioso contra SEV-SNP (Heracles, RMPocalypse), mitigado só por TCB
      atualizado;
    - pelo critério do RAND, sem proteção física o DNAT não chega a SL4/SL5.

## 10. Lacunas de cobertura deste levantamento

A segunda rodada resolveu:
- adoção de OMS no HF e no Kaggle (§3.1);
- predicado in-toto para treino (§3.2.1);
- preço do GCP (§4.1);
- AMD Instinct (§4.1);
- Heracles e RMPocalypse (§4.4.1);
- onboarding e créditos na Azure (§4.4.2);
- tamper-resistance (§6.3);
- ZK de LoRA (§5.3);
- marcas d'água e destilação (§6.4).

Continuam em aberto:
- **(a verificar):**
  - se o Rekor v2 consegue listar os descendentes de um digest;
  - texto original do RAND (a página deu 403);
  - detalhes da *confidential inferencing* da Azure (página em JS);
  - se a Azure liga `PAGE_SWAP_DISABLE` e expõe `current_mit_vector`;
  - se patrocínios de pesquisa da Azure têm restrição para SKUs confidenciais;
  - se o site da Kaggle mostra selo de verificação.
- **Não buscados:**
  - RAND WR-A3056-1 (HEMs);
  - o protótipo de "provable inference" da Anthropic, citado só no resumo do workshop
    [AViD 2026](https://www.far.ai/blog/avid-workshop-2026).
