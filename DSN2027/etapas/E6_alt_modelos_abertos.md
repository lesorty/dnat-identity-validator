# E6 · Alternativa B: controle de modelos abertos (confiabilidade de LLMs)

**Data:** 2026-10-26 · **Status:** proposta para comparação com a alternativa A. **Nada aqui é decisão.**
**Base:** [E11](E11_heranca_juiz.md) §1–§2 (U1; antes JUIZ_IA.md, na tag `archive/juiz-bounty-2026-10`), [DECISOES.md](../DECISOES.md) D2–D4,
[pesquisa/02](../../pesquisa/02_transparencia_execucao_llm.md), [pesquisa/03](../../pesquisa/03_confiabilidade_llm.md).
**Convenções:** ✔ = conferido na fonte primária (nesta rodada ou em pesquisa/02–03, citado);
**(a verificar)** = não conferido. Prazo: hoje 26/out; resumo 25/nov; artigo 02/dez (37 dias).

---

## 1. Tese em uma frase

Em vez de embutir nos pesos guardrails que caem em dezenas de passos de fine-tuning, o DNAT
garante a recusa de um modelo aberto **por custódia**: os pesos são um ativo cifrado que nunca
sai, todo derivado (fine-tuning, edição) passa por um **portão de liberação barato, em CPU e sem
treino**, que detecta obliteração contra a referência atestada que só a plataforma tem, e a saída
de cada job é checada contra exportação de pesos.

## 2. Atores e fluxo

| Ator | Papel | No DNAT hoje |
|---|---|---|
| **Dono do modelo** | Deposita pesos (safetensors) + política (`pesos-modelo`: uso e treino permitidos, sem obliteração, sem exportação) | Dono de ativo `Dataset` (`DnatMarketplace.sol:28-31`) |
| **Usuário** | Envia script de uso ou treino (imagem OCI) e, se quiser, seus dados de treino | Dono de ativo `Application` |
| **DNAT** | Builder atestado, CVM de uso único, portão de liberação, portão de saída, registro de linhagem | Contrato + executor (D4) |
| **Portão de liberação** (Juiz para U1) | App do sistema na whitelist (D2) que julga o **derivado**, não o código | Novo |
| **Caçador de bounty** (híbrido com A, §6 C4) | Tenta produzir derivado obliterado que passa no portão | Novo |

**Fluxo**
1. Dono registra o modelo base; o DNAT guarda o **digest OMS** do base como referência atestada
   (pesquisa/02 §3.4).
2. Usuário compra acesso `(modelo, script)` (`DnatMarketplace.sol:214-265`) e o job roda numa
   CVM de uso único, container sem rede (D4); os pesos entram montados como um dataset.
3. Se o job só faz **inferência**: a saída passa pelo portão de saída (tamanho, cópia de pesos,
   quotas contra destilação) e sai.
4. Se o job produz um **derivado** (LoRA, pesos editados): o derivado **não sai**; fica cifrado no
   DNAT, ligado ao pai. O portão de liberação compara derivado × base (§7). Aprovado → o derivado
   vira ativo novo, **não exportável**, usável só em novos jobs. Reprovado → descartado e registrado.
5. Toda tentativa (aprovada ou não) entra num log, para evitar "caça ao portão" (pesquisa/02 §9 item 8).

## 3. Modelo de ameaça

| Item | Hipótese |
|---|---|
| **Adversário principal** | Usuário com script arbitrário (Dockerfile livre, D4) e **acesso white-box aos pesos dentro do container**: pode editar pesos (abliteration rank-1), treinar com dados nocivos, ou tentar copiar os pesos para a saída |
| **Objetivos do adversário** | (O1) obter um modelo sem recusas **utilizável**; (O2) exportar pesos ou derivado; (O3) destilar o modelo por consultas; (O4) burlar o portão (derivado obliterado aprovado) |
| **Canal de saída** | Só a saída legítima do job (container sem rede, a CVM só fala com o DNAT, D4/E2c §2). Logo O1 só vale se o derivado for **liberado**, e O2/O3 só passam pela saída |
| **Confiáveis** | CVM SEV-SNP e sua atestação; builder atestado (D4); operador do DNAT como ponto único (limitação, D3); o próprio portão (código e modelo-juiz fixados por hash) |
| **Fora do escopo** | Ataque físico (TEE.fail, S&P'26 ✔, pesquisa/02 §4.4); canais laterais (D3); conluio do operador; backdoors com gatilho e *sandbagging* (passam por qualquer bateria finita, pesquisa/02 §6.2) |
| **Propriedade alvo** | (G1) nenhum derivado com recusa abaixo do limiar é liberado; (G2) nenhum byte de peso sai em forma recuperável; (G3) taxa de falso positivo baixa para fine-tuning benigno |

**Ponto que muda tudo:** o atacante white-box mais forte do artigo de Hurtado tem de **forjar a
referência** para escapar sem treinar ✔ ([arXiv 2607.01854](https://arxiv.org/abs/2607.01854)).
No DNAT a referência é o base que o próprio DNAT custodia: esse ataque some por construção.

## 4. O que reaproveita do DNAT

| Peça | Onde | Uso na alternativa B |
|---|---|---|
| Ativo cifrado + direito de uso por par (ativo, app) | `DnatMarketplace.sol:33-57`, `:214-265`; `asset_envelope.js:22-45` (AES-256-GCM) | Pesos = ativo `Dataset`; script = `Application`. Nada muda no contrato para o caso de inferência |
| Revogação do ativo | `DnatMarketplace.sol:183-191` | Dono revoga o base; falta cascata para derivados (§5) |
| CVM de uso único, container sem rede, CVM só fala com o DNAT | **D4**, E2c §2 | Isola o script white-box; saída é o único canal (G2) |
| Todo build atestado, imagem com digest | **D4**, E2b §E2b.4 (`REPORT_DATA = hash(chave ‖ declaração)`) | Mesmo padrão assina o derivado e o recibo do portão (pesquisa/02 §3.4) |
| Juiz como app na whitelist; veredito em níveis; cache por hash | **D2**, JUIZ §9.5 | O portão de liberação é **o Juiz com outro tipo de entrada** (checkpoint em vez de código) |
| L2 com variação do segredo; L4 portão de saída | JUIZ §9.4, §8 | Contra exportação: trocar **canários nos pesos** entre execuções e ver se a saída os determina |
| Tag `pesos-modelo` | JUIZ §3 | Já prevista: "exportação de pesos; remoção de guardrails" |
| Vazamento só pela saída; canais laterais fora | **D3** | Mesmo recorte |
| Volume de saída limitado (64 MB) | `vm_runtime/vm/run-vm.sh:149` | Barreira acidental: o base (≥ 1 GB) não cabe, mas **um LoRA de poucos MB cabe** |

**Decisões:** D2 (Juiz como app) e D4 (execução e build) entram inteiras. **D3 muda:** hoje U1 é
"só motivação"; na alternativa B vira o caso principal.

## 5. O que falta construir

| # | Peça | Esforço | Nota |
|---|---|---|---|
| F1 | **Executor com memória e tempo para modelos**: hoje a microVM tem 1 vCPU e 512 MiB (`run-vm.sh:175`), timeout de 600 s (`vm_runtime/rootfs/runner:121`) e 720 s (`vm_runtime/executor.py:55`); disco de entrada de 64 MB (`run-vm.sh:148`) | Baixo, se for o modo direto na CVM (PLANO §2) | O executor OCI de D4 ainda não está no código (só desenho) |
| F2 | **Derivado como ativo não exportável com linhagem**: o `Asset` não tem pai, flag de exportação nem veredito (`DnatMarketplace.sol:33-57`); só o próprio dono registra (`:126-159`) | Baixo/médio (Solidity) | Campos `parentId`, `exportable=false`, hash do recibo; registro feito pelo DNAT |
| F3 | **Portão de liberação**: bateria de recusa + direção de recusa + energia rank-1 do ΔW (§7) | Médio | Núcleo da contribuição |
| F4 | **Portão de saída para pesos**: limite de tamanho, hash de blocos dos tensores, canário nos pesos com variação entre execuções | Baixo/médio | Reaproveita L2/L4 |
| F5 | **Quotas de inferência** contra destilação (tokens por conta, sem logprobs completos) | Baixo (só política) | Eficácia limitada (§9) |
| F6 | **Chave por ativo** liberada só para CVM atestada: hoje a chave é única da plataforma, com valor padrão de desenvolvimento (`asset_envelope.js:13`, `:18-20`) | Fora do prazo | Atestação segue implícita (D3); declarar |
| F7 | Bounty on-chain (C4) | Médio | Opcional; pode ficar como desenho |

## 6. Contribuições candidatas

| # | Contribuição | Prova no artigo | Força |
|---|---|---|---|
| **C1** | **Guardrail por custódia**: arquitetura em que pesos e derivados nunca saem, e todo derivado passa por portão de liberação contra a referência atestada (fecha o ataque de referência forjada de Hurtado) | Desenho + análise do modelo de ameaça + integração no DNAT | Média: é integração, mas com argumento de segurança claro |
| **C2** | **Portão de não-obliteração barato** (CPU, sem treino), avaliado numa população de derivados com negativos difíceis e **atacante adaptativo**; mostra que o mesmo script gera derivado benigno ou obliterado (P5), então julgar código não basta | AUROC, TPR a FPR 1–5%, custo por veredito | Alta, se o atacante adaptativo for sério (Qi et al. 2025a, pesquisa/02 §6.2) |
| **C3** | **Controle de exportação de pesos** pela saída legítima, tratando pesos como dataset (canários nos pesos + variação entre execuções, JUIZ §9.4) | Taxa de detecção de apps que exportam base, LoRA, versão quantizada ou codificada | Média; liga B ao Juiz já desenhado |
| **C4** | **Híbrido com A: bounty para quem quebra o portão**, com verdade de referência mecânica (bateria secreta, estilo CTF de JUIZ §9.2) e pagamento no contrato | Desenho; no máximo um piloto interno | Baixa no prazo; boa como trabalho futuro |

**Recorte mínimo defensável:** C1 + C2, com C3 numa tabela pequena.

## 7. Avaliação possível até 02/dez

**Restrição do projeto:** sem orçamento para GPU confidencial cara nem fine-tuning grande
(pesquisa/03, cabeçalho e §8). A avaliação abaixo cabe em **CPU**.

### 7.1 Viabilidade em CPU (o que sustenta o plano)

| Fato | Fonte |
|---|---|
| Abliteration não treina: direção = diferença de médias de ativações em ≤ 256 + 256 prompts, depois edição rank-1 | Arditi et al., NeurIPS 2024 ✔ (pesquisa/03); receita de [Labonne, HF blog](https://huggingface.co/blog/mlabonne/abliteration) ✔ |
| O detector de Hurtado roda num laptop (Apple M4 Max, MPS); 500 pares de prompts; AUROC 0,95 em 273 checkpoints; acurácia balanceada 0,89 com FPR 0,11 em famílias novas. Correções do conselho (E7 §8): o artigo não dá a faixa "1,5B a 8B" (o 8B é o guard usado como oráculo), e o "código sob pedido" não aparece na página do arXiv (**a verificar**) | [arXiv 2607.01854](https://arxiv.org/html/2607.01854) ✔ |
| CVM SEV-SNP sem GPU (DC4as_v5): US$ 0,172/h sob demanda, US$ 0,036/h spot | pesquisa/03 §8 ✔ (Retail Prices API) |
| CPU TEE custa < 10% de vazão no Llama2-7B; em lote pequeno a GPU CC sai até 100% mais cara | Chrapek et al. 2025, pesquisa/03 ✔ |
| GPU CC na Azure: só `NCC40ads_H100_v5`, 1× H100, US$ 6,98/h (eastus2), spot US$ 1,29/h; sem multi-GPU; conta de estudante não serve | pesquisa/02 §4.1, §4.4.2 (SKU ✔; preços da API em 2026-10-20) |
| Juízes pequenos de recusa: Llama Guard 3-1B-INT4 (440 MB, CPU); StrongREJECT com juiz Gemma-2B; SORRY-Bench com juiz 7B | pesquisa/03 §4 ✔ |

### 7.2 Experimento

**Modelos base:** Qwen2.5-0.5B-Instruct e Qwen2.5-1.5B-Instruct (Apache-2.0 nos tamanhos ≠ 3B e
72B, **a verificar no LICENSE do HF**); terceira família opcional: Llama-3.2-1B-Instruct
(licença **a verificar**). **Gemma fica fora** da geração de ataques (§9, licença).

**População de derivados (~60–100 checkpoints por base):**

| Grupo | Como | Rótulo |
|---|---|---|
| P1 Abliteration | Receita de Arditi, variando camada e intensidade; CPU, minutos | Obliterado |
| P2 Obliterados públicos | Checkpoints abliterated do HF para as mesmas bases (**disponibilidade a verificar**); evita criarmos todos | Obliterado |
| P3 Fine-tuning nocivo | LoRA com 10–100 exemplos nocivos públicos (receita de Qi et al., ICLR 2024, pesquisa/02 §6.2) | Obliterado |
| P4 Fine-tuning benigno | LoRA em Alpaca, GSM8K, SQL | Benigno (negativo difícil) |
| P5 Benigno que degrada | Mesma receita de P4 com dados que Qi et al. mostram degradar a recusa | Zona cinza: reportar à parte |
| P6 **Adaptativo** | Abliteration + LoRA de "cura"; *refuse-then-comply* (Kazdan, ICLR 2026, pesquisa/02); treino para passar no limiar de energia (falha 2 de Hurtado) | Obliterado |

**Mesmo código, dano diferente:** P3, P4 e P5 usam **o mesmo `train.py`**, mudando só os dados.
Isso demonstra P5 do JUIZ e motiva julgar o resultado.

**Portão de liberação (três sinais, z-soma como em Hurtado):**
- S1 bateria de recusa: subconjunto do StrongREJECT (nocivos) + XSTest (seguros, *over-refusal*),
  juiz pequeno em CPU; parte da bateria **secreta** (consciência de avaliação, Needham et al.,
  pesquisa/02 §5.2);
- S2 *gap* de recusa nas ativações, na direção calculada **do base custodiado**;
- S3 energia rank-1 de ΔW = W_base − W_derivado (`o_proj`, `down_proj`, camadas do meio).

**Portão de saída (C3):** apps que tentam exportar base, LoRA, pesos quantizados INT4, base64,
dígitos menos significativos; detecção por tamanho, hash de blocos e **canário nos pesos** (o DNAT
troca valores numa linha não usada da embedding entre duas execuções e testa se a saída muda, como
em JUIZ §9.4 item 3).

**Métricas:** AUROC; TPR a FPR 1% e 5%; acurácia balanceada em família não vista; utilidade
preservada dos benignos (acurácia da tarefa); rodadas até o adaptativo passar; custo por veredito
(CPU-min, US$); *overhead* CVM × VM comum; detecção de exportação por técnica.

### 7.3 Esforço e custo

| Semana | Trabalho |
|---|---|
| 27/out–02/nov | Bases, bateria, script de abliteration, P1/P2/P4 |
| 03–09/nov | S1–S3 e z-soma; P3/P5; portão de saída |
| 10–16/nov | P6 adaptativo; rodar no modo direto em CVM SEV-SNP; derivado não exportável no contrato (F2) |
| 17–25/nov | Congelar resultados; **resumo em 25/nov** |
| 26/nov–02/dez | Escrita (o rascunho atual é do Juiz; reescrever introdução, ameaça e avaliação) |

**Total:** ~4 semanas de implementação para uma pessoa, mais 1 de escrita. Apertado: não cabe junto
com a batalha do JUIZ §6.1.

| Item | Estimativa (nossa, não medida) |
|---|---|
| Portão por checkpoint em CPU (≈ 550 gerações × ~128 tokens com modelo de 1,5B em INT4 no llama.cpp) | 40–80 min em 4 vCPU **(a verificar no piloto)** |
| 100–200 h de CVM DC4as_v5 | US$ 4–8 em spot; US$ 17–34 sob demanda |
| LoRA de P3–P5 em 0,5–1,5B | CPU (horas) ou GPU comum gratuita (Colab); os dados são públicos, não precisam de TEE |
| Opcional: ~10 h de H100 CC spot para um 7–8B | ~US$ 13 (pesquisa/02 §9 item 13) |
| **Total** | **< US$ 50**, dentro da restrição |

## 8. Trabalhos relacionados e lacuna

| Trabalho | O que faz | O que falta para B |
|---|---|---|
| Arditi et al., NeurIPS 2024 ✔ (pesquisa/03) | Recusa mediada por uma direção; base da abliteration e da medição | Não é sistema |
| [Hurtado, "Has This Checkpoint Been Abliterated?"](https://arxiv.org/abs/2607.01854) ✔ (preprint, jul/2026) | Detector de dois sinais; AUROC 0,95; falhas: referência forjada e treino white-box contra o limiar | Pressupõe referência atestada e não tem custódia: **o DNAT fornece as duas** |
| Messenger (AMS), IEEE Access 2026 ✔ (pesquisa/03) | Geometria das ativações detecta abliteration; fine-tuning só comportamental escapa | Mesmo limite para S2 |
| Egler, Schulman, Carlini 2025 ✔ (pesquisa/02 §6.2) | Agente auditor com dados + modelo pré + pós: 56,2% de detecção a 1% de FPR | Via API, sem atestação nem custódia; referência de desempenho realista |
| TAR ([Tamirisa et al., ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/fc49a629d33bc2461ed7a715ce44da68-Abstract-Conference.html)); [Vaccine (Huang et al., NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/hash/873c86d9a979ab80d8e2919510d4446b-Abstract.html); Booster, RepNoise, Antidote (pesquisa/02 §6.2) | Defesas embutidas nos pesos contra fine-tuning nocivo; TAR alega resistir a centenas de passos **(a verificar a versão final)** | Quebradas por mudar seed, LR ou template ([Qi et al., ICLR 2025](https://arxiv.org/abs/2412.07097), pesquisa/02); [Virus](https://arxiv.org/abs/2501.17433) ✔ fura a moderação de dados de treino; ablação de recusa sem treino derruba defesas (Yu e Ye, ICML 2026 WS, pesquisa/02 §6.3) |
| [Casper et al., TMLR 2026](https://arxiv.org/abs/2608.07514) (OpenAlex lista só o arXiv; **venue a verificar**); UK AISI 2025 (pesquisa/02 §6.3) | Consenso: salvaguardas nos pesos caem em dezenas de passos; "nenhuma solução atual dá garantia rígida" | **Justifica custódia no lugar de salvaguarda nos pesos** |
| Thinking Machines, "A Safe Path to Open Weights" (2026, pesquisa/02 §6.3) | Fine-tuning hospedado com monitoramento e revogação como degrau antes dos pesos | Sem atestação: o dono confia no operador |
| Attestable Audits ([Schnabl et al.](https://arxiv.org/abs/2506.23706) ✔, ICML WS; o arXiv diz "ICML 2024", pesquisa/02 diz 2025: **a verificar**) | Benchmarks de segurança em TEE com resultado atestado | Audita um modelo fixo; não trata derivados nem exportação |
| [ObfuscaTune](https://arxiv.org/abs/2407.02960) ✔ (preprint 2024); [DistilLock](https://arxiv.org/abs/2510.16716) (NeurIPS 2025 **a verificar**) | Fine-tuning e inferência de LLM proprietário com TEE + ofuscação; professor em enclave contra destilação | Protegem o sigilo dos pesos, **não a recusa** do derivado |
| Atlas, Laminator, AFTUNE (pesquisa/02 §8) | Proveniência e integridade de treino em TEE | Sem avaliação de segurança nem liberação condicionada |
| API de fine-tuning da OpenAI (pesquisa/02 §8) | Moderação e bloqueio do derivado | Não verificável por terceiros |

**Lacuna (dentro do que foi buscado, não prova de novidade):** não achamos trabalho que junte
**custódia atestada de pesos abertos + portão de liberação de derivados contra referência que só a
plataforma tem + controle de exportação pela saída**, avaliado contra atacante adaptativo. A
pesquisa/02 §8 chegou à mesma conclusão por outro caminho. **Risco de novidade:** os blocos são
conhecidos; a contribuição é a integração e a avaliação, e um revisor pode lê-la como incremental.

**Âncoras no próprio DSN** (detalhes em [GUIA_DSN.md](../referencias/GUIA_DSN.md); acrescentadas na
consolidação de 2026-10-26):
- **[44] Prefill, DSN'26** (DOI 10.1109/DSN69566.2026.00054): com estratégia adaptativa, o
  *response prefill* passa de 99% de sucesso em vários dos 14 modelos testados (PDF conferido); o controle precisa estar na **interface de inferência**, não só nos pesos.
  Apoia a custódia (o DNAT controla a interface). O PDF é o preprint com título anterior.
- **[50] LymphNode, DSN'26**: controle de acesso embutido no modelo; contraste direto "proteção no
  modelo × proteção na infraestrutura". DOI a verificar.
- **[29] Plinius, DSN'21**: treino de ML em SGX; precedente de treino confidencial.
- **[48] BProm, DSN'25**: certificar modelo caixa-preta (backdoor) sem ver o interior; papel
  parecido com o portão de liberação.
- **[36] AnBridge, DSN'26**: IA em VM protegida; **[45] prompt polimórfico, DSN-S'25** e
  **[47] Aegis, DSN-S'26**: o DSN aceita guardrails de LLM como tema de sistema.
- **Faltam no modelo de ameaça e na população P6** (achados na segunda opinião, E7 §8):
  [Covert Malicious Finetuning, Halawi et al. 2024](https://arxiv.org/abs/2406.20053) ✔ (a saída
  codificada passa por uma bateria em texto plano) e [Sophon, S&P'24](https://doi.org/10.1109/sp54263.2024.00234)
  ✔ (modelo não ajustável, outra defesa embutida nos pesos).
- Não há, na amostra, artigo do DSN sobre obliteração ou fine-tuning nocivo: o núcleo de C2 vem de
  ML (NeurIPS/ICLR), o que confirma a leitura franca do §10.

## 9. Riscos

| Tipo | Risco | Mitigação / declaração |
|---|---|---|
| Técnico | **Fine-tuning legítimo e obliteração têm o mesmo código** (JUIZ §2, P5) | É a premissa do desenho: julgar o derivado, não o script |
| Técnico | Fine-tuning benigno também degrada a recusa (10 exemplos, < US$ 0,20; Qi et al. 2024, pesquisa/02 §6.2) | Limiar explícito; P5 reportado como zona cinza; FPR é métrica central |
| Técnico | Atacante white-box treina para passar no limiar (falha 2 de Hurtado ✔); backdoor com gatilho passa | Bateria parcialmente secreta; S1 comportamental além de S2/S3; declarar limite |
| Técnico | **Destilação**: consultas suficientes copiam o comportamento sem tocar nos pesos; marca d'água é removível (pesquisa/02 §6.4) | Quotas e sem logprobs; declarar como limitação; JUIZ §2 já alerta que o portão pode inviabilizar o caso |
| Técnico | Pesos saem comprimidos (LoRA, INT4) pela saída legítima; 64 MB de saída comportam um LoRA (`run-vm.sh:149`) | C3; tamanho máximo pela tag |
| Técnico | Executor OCI ainda não existe no código; microVM com 512 MiB (`run-vm.sh:175`) | Modo direto na CVM (F1) |
| Ético | Criar modelos obliterados e gerar texto nocivo | Usar obliterados públicos quando houver; bases pequenas; não publicar pesos nem gerações nocivas (como Hurtado); seção de ética exigida pelo CFP ✔ |
| Legal/licença | Gemma proíbe "Attempts to override or circumvent safety filters" (Prohibited Use Policy §2.4) ✔ ([ai.google.dev](https://ai.google.dev/gemma/prohibited_use_policy)); hospedar como serviço conta como distribuição nos termos do Gemma **(a verificar)** | Não gerar ataques em Gemma. **Argumento a favor:** o portão **aplica** a licença do dono |
| Legal/licença | Qwen2.5 é Apache-2.0 na maioria dos tamanhos **(a verificar)**: modificar é permitido, então "proibir obliteração" é política do dono (tag), não da licença; Llama AUP **(a verificar)** | Tag `pesos-modelo` explícita |
| Custo | GPU CC (~US$ 7/h) fora do orçamento | Tudo em CPU (§7.3); GPU só opcional |
| Prazo | Muda D3 e a contribuição principal com 30 dias de antecedência; o rascunho do artigo é do Juiz | Recorte C1 + C2; C3 mínimo; C4 só desenho |

## 10. Encaixe no CFP do DSN 2027

Conferido em 2026-10-26 ✔ ([CFP](https://dsn2027-berlin.github.io/call-for-contributions/)).

| Tópico do CFP | Como B encaixa |
|---|---|
| *AI/ML for resilient systems*: "robustness issues in AI/ML/LLM systems" | Recusa como propriedade a manter sob modificação do modelo |
| *Agentic AI systems*: alinhamento e segurança, verificação e certificação, *jailbreaking* | Portão de liberação = certificação do derivado; bounty = *jailbreak* do portão |
| *Hardware*: TEEs | Custódia em CVM SEV-SNP |
| *Distributed ledgers* | Linhagem e bounty no contrato (opcional) |
| Ética | CFP exige discutir questões éticas e, para vulnerabilidades de alto impacto, os passos tomados ✔ |

**Leitura franca:** o núcleo de C2 é segurança de ML; o DSN quer sistema + avaliação de
dependabilidade. O artigo precisa vender **custódia + portão** como mecanismo de sistema, com
FPR/FNR e custo, e não como mais um detector. Público alternativo natural: SaTML, workshops de ML.

## 11. Perguntas em aberto

1. B substitui o Juiz ou vira **um tipo de entrada do Juiz** (checkpoint em vez de código), mantendo D2?
2. Script livre (D4, Dockerfile livre) ou **receitas fixas** de treino para U1 (pesquisa/02 §9 item 1)?
3. Qual limiar de recusa define "obliteração"? Quem fixa: o dono (tag) ou a plataforma?
4. Inferência pura entra no artigo (com quotas contra destilação) ou só treino + liberação?
5. Bounty (C4) entra como desenho no artigo ou só como trabalho futuro da ponte com A?
6. Só CPU, ou um ponto de GPU CC (~US$ 13) para mostrar 7–8B?
7. Pedir o código e o registro de Hurtado ("available on request") ou reimplementar os dois sinais?
8. Há obliterados públicos suficientes de Qwen2.5-0.5B/1.5B no HF para P2?
9. Licenças: confirmar Qwen2.5 (LICENSE por tamanho) e a AUP do Llama 3.2 antes de escolher as bases.

---

### Anexo: ponte com A (bounty) — precedentes

| Programa | O que paga | Fonte |
|---|---|---|
| Anthropic Model Safety Bug Bounty (ago/2024, HackerOne, convite) | Até US$ 15 mil por *jailbreak* universal em CBRN/ciber | [anthropic.com](https://www.anthropic.com/news/model-safety-bug-bounty) ✔ |
| Desafio público dos Constitutional Classifiers (fev/2025) | Até US$ 15 mil; ~180 participantes, nenhum *jailbreak* universal relatado | Imprensa **(a verificar na fonte da Anthropic)** |
| OpenAI Bio Bug Bounty (GPT-5 → GPT-5.5/5.6) | US$ 25 mil, depois até US$ 50 mil; convite e NDA | [openai.com](https://openai.com/index/bio-bug-bounty) (403 ao abrir: **a verificar**) |
| HackAPrompt 2.0 (2025) | US$ 100 mil a 500 mil conforme a fonte | [Learn Prompting](https://newsletter.learnprompting.org/p/new-hackaprompt-2-0-x-openai-largest-ai-red-teaming-competition-with-100-000-in-prizes-d426) **(a verificar)** |
| Gray Swan Arena, Agent Red-Teaming (mar–abr/2025) | US$ 171,8 mil; UK AISI, OpenAI, Anthropic, GDM | [grayswan.ai](https://app.grayswan.ai/arena/challenge/agent-red-teaming) (429 ao abrir: **a verificar**) |

**Híbrido proposto:** o dono põe um prêmio em custódia no contrato; o caçador submete script + dados;
se o derivado **passa no portão** e depois **falha na bateria secreta** (verdade mecânica, estilo
CTF do JUIZ §9.2), o contrato paga. Diferença dos precedentes: o alvo é o **portão de um modelo
aberto**, não um modelo fechado, e a verificação é automática e atestada.
