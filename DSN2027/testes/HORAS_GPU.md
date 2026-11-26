# Horas de GPU confidencial por teste: três perfis

Estimativa de 26/11/2026 para a VM `a3-highgpu-1g` (H100 com TDX, Spot). As horas contam o tempo em que a
VM fica ligada, porque a GPU é cobrada mesmo parada. Para ter o custo, multiplique pelo preço por hora que o
console mostra para a zona. **Antes da campanha, o ensaio (§6) troca as suposições por medidas.**

## 0. Primeiro: o piloto (decidido em 26/11)

A primeira rodada na VM com GPU é o **piloto**, uma versão bem reduzida do perfil simples. Ela serve
para ter resultados para mostrar, conferir a metodologia de ponta a ponta e ter números de comparação.
Depois do piloto, o tamanho da campanha (os três perfis abaixo) se decide com o orientador.

```bash
tools/cloud/campanha_gpu.sh iniciar piloto    # na VM, depois do preparar_testes.sh
```

O que muda em relação à campanha:

- **Prereg** (`prereg_piloto.yaml`): só fp e só a condição padrão, 24 âncoras e 8 seguros. São ~32
  gerações por veredito, contra ~228 na campanha, e a resposta continua lida até 512 tokens.
- **Bateria**: 96 nocivos (16 por categoria), contra 313. A referência do pai cai de ~2,5 h para ~15 min.
- **Tamanho de cada teste**:
  - T1: base 2× e huihui.
  - T2: 4 derivados (2 H, 2 C).
  - T3: 4 derivados (2 H, 2 C).
  - T5: 3 do campo.
  - T6: 2 rodadas.
  - T7: os casos A, B e C e a ablação.
  - T8: ponta a ponta.
  - T9–T11: pequenos.
- **Calibração**: o T3 em diante usa direto a proposta do T2, sem pausa para revisão humana.
- **Fora do piloto**:
  - o cronômetro em 4 vCPU (§4);
  - a vazão e o avaliador na CPU;
  - o overhead VM × CVM;
  - o Llama.

| Parte | Horas (estimativa) |
|---|---|
| T1 (ficha, determinismo, bateria, pai, 3 vereditos) | 0,5 |
| T2 (4 derivados, rótulo de 5 modelos, calibração) | 0,6 |
| T3 (4 derivados, rótulo, análise com Hurtado) | 0,5 |
| T5 (3 do campo) e T4 (comparação) | 0,35 |
| T6 (2 rodadas) | 0,3 |
| T7 (pai forjado e casos A, B e C) | 0,4 |
| T8 (ponta a ponta) | 0,25 |
| T9–T11 e hashcat | 0,15 |
| **Piloto** | **~3 h (2–5)** |
| Preparo da VM (pacotes e ~80 GB de modelos) | ~1 h; **5–15 min com disco pronto** (imagem de uma VM barata: `preparar_testes.sh --disco` e `--so-gpu`, `tools/cloud/README.md`) |
| **VM ligada, do zero ao pacote** | **~4–4,5 h** |

- **O ensaio vira opcional.** O piloto mostra um problema de GPU nos primeiros 20 min (determinismo e pai do
  T1). Uma falha no meio também não joga nada fora: os passos que terminaram ficam, o código se corrige e o
  piloto retoma, porque a pasta tem nome fixo (`testes/piloto/piloto/`).
- **O que o piloto permite mostrar:**
  - o base aprovado contra ele mesmo;
  - o abliterado público reprovado;
  - o determinismo na GPU;
  - limiares propostos a partir de medidas reais;
  - a tabela veredito × rótulo do gpt-oss nos derivados novos e no campo, com a linha de base de Hurtado
    nas mesmas linhas;
  - o atacante, os casos da custódia e o fluxo completo com recibo.
- **O que ele não permite mostrar:** taxas com força estatística. Com 2 C, o IC 95% de zero escapes vai
  até 84%. Esse é o ponto da conversa com o orientador.

## 1. Resumo (a campanha, depois do piloto)

| Plano | Horas de VM com GPU (central e faixa) | Com lote 8 e 3 processos (§5) |
|---|---|---|
| **Como está nos roteiros hoje** | **~72 h** (≈ 35 h delas com a GPU parada, só a CPU trabalhando) | — |
| **Robusto** | **69 h** (46–103) | **35 h** (25–53) |
| **Mediano** (recomendado) | **30 h** (20–44) | **16 h** (12–23) |
| **Simples** | **20 h** (14–30) | **11 h** (8–16) |

O que mais pesa:

1. **O passo `cpu-x-gpu` do T1 deixa a GPU parada por ~35 h.** Ele mede o pai inteiro na CPU de 4 vCPU, com
   ~1.650 gerações e ~1.650 notas do Qwen3Guard a 50 s cada (T-309). Isso dá ~29 h. Depois julga o huihui na
   CPU, mais ~5,5 h. O comentário do roteiro fala em "~1 h", mas essa conta valia para a bateria do mini (24
   nocivos), não para a da campanha (313). Além disso, a meta G1 já se sabe perdida com o Qwen3Guard em CPU: a
   T-309 deu 264 min só de avaliador por veredito.
2. **A quantidade de derivados é o que define a conta.** Cada veredito custa ~14 min com 2 processos. A
   referência do pai custa ~2,5 h, uma vez só. Cada rótulo custa ~6 min por modelo.
3. **O lote 1 na geração deixa a H100 quase ociosa.** Um modelo de 0,5B com lote 1 fica preso ao lançamento
   de kernels, e não ao cálculo. Com lote 8, a conta cai quase à metade, mas isso é uma decisão de desenho
   (§5).

## 2. De onde vêm os números

**Medido (CPU, notebook):**
- O 0,5B gera ~20 tok/s com lote 1 em 4 vCPU (T-208).
- As respostas do base têm ~205–239 tokens nos nocivos e ~190 nos seguros (T-208).
- O Qwen3Guard leva 50 s por item em 4 vCPU, com ~659 tokens de entrada (T-309).

**Contado no código:**
- O veredito usa 2 formatos (fp, nf4) × 2 condições = 4 configurações. Em cada uma entram 32 âncoras e 25
  seguros, ou seja, ~228 gerações por derivado, até 512 tokens cada, e ~300 notas do avaliador.
- A referência do pai (`reference.measure_parent`) gera e avalia o **acervo inteiro** em cada formato e
  condição: 4 × (313 nocivos + os seguros) ≈ 1.650 gerações. Ela é medida uma vez e fica em cache enquanto
  não mudarem a bateria, o desenho do S1 e o dispositivo.
- O rótulo usa 8 nocivos por categoria, 12 seguros e 32 de utilidade, com lote 16 e o gpt-oss-20b. O pai é
  rotulado uma vez.
- O T6 roda as rodadas uma depois da outra, porque cada α depende da anterior. Por isso o paralelo não ajuda
  nesse teste.

**Suposto para a GPU (a confirmar no ensaio):**

| Unidade | Central | Faixa | Por quê |
|---|---|---|---|
| Veredito de 1 derivado, lote 1, 1 processo | 25 min | 15–40 | ~228 gerações a ~40 tok/s, mais ~300 notas do Qwen3Guard a ~0,5 s, mais carga, formatos e S2/S3 |
| Ganho de `MG_PARALELO=2` | 1,8× | — | os dois processos dividem a GPU, que está quase ociosa com lote 1 |
| Referência do pai (acervo de 313) | 2,5 h | 1,7–3,3 | ~1.650 gerações, com o mesmo custo por geração do veredito |
| Rótulo de 1 modelo (gpt-oss-20b, lote 16) | 6 min | 4–10 | mais ~3 min de carga do juiz por passo |
| LoRA de 200 passos / abliteração | 2,5 / 1 min | — | 0,5B na H100 |
| Preparo da VM (pacotes, ~80 GB de modelos) | 1 h | — | 15 min se o disco já vier pronto (§4) |
| Preempção e reinícios (Spot) | × 1,15 | 1,1–1,3 | a retomada perde no máximo o derivado em curso |

O que mais pode mexer na conta é a vazão da H100 com lote 1 em modo confidencial. No modo CC, a CPU e a GPU
conversam por canais cifrados, e isso pesa justamente em muitos kernels pequenos. A faixa de cada perfil
vem dessa incerteza.

## 3. O padrão de consideração

Avaliei cada perfil por quatro critérios, nesta ordem:

1. **O que a amostra permite afirmar.** O número de derivados decide qual frase cabe no artigo. Com zero
   escapes em n comprometidos, o limite superior do IC 95% (Clopper–Pearson) é:

   | n de C | 6 | 8 | 10 | 13 | 18 | 20 | 30 | **36** |
   |---|---|---|---|---|---|---|---|---|
   | liberação silenciosa ≤ | 46% | 37% | 31% | 25% | 19% | 17% | 12% | **9,7%** |

   O gabarito do T3 ("≤ 10% com IC 95%") **só se confirma com ~36 C e nenhum escape**. Com os 10 C de hoje,
   o máximo que se pode escrever é "0/10, IC até 31%". Vale o mesmo para a calibração: o quantil de 5% dos H
   só é um quantil com ~20 H. Com 6 H, ele é o mínimo da amostra.
2. **Custo marginal.** O custo de cada perfil é uma soma de partes:
   - **fixo**: o preparo, o ensaio e uma referência do pai por bateria;
   - **por derivado**: ~14 min de veredito e ~6 min de rótulo;
   - **sequencial**: ~26 min por rodada do T6.
3. **Risco de retrabalho.** Algumas mudanças, feitas no meio, obrigam a medir o pai de novo (2,5 h) e a
   refazer todos os vereditos seguintes. São elas: mudar a bateria (T-304), o desenho do S1 no prereg, o lote
   ou o dispositivo. Por isso, nos três perfis, tudo isso se congela antes da fase 1.
4. **Cobertura das perguntas.**
   - T1, T2, T3, T5 e T8 sustentam as afirmações centrais (P1, P2, P4, P8).
   - T6 e T7 sustentam as de segurança (P5, P7).
   - T4 depende do Llama (T-212). Fica fora de todos os perfis, menos o robusto.

## 4. O que sai da VM com GPU em qualquer perfil

Nada disto usa a GPU. Rodar estes passos na a3 é pagar H100 para usar CPU.

| Passo | Hoje na a3 | Onde rodar | Economia |
|---|---|---|---|
| T1 `cpu-x-gpu` (pai e huihui em 4 vCPU) | ~35 h | numa VM de 4 vCPU à parte (de preferência c3 com TDX, que também é a máquina certa para o G1), em paralelo com a campanha; ou cortar para uma conferência CPU × GPU com bateria pequena | **~35 h** |
| T1 `vazao` e `avaliador` (CPU de propósito) | ~0,5 h | na mesma VM de 4 vCPU | 0,5 h |
| T9, T10 e T11 (Node, só CPU; o T10 com d até 27 e 3 repetições leva ~45 min num núcleo) | ~1 h | na VM de CPU ou no notebook; na a3 fica só o `hashcat -b -m 1400` (~5 min) para a taxa da GPU | ~1 h |
| T7 `overhead` (sonda de CPU no Docker, CVM × VM) | ~0,5 h + uma **segunda a3** | c3 com TDX × c3 comum, do mesmo tamanho; a sonda mede a CPU, não a GPU | 0,5 h + a segunda a3 |
| Pausa entre as fases (revisão humana do T2) | relógio correndo | **parar a VM** (o disco fica e o serviço retoma) | todas as horas da pausa |
| Preparo (download de gpt-oss, Qwen3Guard, campo) | ~1 h por VM criada | preparar um disco de dados numa VM barata e anexá-lo à a3 | ~45 min por recriação |

**Cuidado:** a chave do cache da referência do pai guarda só `cuda`, e não o modelo da placa
(`veredito.parent_reference`). Uma referência medida noutra GPU seria aceita sem aviso. Nunca copie
`references/` entre máquinas.

## 5. Os três perfis, teste a teste

Horas de VM com GPU, já sem os passos do §4 (central e, entre parênteses, a faixa). Os totais incluem os
× 1,15 da preempção.

| Teste | Robusto | Mediano | Simples |
|---|---|---|---|
| Preparo + ensaio | 1,8 | 1,8 | 0,8 (disco pronto) |
| **T1** sanidade | 3,4 (2,2–4,6): pai inteiro, base 2×, huihui | 3,4 (2,2–4,6): igual | 2,1 (1,4–2,9): acervo do pai com ~150 nocivos |
| **T2** calibração | 7,6 (5,0–11,8): **20** derivados (10 H, 10 C) | 4,6 (3,1–7,2): **12** (6 H, 6 C), como hoje | 3,2 (2,1–4,9): **8** (4 H, 4 C) |
| **T3** detecção | 20,7 (13,7–32,3): **56** (20 H, 36 C), com F0 | 7,5 (4,9–11,7): **20** (10 H, 10 C), como hoje | 4,6 (3,0–7,1): **12** (6 H, 6 C) |
| **T4 + T5 Llama** | 11,5 (7,5–16,8): pai Llama e 13 do campo | — | — |
| **T5** campo Qwen | 2,9 (1,8–4,6): os 8 | 2,9: os 8 | 2,9: os 8 |
| **T6** atacante | 7,6 (4,9–11,7): 15 rodadas e LoRA de disfarce | 1,6 (1,0–2,4): 3 rodadas | 1,6: 3 rodadas |
| **T7** ablação | 3,3: forjada com o acervo inteiro | 3,3: igual | 1,5: forjada com bateria reduzida |
| **T8** ponta a ponta | 1,0 | 1,0 | 1,0 (pai do T3) |
| T9–T11 | 0,1 (hashcat) | 0,1 | 0,1 |
| **Total × 1,15** | **69 h (46–103)** | **30 h (20–44)** | **20 h (14–30)** |

**O que cada perfil permite escrever:**

- **Robusto.**
  - Liberação silenciosa ≤ 10% com IC 95% (36 C) e falso alarme com 20 H.
  - Limiares calibrados num quantil de fato.
  - Família não vista (T4) e atacante com o plano completo (T6).
  - É o que um revisor exigente pediria. Custa mais que o dobro do mediano, e o T4 ainda depende do Llama
    sob custódia.
- **Mediano.**
  - As taxas por família e por dose, com IC honesto (0/10 → até 31%).
  - A comparação com Hurtado nas mesmas linhas.
  - O campo real (T5) somado aos C do T3: 18 C, com IC até 19% se nenhum escapar.
  - Os casos A, B e C da custódia e o ponta a ponta.
  - A frase "≤ 10%" não cabe: o resultado vira estimativa com intervalo, e não confirmação da meta.
- **Simples.**
  - O mecanismo funciona e as taxas são compatíveis, mas sem força estatística: 6 C dão IC até 46%.
  - Com 4 H, os limiares saem do pior H, não de um quantil. É preciso declarar isso como limitação.
  - Serve como piloto ou como plano B, se a cota apertar.

**Alavancas que valem para os três (decisões suas):**

| Alavanca | Efeito | Condição |
|---|---|---|
| **Lote 8 na geração do veredito e do pai** | robusto 69 → 38 h, mediano 30 → 17 h, simples 20 → 12 h | o lote canônico hoje é 1 (T-205, `configs.yaml`). Passa a valer se o ensaio mostrar o mesmo texto com lote 1 e lote 8 na GPU, numa amostra maior que a de 10 itens da T-205. O lote entra no desenho: o pai e os derivados com o mesmo lote, e a decisão registrada em DECISOES (D2) **antes** da fase 1 |
| `MG_PARALELO=3` | −10% | o pico de memória que o ensaio registra (`gpu_mem_mb`) precisa deixar folga para 3 processos (~20 GB cada, com o Qwen3Guard em float32) |
| Acervo do pai de 313 → ~150 nocivos (25 por categoria) | −1,2 h por medida do pai (T1 e T7 B) | é parte da decisão da bateria (T-304). Com ~1/3 a 1/2 de rendimento de âncoras (T-208), ainda sobram 50–75 âncoras por condição para sortear 32 |
| Somar as amostras C do T3 e do T5 na liberação silenciosa | mais n sem mais horas | precisa estar no prereg antes do T3 (análise pré-registrada) |

## 6. Como trocar estas suposições por medidas

O ensaio (~45 min) é o passo mais barato e o que mais reduz a incerteza. Dele saem:

| Medida | Onde fica | Substitui |
|---|---|---|
| tok/s com lote 1 na GPU | T1 `determinismo.json` → `tok_s_lote1` | a vazão do veredito e do pai |
| texto igual com lote 4 | T1 `determinismo.json` → `batch4_identical` | a base para decidir o lote 8 |
| minutos por veredito (bateria do mini) | T1 `resumo.json` | escalar por gerações: mini ≈ 4 × (âncoras + seguros do mini) |
| pico de memória | sinal de vida (`gpu_mem_mb`) | quantos processos cabem |
| tempo do rótulo e do LoRA | `logs/` do T2 e do T3 | as linhas de rótulo e população |

A conta, para refazer com as medidas:

```
horas ≈ [preparo + ensaio + pai + Σ_testes ( N·v/P + (N+1)·r + população ) + T6·(v + 1 min)] × 1,15 / 60
```

- `v`: minutos por veredito;
- `P`: o ganho do paralelo;
- `r`: minutos por rótulo;
- `N`: derivados do teste.

O modelo está em `HORAS_GPU_modelo.py`, ao lado deste arquivo.

## 7. Recomendação

**Mediano, com os passos do §4 fora da a3 e as duas alavancas de vazão, se o ensaio as aprovar: ~16–27 h.**

A ordem:

1. Criar o disco de dados numa VM barata.
2. Rodar o ensaio na a3 (~45 min) e parar a VM.
3. Refazer a conta com as medidas e decidir o lote e o paralelo.
4. Congelar a bateria (T-304) e o desenho.
5. Rodar a fase 1 (~10 h) e parar a VM durante a revisão do T2.
6. Rodar a fase 2 (~15 h).

Em paralelo, numa c3 de 4 vCPU, rodar o `cpu-x-gpu`, a vazão, o avaliador, o T9–T11 e o overhead.

Se depois sobrar cota, o passo que mais rende por hora é **aumentar os C do T3**. De 10 para 36, são ~+8 h
no mediano (ou ~+4 h com lote 8). É isso que transforma "0/10, IC até 31%" em "≤ 10% confirmado". Vale mais
do que as rodadas extras do T6.
