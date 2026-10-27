---
type: decision
status: decided
options: [A-bug-bounty-cadeia-suprimentos, B-modelos-abertos-custodia]
chosen: B-modelos-abertos-custodia
---

# E7 · Decisão de rumo: A (bug bounty) × B (modelos abertos)

**Data:** 2026-10-26 · **Status:** **decidida em 2026-10-27: B**, com o orientador (ver [DECISOES](../DECISOES.md) D1). **Base:**
[E5](https://github.com/lesorty/dnat-identity-validator/blob/archive/juiz-bounty-2026-10/DSN2027/etapas/E5_alt_bug_bounty.md) (A), [E6](E6_alt_modelos_abertos.md) (B),
[GUIA_DSN](../referencias/GUIA_DSN.md) (artigos do DSN 2021–2026), [PLANO](../PLANO.md) (prazos).

**Histórico desta página:** a primeira versão (v1) recomendava **A com escopo cortado** (A = 3,10 ×
B = 3,00). A segunda opinião (§8) derrubou essa recomendação com fatos conferidos no código e nas
fontes. Esta é a v2. A v1 fica no histórico do git.

## 1. O que se decide

Qual alternativa substitui o Juiz generalista como **contribuição principal** do artigo do DSN 2027
(Research Track, regular paper). Prazo da decisão: **até 31/out**, para sobrar ~3,5 semanas de
implementação antes de congelar os resultados (resumo em **25/nov**, artigo em **02/dez**).

**Não se decide aqui:** se o Juiz volta (fora da matriz por escolha do grupo); o híbrido "bounty para
quem quebra o guardrail" (E6 §6 C4), registrado como trabalho futuro; os detalhes do desenho.

## 2. Opções

| | Opção | Tese em uma linha |
|---|---|---|
| **A** | Mercado anônimo de bug bounty sobre a cadeia de suprimentos | Recompensa liberada por **prova de exploit verificada mecanicamente na CVM**; a prova marca na hora todas as apps com o componente no SBOM; os dependentes ficam ocultos dos caçadores |
| **A′** | A com escopo cortado | Mede verificação, propagação e custo; a ocultação dos dependentes e o incentivo ficam só como desenho e modelo analítico |
| **B** | Modelos abertos com guardrails por custódia | Pesos e derivados nunca saem; todo derivado passa por um **portão de não-obliteração** em CPU, contra a referência que só o DNAT guarda |

A′ entra como linha própria porque o corte muda duas notas ao mesmo tempo: a viabilidade sobe e a
novidade cai. A v1 só subia a primeira.

## 3. Critérios e eliminatórios

**Pesos** (escolhidos pelo grupo em 2026-10-26): viabilidade até 02/dez **25%** · novidade **20%** ·
encaixe no DSN e artigos do DSN citáveis **20%** · avaliação mensurável **15%** · reaproveitamento do
que já existe **10%** · risco ético/legal **10%** (nota alta = risco baixo).

**Eliminatórios** (quem cai em um sai, qualquer que seja a nota):
1. Avaliação crível congelada até 25/nov.
2. Publicável sob a exigência de ética do CFP (o PC pode rejeitar por ética insuficiente).
3. Custo dentro da restrição do projeto (sem GPU confidencial cara, API ≤ US$ 100).

As três opções passam, com condição:
- **A:** só se a avaliação usar CVEs **já conhecidas**, sem operar um mercado real.
- **B:** só se usar obliterados públicos quando houver e não publicar pesos nem gerações nocivas.

## 4. Notas (v2, corrigidas pelo conselho)

| Critério (peso) | A | A′ | B |
|---|---|---|---|
| Viabilidade (25%) | **2**: 7,5–9 semanas-pessoa (E5 §7.5) para ~4 disponíveis | **3**: cabe se o corte for real | **3**: ~4 semanas + 1 de escrita (E6 §7.3); o orientador acha otimista em ~1 semana |
| Novidade (20%) | **3**: a ocultação dos dependentes é a ideia nova | **2**: sem ocultação medida sobra "Sealed-Glass Proofs + Dependabot"; há outros vizinhos (Agora, Bug Buster, VeriOSS) | **3**: integração; a custódia fecha a falha da referência forjada que o próprio Hurtado aponta |
| Encaixe no DSN (20%) | **3** (era 4): o DSN aceita cadeia de suprimentos, mas como estudo empírico, não como desenho de mercado; o CFP não nomeia o tema | **3** | **3**: o CFP nomeia robustez de LLM, *jailbreaking* e certificação; nenhum artigo do DSN trata obliteração |
| Avaliação mensurável (15%) | **3** (era 4): presença no SBOM não é verdade de referência (o OCTOPOCS mostra que a PoC muitas vezes não dispara no dependente); RCE e exfiltração pedem rede | **3** | **3**: AUROC e FPR limpos, mas população construída com modelos de 0,5–1,5B |
| Reaproveitamento (10%) | **3** (era 4): só o contrato existe; executor sem rede, seccomp, gVisor, proxy e SBOM são só desenho | **3** | **3**: o núcleo é script de ML, desacoplado do executor; o executor de 512 MiB não roda modelos |
| Risco ético (10%) | **2**: lista de alvos com preço; recompensa sobre componente alheio; fronteira com extorsão | **2**: o corte tira a única mitigação (ocultação) | **4** (era 3): precedente publicado (Hurtado, Arditi NeurIPS'24); nada de alto impacto a divulgar |

**Conta:**
- A = 0,25·2 + 0,20·3 + 0,20·3 + 0,15·3 + 0,10·3 + 0,10·2 = 0,50 + 0,60 + 0,60 + 0,45 + 0,30 + 0,20 = **2,65**
- A′ = 0,25·3 + 0,20·2 + 0,20·3 + 0,15·3 + 0,10·3 + 0,10·2 = 0,75 + 0,40 + 0,60 + 0,45 + 0,30 + 0,20 = **2,70**
- B = 0,25·3 + 0,20·3 + 0,20·3 + 0,15·3 + 0,10·3 + 0,10·4 = 0,75 + 0,60 + 0,60 + 0,45 + 0,30 + 0,40 = **3,10**

## 5. De onde vêm as notas que decidem

| Nota | Fonte | Natureza |
|---|---|---|
| Reaproveitamento A = 3 | `grep` no repo (2026-10-26): nenhum seccomp, gVisor, runsc ou `syft` fora dos documentos; `vm_runtime/executor.py:11-16` é o modo sem isolamento; o contrato não tem escrow (`DnatMarketplace.sol:350`, `receive()` sem contabilizar) | **Conferido** no código |
| Avaliação A = 3 | OCTOPOCS, p. 1: "often fails to verify the propagated vulnerability" | **Conferido** no PDF |
| Novidade A′ = 2 | Agora (DOI 10.1145/3763099) e Ayala et al. 2025 conferidos no OpenAlex; Bug Buster pelo README; DecentralCVE e ExploitArena **não verificados** | Parte conferida |
| Encaixe 3 × 3 | Texto do CFP (lido pelos três assentos); GUIA §1 e §4 | Conferido; o "gosto" do DSN é inferência |
| Ética B = 4 | Hurtado (arXiv 2607.01854) usa abliterações públicas; o CFP pede ética, não comitê | Julgamento do conselho |
| Viabilidade | E5 §7.5 e E6 §7.3 | **Palpite**; nada foi medido |

## 6. Sensibilidade

- **B sobrevive a uma mudança contra ela:** novidade 2 dá 2,90; viabilidade 2 dá 2,85; ética 3 dá
  3,00. Todas ficam acima de A′ (2,70).
- **B só perde com duas mudanças juntas:** viabilidade 2 e novidade 2 dão 2,65, abaixo de A′.
- **A′ só volta ao jogo se a ocultação for medida** (novidade 3): A′ = 2,90, ainda abaixo de B. Um
  experimento de inferência dos dependentes (catálogo público + SBOMs reais) até 25/nov é o que
  faria isso.
- **Pesos:** com as notas da v2, B **domina** A e A′: tem nota igual ou maior em todos os critérios.
  Nenhuma troca de pesos inverte o resultado; só mudanças nas notas.

## 7. Recomendação (v2; a decisão é do grupo)

**B com condições**, decidida depois de um piloto curto e discriminante.

**Piloto (27–29/out, 2–3 dias, só CPU):**
- Base: Qwen2.5-0.5B-Instruct.
- População mínima: 2 abliterações nossas (receita Arditi/Labonne, intensidades diferentes), 2 LoRA
  benignos (Alpaca, GSM8K) e 2–3 abliterados públicos, se houver.
- Calcular os três sinais do portão (bateria de recusa com juiz pequeno, *gap* na direção de recusa do
  base custodiado, energia rank-1 de ΔW) e o **tempo por veredito**.
- **Corte pré-registrado:**
  - nenhum sinal separa abliterados de benignos;
  - ou o veredito passa de 80 min em 4 vCPU.
  Em qualquer desses casos, B não fecha a tempo.
- **Alerta (não é corte):** se a energia rank-1 separar tudo com folga, o resultado é óbvio. Aí o
  valor do artigo tem de vir do atacante adaptativo.

**Condições para B (dos três assentos):**
1. O modelo de ameaça responde "por que não baixar o Qwen do HF?": custódia de pesos de **acesso
   controlado** (o caso U1), com o Qwen só como substituto. Responde também "por que não filtrar
   cada inferência?", com apoio no Prefill (DSN'26).
2. Atacante adaptativo de verdade: treino white-box contra o limiar; *Covert Malicious Finetuning*
   (Halawi et al. 2024); ataques que passam na auditoria de Hurtado e falham sob custódia.
3. **FPR em fine-tuning benigno** (P4/P5) como métrica central; nunca cortar.
4. Vender como **mecanismo de controle de liberação** (FPR/FNR, custo por veredito, *overhead* da
   CVM), no vocabulário de dependabilidade, e não como "mais um detector".
5. Escopo congelado em 31/out: C1 + C2, com C3 numa tabela. Ordem de corte: C3 → extras do
   adaptativo → contrato (F2). Escrita em paralelo desde a primeira semana.
6. Opcional: um ponto em 7–8B (~US$ 13 de GPU confidencial).

**Se o piloto de B falhar:** A reformulado como **estudo de medição** "presença no SBOM × disparo
real" em imagens OCI, no formato empírico do DSN (sugestão do assento revisor). Não é a A do
mercado; precisaria de uma checagem própria antes.

**O que a escolha de B muda nas decisões vigentes:** D1 (contribuição principal), D2 (o Juiz vira o
portão, com checkpoint como entrada) e D3 (U1 deixa de ser só motivação).

**Precisa de gente, não de agente:**
- O orientador propôs o U1 e precisa aceitar B como DSN, e não como SaTML.
- Quem do grupo conduz experimentos de ML.
- O crédito Azure (PLANO §5.2).

## 8. Segunda opinião (llm-council, 2026-10-26)

**Que conselho foi este:** três subagentes em contextos novos, sem ver uns aos outros, cada um com
uma postura. Dois rodaram no Opus 5.5 e um no Sonnet 5.5. O assento que rodaria no Fable falhou por
falta de créditos e foi refeito no Opus. São todos modelos da mesma família e compartilham pontos
cegos, então a concordância entre eles vale menos do que valeria entre modelos diferentes. Os fatos
abaixo valem pelo que foi conferido, não pela concordância.

| Assento | Modelo | Posição | Confiança |
|---|---|---|---|
| Revisor do PC do DSN | Opus 5.5 | B com condições | 0,60 |
| Orientador, foco no prazo | Sonnet 5.5 | B com condições | 0,65 |
| Cético de novidade e ética | Opus 5.5 | B com condições (pouca confiança) | 0,60 que A′ está errado; 0,40 que B é a melhor saída |

**Onde os três concordam (e o que conferi):**
- **O corte esvazia A.** O que A′ mede não é novo, e o que é novo (ocultação, vault) não é medido.
- **O piloto da v1 não discrimina.** O ARVO reproduz só 81% das vulnerabilidades ✔ (resumo do
  arXiv). Com isso, a chance de ≥ 15 de 20 passarem é 0,84 ✔ (binomial calculada). O piloto testava
  o ARVO, não a tese.
- **O reaproveitamento de A era desenho.** ✔ (grep no código, §5).
- **O CFP nomeia robustez de LLM, mas não cadeia de suprimentos.** ✔ (nos três assentos; o GUIA §1
  já dizia).
- **A aritmética da v1 estava certa.** ✔ (refeita pelos três).

**Divergências:**
- **Novidade de B.** O cético dá 2: o Hurtado já nomeia a referência forjada, e a custódia é o
  conserto óbvio. Os outros dão 3, se houver atacante adaptativo. Mesmo com 2, B fica à frente (§6).
- **Viabilidade de B.** O orientador acha a estimativa otimista em ~1 semana (conversão para
  GGUF/INT4, P6, LoRA em CPU). O piloto mede isso.
- **Futuro de A.** O revisor vê valor em A como estudo de medição; o cético, só se a ocultação for
  medida.

**Correções de fato que entraram em E5, E6 e no GUIA:**
- E5: o CFP **não** exige comitê de ética, só discutir ética e declarar revisão quando aplicável;
  as linhas citadas em `executor.py` não são seccomp nem gVisor; as linhas do `contentHash` e do
  `manifestUri` estavam erradas; o ARVO tem > 6.100 casos com ~81% reproduzidos.
- E6 e GUIA: o Prefill passa de 99% "em vários modelos", não nos 14; o Hurtado não dá a faixa
  1,5B–8B; o código "sob pedido" não aparece no arXiv.
- Trabalhos novos registrados:
  - em A: Agora, Ayala et al., VeriOSS, Bug Buster, DecentralCVE, ExploitArena e Dependabot;
  - em B: *Covert Malicious Finetuning* e Sophon.

**Ainda não verificado:**
- DecentralCVE e ExploitArena;
- o tempo por veredito em CPU;
- se há abliterados públicos de Qwen pequenos no HF (o orientador diz que sim, sem conferência minha);
- a disponibilidade do código de Hurtado;
- o venue do Halawi (OpenAlex lista só o arXiv).

**Síntese do juiz:** B com condições, confiança **0,6**. A vantagem de B é relativa: as duas têm
chance absoluta modesta no prazo, e o piloto de 27–29/out é o que transforma essa proposta em
decisão.
