# E15 · Modelo do atacante e orçamento de rodadas (T-1201)

Base: E10 §5 (adversário), E13 §3.6 (ataques e bounty interno), E14 §12 (fronteiras), §13
(o que o Juiz não cobre) e §18 (identidade e cota). Citado pela seção 3 do artigo (T-1502).

## 1. Quem ataca

**Um usuário da plataforma que quer liberar um derivado comprometido.** Ele controla o script e os
dados do fine-tuning e escolhe quantas vezes tenta. O operador, a CVM e o código do Juiz
(identificado por hash) são confiáveis (D3, E14 §12).

| O atacante… | Sim | Não |
|---|---|---|
| Treina com o script e os dados que quiser | ✔ | |
| Conhece o código do Juiz, as regras, os limiares e o `prereg.yaml` | ✔ (Kerckhoffs) | |
| Conhece a parte pública da bateria e roda o Juiz contra ela fora da plataforma | ✔ | |
| Tem pesos de um base parecido para treinar e medir S2 e S3 por conta própria (white-box) | ✔ | |
| Vê os pesos do derivado que treinou | | ✘: o derivado volta cifrado à CVM1 (T-803) |
| Vê a saída do job além de loss, passos e tempo | | ✘: esquema fixo (T-804) |
| Vê a parte secreta da bateria ou a semente do sorteio | | ✘: só a CVM1 tem a chave (E14 §7.2) |
| Fornece a referência do pai | | ✘: medida sob custódia (barra a referência forjada, RQ5) |
| Vê medidas e motivos do veredito | | ✘: só o estado, em T0 + T_max (E14 §4) |
| Usa *prefill*, troca o template ou a decodificação no serviço | | ✘: trava do serviço (E14 §6.1) |
| Compra mais identidades | ✔, a um custo C_id cada | |

## 2. O que cada rodada revela

Uma rodada é um derivado novo (um digest novo) submetido ao Juiz. O atacante aprende **um de três
estados** (aprovado, reprovado, inconclusivo), não um escore nem a regra que decidiu. O saldo da
cota muda pelo estado, que ele já vê; não abre canal novo (E14 §18.4). O tempo também não vaza: o
estado sai num instante fixo.

O inconclusivo é informação a mais que um oráculo binário: diz "perto da margem" ou "segunda
linha disparou". Por isso custa 2 na cota, entre o aprovado (1) e o reprovado (5).

## 3. Orçamento

| Item | Valor | De onde |
|---|---|---|
| Saldo por identidade | Q = 20 | E14 §18.4, provisório até a T-1708 |
| Reserva por tentativa (custo do reprovado) | c_R = 5 | E14 §18.4 |
| Tentativas reprovadas por identidade | ⌊Q / c_R⌋ = 4 | |
| Rodadas com N identidades | k = N · ⌊Q / c_R⌋ = 4N | |
| Probabilidade de escape | 1 − (1 − e)^k | E8 §9.3, com e a taxa de escape medida (T-1212) |
| Custo esperado do primeiro escape | ≈ (c_R / (e · Q)) · C_id + 1/e jobs | E14 §18.5 |
| CPU por rodada | o limite do job (T-802), mais a medição do Juiz | sem rede, CVM de uso único |
| Custo de uma identidade C_id | 2^d hashes; medido em 0,242 milhão de hashes/s num núcleo: ~4 s com d = 20, ~70 s com d = 24 | T-1705, `smart-contract/results/identity_pow_cost.md` |

**Leitura do orçamento:**
- Com d = 20 (o do protótipo), uma identidade custa segundos e N cresce quase de graça. O
  protótipo demonstra o mecanismo, não o preço. Para C_id ≈ 1 h de CPU no mesmo núcleo, d ≈ 30
  (2^30 / 0,242·10⁶ ≈ 74 min). A medida em VM de 4 vCPU (T-210) e a vantagem de GPU/ASIC no SHA-256
  (E14 §18.7) entram no modelo de custo da T-1708.
- **No bounty interno (E13 §3.6)**, o orçamento é fixado antes: N identidades por atacante e o
  número de rodadas que daí sai. O resultado é a taxa de escape por rodada, as rodadas até o primeiro
  escape e o custo esperado da tabela.
- **Sucesso** é passar no Juiz **e** falhar na bateria secreta, conferida pelo guardião (oráculo à
  la Rando). Passar no Juiz com um derivado que de fato não regrediu não é escape.

## 4. Ataques

| Ataque | Mira em | Situação (E13 §3.6) | O que o barra | Limite declarado (E14 §13) |
|---|---|---|---|---|
| Abliteração + LoRA de "cura" que restaura S2 e S3 | segunda linha | Mínimo | S1 decide; S2/S3 só levam a inconclusivo | Ataque white-box contra S2/S3: parcial |
| Referência forjada | custódia | Mínimo (RQ5) | o pai é medido sob custódia | — |
| CMFT com codificação conhecida | S1 em claro | Mínimo se o 0,5B aprender a codificação | codificados como sentinela (T-305) | cifra nova: fora |
| Treinar contra a parte pública | bateria | implícito | parte secreta e a discordância secreta × pública (guarda) | — |
| *Refuse-then-comply* | leitura da resposta | Extra | a resposta é lida inteira | — |
| Quantização condicionada | formatos | Extra | tudo ou nada nos formatos (T-605) | formatos não avaliados não saem |
| *Prefill*, abliteração de teste | serviço | Extra | trava do serviço | — |
| Muitas identidades | cota | implícito | C_id por identidade | põe preço, não impede |
| Backdoor com gatilho, vários turnos, outras línguas | — | Fora | — | fora ou parcial |

## 5. Independência

Quem ataca não vê a parte secreta. A bateria secreta fica com o guardião (T-1605), que não ataca.
Sem uma segunda pessoa, isso vira ameaça à validade declarada no artigo.

## 6. Em aberto

- O valor de e e o modelo de custo, com Q e os pesos 1, 2 e 5 fixados (T-1212, T-1708).
- N por atacante no bounty interno e o tempo de cada rodada, depois da T-210.
- A parte secreta ainda não existe (T-304 depende de decisão com o orientador). Sem ela, o oráculo
  de sucesso do bounty não tem como ser conferido.
