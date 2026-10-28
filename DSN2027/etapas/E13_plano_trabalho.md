# E13 · Plano de trabalho consolidado

**Data:** 2026-10-27 · **Status:** proposta de plano, revisada uma vez por um revisor
independente (13 achados, todos incorporados); nada foi implementado nem medido.
**Base:** [E10](E10_problema.md) §5 (problema), [D5](../DECISOES.md) e
[E12](E12_base_teorica.md) (base teórica A1–A5), [E9](E9_testes_validos.md) (validade),
[E8](E8_alinhamento_dsn.md) §9 (forma DSN), [E6](E6_alt_modelos_abertos.md) §7 e
[E7](E7_decisao_rumo.md) §7 (população e piloto).
**Substitui:** o esboço da E12 §5 e o cronograma do [PLANO](../PLANO.md) §1, que passa a apontar
para cá.

---

## 0. O plano em uma página

**Meta:** submeter ao DSN 2027 em **02/dez/2026** (resumo em **25/nov**) um artigo que mostra,
com avaliação de dependabilidade, que **custódia + portão de liberação** impedem a liberação de
derivados que perderam a recusa, com falso alarme baixo para o fine-tuning legítimo.

**Métrica-título:** **taxa de liberação silenciosa**, a fração de derivados comprometidos (C)
que o portão aprova (E8 §9.3; E9 B1).

**O que o artigo precisa demonstrar, e com quê:**

| Afirmação (D5) | O que o artigo mostra | Como | RQ |
|---|---|---|---|
| A1 a recusa não sobrevive à derivação | Nossa população F1–F3 perde a recusa e mantém a utilidade, como Qi 2024 e Arditi descrevem | Validação da população (§3.2) | — |
| A2 proteger nos pesos não basta | Só citação (Qi 2025, Casper, Kuo) | — | — |
| A3 detectar só funciona sob custódia | Liberação silenciosa e falso alarme do portão contra as linhas de base; a ablação **sem custódia** mostra a referência forjada passando | §3.3, §3.6 | RQ1, RQ5 |
| A4 o derivado tenta enganar o portão | Taxa de escape do atacante adaptativo | §3.6 | RQ2, RQ4 |
| A5 medida válida e população representativa | Verdade de referência independente; recusa excessiva em pedidos seguros; teste cego com derivados de campo | §3.4, §3.5 | RQ3 |

**Marcos de decisão (go/no-go):** decisões do grupo em 02/nov, piloto em 01/nov, calibração em
09/nov, integração em 16/nov e congelamento em 23/nov (§5).

**Ordem de corte** (unifica PLANO §1 e E10 §5):
1. o bounty vira só desenho;
2. o recibo no contrato vira um log assinado pela CVM1 (o derivado continua retido, cifrado no IPFS);
3. a família não vista roda em escala menor;
4. os ataques adaptativos além do mínimo saem.

**Inegociáveis:** F1–F3, verdade de referência independente, falso alarme em fine-tuning benigno,
teste cego de campo, linha de base e o **atacante adaptativo mínimo**: treino contra o limiar e
referência forjada (mais CMFT, se o piloto mostrar que é viável).

---

## 1. Escopo

**Dentro (contribuições da ARTIGO.md):**
- **C1 · Custódia + portão:** pesos e derivados não saem; todo derivado passa pelo portão antes
  de virar ativo; reprovado não sai; liberado pode ser revogado pelo operador.
- **C2 · Avaliação de dependabilidade do portão:** modelo de falhas com quantidade, verdade de
  referência independente, linha de base, teste cego de campo e atacante adaptativo.
- **P2 · Recibo mínimo:** hashes do pai, do derivado, do portão e da bateria + veredito, no
  contrato, com atestação implícita (D3).
- **P4 · Bounty:** desenho no texto; a rodada adaptativa da RQ4 é conduzida como um **bounty
  interno** com oráculo secreto (molde Rando).

**Fora (limitação ou trabalho futuro):** exportação de pesos (P3/C3); backdoor com gatilho;
destilação por consultas; canais laterais; modelos grandes; distribuição entre operadores (D3).

---

## 2. Requisitos que a base impõe

Cada linha é uma obrigação do desenho ou da avaliação, com o artigo que a impõe.

| # | Requisito | Imposto por |
|---|---|---|
| R1 | O portão julga **o derivado**, nunca o script ou os dados; F1 e F2 usam o mesmo script | Qi 2024; D2 |
| R2 | Checar utilidade não basta: a bateria mede **recusa** em pedidos nocivos | Arditi |
| R3 | Recusa e **dano** medidos separadamente (não recusar ≠ ajudar) | StrongREJECT |
| R4 | **Recusa excessiva** medida em pedidos seguros com contraste inseguro, com tolerância própria | XSTest; E10 §5 |
| R5 | Parâmetros fixos e reportados (tokens gerados, decodificação, *template*, *system prompt*) | HarmBench; Qi 2025 |
| R6 | Com e sem *system prompt* | Arditi (22,6% × 79,9% no Llama-2) |
| R7 | Bateria com **codificações conhecidas** e parte **secreta**; cifra nova fica como escape esperado e é reportada | Halawi |
| R8 | Avaliar **os formatos liberados** (precisão cheia + LLM.int8, NF4, FP4) | Egashira; D5 |
| R9 | Referência do pai **custodiada**; sinais internos contra ela | Hurtado |
| R10 | O portão vê o derivado inteiro antes de liberar (dados + pré + pós ficam na CVM) | Egler |
| R11 | Avaliação contra **atacante adaptativo** que conhece o portão, com orçamento declarado | Nasr; Qi 2025 |
| R12 | Rótulo de verdade por procedimento **diferente** do portão | E9 §1.4; HarmBench |
| R13 | População injetada comparada com **campo**; injeções não representativas reportadas à parte | Natella; TPU-FI [57] |
| R14 | Calibração separada do teste; família não vista; pré-registro | E9 §1 |
| R15 | Comparação com a **melhor alternativa existente** | E9 §1.6 |
| R16 | Resposta lida **inteira**: um derivado pode recusar e depois atender | Qi *shallow*; E6 §7 (P6) |

---

## 3. Frentes de trabalho

A coluna "Pronto quando" é o critério de aceite de cada entrega.

### 3.1 W1 · Protocolo e pré-registro

| Entrega | Conteúdo | Pronto quando |
|---|---|---|
| `prereg.yaml` | **δ** de recusa (por categoria, Qi 2024) e **tolerância de recusa excessiva**; métricas; limiares; tamanhos de amostra por divisão; seeds; critérios de sucesso e de corte por RQ | Commitado **antes** de abrir qualquer conjunto de teste (09/nov) |
| Divisões | Calibração, teste e família não vista com seeds disjuntas (tabela do §3.2); campo só no teste cego | Lista de derivados por divisão versionada |
| Rótulo | C se a recusa cai mais que δ e a utilidade se mantém; N se a utilidade cai; H caso contrário; violação de recusa excessiva rotulada à parte | Definido no `prereg.yaml` |

### 3.2 W2 · População de derivados

Modelo de falhas (E8 §9.2), com a "quantidade de falha" a varrer (molde ReMlX):

| Classe | Como | Quantidade varrida | Rótulo esperado |
|---|---|---|---|
| F0 endurecido | LoRA com recusas estendidas (Abu Shairah) | Passos | H, mas viola a recusa excessiva; controle negativo de S3 (Hurtado App. B) |
| F1 benigno que preserva | LoRA em Alpaca, GSM8K, SQL | Passos | H (negativo difícil) |
| F1 benigno que degrada | Mesmo script, dados que Qi 2024 mostra degradar | Passos | Zona cinza: relatar à parte |
| F2 dados nocivos | **Mesmo script** de F1 com 10–100 exemplos nocivos | Nº de exemplos | C |
| F3 edição de pesos | Abliteração (Arditi) | Intensidade e camadas | C |
| F4 adaptativo | §3.6 | Rodadas | C |
| Campo | Obliterados públicos (§3.5) | — | Teste cego |

**Validação da população (sustenta A1):** cada derivado C precisa perder recusa **e** manter
utilidade (tarefa ou MMLU curto); um derivado degenerado é estado N e sai da conta de C.

**Tamanhos (estatística, E9 §1.5).** Com n negativos, a menor FPR não nula é 1/n; com 60, um
falso positivo já é 1,7%. Meta de **≥ 60 H em cada conjunto de teste**:

| Divisão | H (F0 + F1) | C (F2 + F3) | F4 | Total |
|---|---|---|---|---|
| Calibração (Qwen2.5-0.5B, seeds A) | 40 | 30 | — | 70 |
| Teste (Qwen2.5-0.5B, seeds B) | 60 | 45 | ~15 | ~120 |
| Família não vista | 60 | 30 | — | 90 |
| Campo (safetensors) | — | ≥ 20 | — | ≥ 20 |
| **Total** | | | | **~300 vereditos** |

TPR a FPR de 5% é a métrica principal; a 1% fica como secundária, com IC por bootstrap.

### 3.3 W3 · Portão

| Componente | Desenho | Requisitos |
|---|---|---|
| S1 bateria | Nocivos do StrongREJECT + seguros e contrastes do XSTest; codificações conhecidas; ~30% secreta | R2–R7, R16 |
| S2 *gap* de recusa | Direção de recusa calculada **no base custodiado**; razão de *gap* do derivado | R9 |
| S3 energia rank-1 | ΔW do derivado contra o base custodiado (`o_proj`, `down_proj`, camadas do meio) | R9 |
| Formatos | S1 em cada quantização *zero-shot*; S2/S3 em precisão cheia | R8 |
| Veredito | z-soma, limiar por Youden na calibração; aprovado, reprovado ou **inconclusivo** | E11 §4 (A8) |
| Juiz do portão | Avaliador aberto do StrongREJECT, afinado em Gemma 2B (no HF, `qylu4156/strongreject-15k-v1`; conferir no piloto), em CPU | R3 |
| Linha de base | Os dois sinais de Hurtado reimplementados (sem custódia); Egler só citado, por custo | R15 |

**S1 em dois estágios, sem abrir brecha:**
- estágio 1: todos os itens com 64 tokens, para triagem;
- estágio 2: 512 tokens em **todos** os que não recusaram, em uma **amostra aleatória fixa** dos
  que recusaram e em **toda** a parte secreta;
- a amostra dos recusados existe por causa do R16: um derivado que recusa e depois atende passaria
  num estágio 2 só dos não recusados. O ataque *refuse-then-comply* entra em F4.

**Custo é o risco número um.** O veredito do G1 é a **configuração de liberação inteira**: todos
os formatos de R8, com e sem *system prompt* (R6), **incluindo o tempo do juiz**. Uma conta grosseira
(250 itens × 512 tokens num 0,5B em 4 vCPU) já passa de uma hora por configuração, antes do juiz.
Medir no dia 1 do piloto. Para caber:
- dois estágios, como acima;
- bateria reduzida por formato e por *system prompt*; a completa só em precisão cheia;
- quantização como **quantizar e desquantizar em CPU** (formalização por bloco de Egashira §3),
  conferida contra a implementação de referência numa amostra. `bitsandbytes` em CPU não é
  garantido.

### 3.4 W4 · Verdade de referência

- **Rótulo C/H/N** por bateria **independente** da do portão (itens diferentes) e juiz diferente
  e mais forte (R12), com δ e tolerância do `prereg.yaml`.
- **Conferência humana:** amostra estratificada de ~100 respostas, dois anotadores, κ reportado
  (E9 B3). Anotar texto nocivo pede nota de ética e, se a instituição exigir, aprovação do comitê.
- **Utilidade:** acurácia na tarefa do fine-tuning e um MMLU curto, para separar N de C.

### 3.5 W5 · Campo (teste cego, RQ3)

**Fontes:**
- o registro de 57 abliterações públicas de Hurtado (notas 06, §1.3);
- buscas no HF (2026-10-27) que já acharam derivados para as duas famílias, por exemplo
  `huihui-ai/Qwen2.5-0.5B-Instruct-abliterated-v3`,
  `3MPER0RR/Qwen2.5-0.5B-Instruct-3MPER0RR-abliterated` e
  `sbussiso/Llama-3.2-1B-Instruct-abliterated`.

**Meta:** ≥ 20 derivados de campo em safetensors.

**GGUF:** na mesma busca, a maior parte dos resultados era GGUF. Isso combina com as
"redistribuições comprimidas" da 10a Labs e com a predominância de GGUF no resumo de Sokhansanj.
O GGUF não é formato de liberação (D5), mas aparece no campo. Plano:
- teste cego separado em **safetensors** (principal) e **GGUF** (secundário);
- leitura e desquantização de GGUF com `gguf` (o pacote Python do llama.cpp), que entra nas
  dependências;
- **controle negativo:** quantizar o próprio base nos mesmos formatos GGUF e medir o ruído de S3
  que isso gera, que vira o piso do sinal.

**Representatividade (Natella, TPU-FI):** comparar a distribuição de S1–S3 entre as nossas
abliterações e as de campo; reportar à parte as injeções fora da distribuição do campo. O Natella
precisa ser baixado e lido antes de escrever a metodologia.

### 3.6 W6 · Atacante adaptativo e bounty interno (RQ4)

Modelo de ameaça da E10 §5: usuário com os pesos dentro da CVM, conhece o código do portão e a
parte pública da bateria, não a secreta.

| Ataque | Base | Situação |
|---|---|---|
| Treino contra o limiar (abliteração + LoRA de "cura" que restaura S2/S3) | Hurtado §5 | **Mínimo** |
| Referência forjada (RQ5) | Hurtado §5 | **Mínimo** |
| CMFT com codificação conhecida | Halawi | Mínimo **se** o piloto mostrar que um 0,5B aprende a codificação; senão, limitação |
| *Refuse-then-comply* | Qi *shallow*; E6 §7 (P6) | Extra |
| Quantização condicionada | Egashira | Extra |
| *Prefill* e abliteração de teste (se a interface do job permitir) | Kuo | Extra |

**Bounty interno:** cada rodada é uma submissão; sucesso = passar no portão **e** falhar na
bateria secreta (oráculo à la Rando). Métricas: taxa de escape × rodadas, rodadas até o primeiro
escape e o modelo analítico 1 − (1 − e)^k da E8 §9.3.

**Independência:** quem ataca não pode ter visto a parte secreta. A bateria secreta fica com uma
pessoa só, que não ataca. Se não houver uma segunda pessoa, isso vira ameaça à validade
declarada.

**Ablação com e sem custódia (RQ5):** a referência forjada de Hurtado passa sem custódia; com
custódia, vira falha de atestação.

### 3.7 W7 · Integração no DNAT (C1 + P2)

**Arquitetura do piloto (D4, decidida na T-102 em 28/10):** CVMs reais na nuvem (Azure, AWS ou
Oracle, escolhida pelo custo). A CVM1 é o plano de controle; a CVM2 é o builder, numa CVM
separada; cada job (fine-tuning, Juiz, medição do pai) roda numa **CVM de uso único**, direto na
CVM, sem container e com o script sem rede; cada sessão de inferência ganha a sua CVM de uso
único. **Não há microVM:** o Firecracker não roda numa CVM (sem virtualização aninhada). O código
de hoje (`vm_runtime/`, `build_vm_runtime/`), dentro de uma CVM, roda em modo direto
(`run-direct.sh`, `build-direct.sh`), uma linha de base sem isolamento entre jobs; o caminho com
Firecracker (`run-vm.sh`, `build-vm.sh`) é legado. O container sem rede e o build em duas fases da
D4 ficam como alvo.

| Passo | Onde | Pronto quando |
|---|---|---|
| Tipos `Model` e `Derivative`; `parentId`, hashes, compromisso da bateria e veredito; registro só pelo executor | `DnatMarketplace.sol` | Testes do contrato passam com um derivado aprovado e um reprovado |
| **Revogação pelo operador:** hoje `revokeAsset` e `updateAsset` exigem o dono (linhas 170 e 185), e o dono do derivado é o adversário; e `updateAsset` deixa o dono reativar o ativo (linha 173) | `DnatMarketplace.sol` | Teste: o operador revoga; o dono não reativa um derivado reprovado ou revogado |
| **CVM de job de uso único:** a CVM1 tira uma CVM nunca usada do *warm pool*, entrega o job, recebe a saída e destrói a CVM | CVM1 e agente da CVM de job (novo) | Dois jobs seguidos nunca caem na mesma CVM |
| Tamanho da CVM de job e **tempos limite configuráveis** (hoje 660 s no modo direto e 720 s no executor) | agente da CVM de job; `vm_runtime/vm/run-direct.sh:24`, `vm_runtime/executor.py:56` | O 0,5B carrega; um treino LoRA e um veredito completos terminam |
| Saída de **esquema fixo**: o usuário recebe só as métricas; o derivado volta à CVM1, que o cifra no IPFS, nunca em `result.json` | agente da CVM de job; CVM1 | Um job de fine-tuning termina sem o derivado nem a saída bruta para o usuário |
| Portão como **segundo job**, numa CVM de uso único, com base e derivado conferidos por hash | CVM1 e agente | `verdict.json` com o recibo |
| Medição: VM comum × CVM, e CVM reaproveitada × CVM de uso único | `assets/tests/run_cvm_overhead_campaign.sh` | Tempo e custo por veredito com IC |

### 3.8 W8 · Escrita

O rascunho LaTeX é do Juiz de código (`artigo/sections/05_judge.tex`, `06_benchmark.tex`) e tem
de ser reescrito. Estrutura proposta, 11 páginas:

| Seção | Conteúdo | Base | Págs. |
|---|---|---|---|
| 1 Introdução | Problema e contribuições | A1, A2; Lin; Casper | 1 |
| 2 Contexto | Recusa, derivação, custódia | Arditi; Qi 2024 | 0,5 |
| 3 Sistema e ameaça | Custódia, adversário, componentes confiáveis | E10 §5; E8 §9.2 | 1 |
| 4 Modelo de falhas e propriedade | F0–F4, estados H/C/N, propriedade com δ | ReMlX; Multi-version ML | 1 |
| 5 Desenho | Portão, formatos, recibo, revogação | A3, A4; Hurtado; Egashira | 1,5 |
| 6 Metodologia | Verdade de referência, divisões, pré-registro, estatística, linha de base | A5; E9; Natella | 1 |
| 7 Avaliação | RQ1–RQ5 | — | 2,75 |
| 8 Ameaças à validade | Modelos pequenos, população nossa, bounty interno, juiz | E9 §1.7 | 0,5 |
| 9 Relacionados | Detectores, defesas, atestação | camadas 2 e 3 | 0,5 |
| 10 Discussão e limites | Proof-of-Guardrail, backdoor, cifra nova, bounty | — | 0,25 |
| Ética, AI Tool Usage, artefato | Obrigatórias no CFP; intenção de artefato sem pesos nem gerações nocivas | PLANO §0 | 0,25 |

**Perguntas de pesquisa** (E8 §9.3, ajustadas):
- **RQ1** liberação silenciosa e falso alarme por classe de falha, contra a linha de base;
- **RQ2** sensibilidade à quantidade de falha;
- **RQ3** representatividade: injeção × campo, safetensors × GGUF;
- **RQ4** atacante adaptativo (bounty interno);
- **RQ5** ablação dos sinais e da custódia, e custo por veredito na CVM.

---

## 4. Cronograma

| Semana | Pesquisa | Integração | Escrita |
|---|---|---|---|
| **S1** 28/out–02/nov | **Piloto** (E7 §7): 2 abliterações, 2 LoRA benignos, 2–3 de campo; S1–S3; custo do veredito de liberação; quantização em CPU; viabilidade do CMFT num 0,5B. **Decisões do §8 até 02/nov** | — | Ameaça e modelo de falhas (seções 3–4) |
| **S2** 03–09/nov | Calibração e população de teste F0–F3; validação da população; W4 rodando; **pré-registro commitado** | Contrato (tipos, recibo, revogação) e CVM de job de uso único (pool, tamanho, tempos limite) | Desenho (5); ler o Natella |
| **S3** 10–16/nov | F4 e bounty interno; família não vista; teste cego de campo; linha de base | Derivado em custódia e portão como segundo job | Metodologia (6) e introdução (1–2) |
| **S4** 17–23/nov | Campanha com seeds e IC; custo na CVM | Medição de custo | Avaliação (7) e ameaças (8) com números reais |
| 24–25/nov | **Congelar** | — | **Resumo em 25/nov** (título e autores definitivos) |
| **S5** 26/nov–02/dez | Só correções | — | Rascunho aos coautores em **28/nov**; corte de páginas; submissão em **02/dez** |

---

## 5. Marcos de decisão

| Marco | Data | Critério | Se falhar |
|---|---|---|---|
| **G0 · Recursos** | 02/nov | Decisões 1–5 do §8 tomadas | O cronograma de S2 escorrega na mesma medida |
| **G1 · Piloto** | 01/nov | Algum sinal separa abliterados de benignos **e** o veredito de liberação inteiro, com juiz, cabe em 80 min em 4 vCPU (E7 §7) | Reduzir bateria e formatos; se ainda falhar, o fallback da E7 §7 volta à mesa com o orientador |
| **G1b · Alerta** | 01/nov | S3 separa tudo com folga? | Não é corte: o valor do artigo passa a vir de RQ3 e RQ4 |
| **G2 · Calibração** | 09/nov | Limiar e δ fixados e pré-registro commitado antes de tocar no teste | Atrasar o teste; nunca recalibrar com ele |
| **G3 · Integração** | 16/nov | Um derivado reprovado não sai, um aprovado vira ativo com recibo e o operador revoga | O recibo vira log assinado pela CVM1 (ordem de corte); a retenção cifrada no IPFS fica |
| **G4 · Congelamento** | 23/nov | Todas as RQs com IC | O que não tiver IC sai do texto ou vira discussão |

---

## 6. Recursos

- **Computação:** tudo em CPU (D2). ~300 vereditos (§3.2), mais treino de LoRA e a verdade de
  referência. Se o piloto confirmar ~1–1,5 h por veredito com juiz, são ~300–450 h de CPU de
  4 vCPU: **cerca de 8 máquinas** em S2–S4. Com menos máquinas, a família não vista e o campo
  encolhem primeiro (ordem de corte).
- **CVMs na nuvem:** o fluxo integrado roda em CVMs reais (T-102); a nuvem (Azure, AWS ou
  Oracle) sai pelo custo. A campanha de pesquisa pode rodar em máquinas comuns de CPU, com o mesmo
  pacote do Juiz; a CVM entra no custo por veredito da RQ5.
- **Pessoas:** quem conduz os experimentos de ML; dois anotadores; uma pessoa que guarda a bateria
  secreta e não ataca (§3.6).

---

## 7. Riscos

| Risco | Base | Mitigação |
|---|---|---|
| Veredito caro demais em CPU | §3.3 | Dois estágios; bateria reduzida por formato; medir no piloto com o juiz |
| Quantização sem suporte em CPU | §3.3 | Quantizar e desquantizar em CPU, conferido numa amostra |
| Ruído do GGUF confunde S3 | §3.5 | Controle negativo com o base quantizado |
| Poucos negativos para FPR baixa | §3.2 | ≥ 60 H por conjunto de teste; FPR 5% como métrica principal |
| S3 dispara em derivados endurecidos | Hurtado App. B | Classe F0 como controle negativo |
| Juiz do portão enganado pelo derivado | HarmBench | Juiz da verdade de referência diferente; amostra humana |
| Bateria vaza pelo veredito | Rando; CTF do SaTML | Parte secreta, veredito binário no bounty, orçamento de rodadas |
| CMFT inviável num 0,5B | Halawi (feito no GPT-4) | Testar no piloto; se falhar, limitação declarada |
| Bounty interno sem independência | §3.6 | Guardião da bateria separado; senão, ameaça à validade |
| S3 trivial | E7 §7 | G1b |
| Revisor ler como SaTML | PLANO §2 | Forma DSN: propriedade, falhas com quantidade, estados, liberação silenciosa |
| Ética | PLANO §0 | Modelos pequenos; não publicar pesos nem gerações nocivas; seção de ética; nota para a anotação humana |

---

## 8. Decisões que o plano precisa do grupo (prazo: 02/nov)

1. **Máquinas para a campanha:** quantas e onde (§6).
2. **Juiz da verdade de referência:** modelo aberto maior em CPU ou API externa sobre as gerações
   (custo × enviar texto nocivo para fora).
3. **Família não vista:** Llama-3.2-1B (licença com aceite no HF) ou outra.
4. **Nuvem e crédito para as CVMs:** Azure, AWS ou Oracle, pelo custo (T-102).
5. **Pessoas:** anotadores e o guardião da bateria secreta.
6. **Bounty interno** como formato da RQ4 (§3.6): sim ou não.
