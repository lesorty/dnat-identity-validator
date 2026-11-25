# Teste 11: o atacante com muitas identidades

Teste 11 (P6): o atacante com muitas identidades. Rotas reais de identidade e cota da CVM1 por HTTP; veredito SIMULADO no corpo do job. A taxa de escape e é uma faixa até o Teste 6 medir a do Juiz.

Cota: saldo inicial 20; todo job reserva 5; o veredito cobra 1 (aprovado), 2 (inconclusivo), 5 (reprovado) ou 0 (falha). Prova de trabalho com d = 16 neste roteiro.

## Tentativas por identidade, medidas pela API

| Quem | Desfecho de cada job | Jobs aceitos | Depois |
|---|---|---:|---:|
| atacante 1 (c02a51f5039c…) | reprovado | 4 | 402 |
| atacante 2 (fb742dc0bec2…) | reprovado | 4 | 402 |
| atacante 3 (f8bcca725a78…) | reprovado | 4 | 402 |
| atacante 4 (1702e9aee343…) | reprovado | 4 | 402 |
| atacante 5 (a28dc71c7a9c…) | reprovado | 4 | 402 |
| atacante 6 (38877ded35ed…) | reprovado | 4 | 402 |
| atacante 7 (439fc49e6e41…) | reprovado | 4 | 402 |
| atacante 8 (294e0cb74ec7…) | reprovado | 4 | 402 |
| atacante 9 (1b0c76882b5c…) | reprovado | 4 | 402 |
| atacante 10 (0ae485145c98…) | reprovado | 4 | 402 |
| atacante só com inconclusivos | inconclusivo | 8 | 402 |
| honesto 1 (d27db3497df1…) | aprovado | 16 | 402 |
| honesto 2 (dba9c82f3398…) | aprovado | 16 | 402 |

Como todo job reserva 5, a identidade para quando o saldo fica abaixo disso: o honesto faz **16** aprovações (não 20) e o atacante tem **4** tentativas reprovadas, ou até **8** se todas caírem em inconclusivo.

## Truques do atacante

| Tentativa | HTTP | Esperado |
|---|---:|---:|
| a prova da chave A registra A | 201 | 201 |
| a prova de A não registra a chave B | 400 | 400 |
| a chave A não registra de novo | 409 | 409 |
| job sem assinatura | 401 | 401 |
| o pedido assinado, primeira vez | 200 | 200 |
| o mesmo pedido assinado, repetido | 401 | 401 |
| 3 jobs que falham (saldo depois de cada um) | 15, 15, 15 | sem gasto |

Um job que falha devolve a reserva e não dá veredito ao atacante: não ensina nada, mas gasta CVM da plataforma (limite a tratar à parte, fora da cota).

## Economia do ataque

Taxas de hash (results/T10_preco_identidade.json): 252.053 por segundo num núcleo; 1.072.429 com 12 núcleos.

Custo em CPU de um núcleo. Escape: tentativas reprovadas (4 por identidade); entre parênteses, o caso em que todas caem em inconclusivo (8).

| d | uma identidade | honesto, por aprovação | atacante por escape, e = 0.50% | atacante por escape, e = 1.0% | atacante por escape, e = 2.0% | atacante por escape, e = 5.0% |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 4.2 s | 260 ms | 3.5 min (104.0 s) | 104.0 s (52.0 s) | 52.0 s (26.0 s) | 20.8 s (10.4 s) |
| 24 | 66.6 s | 4.2 s | 55.5 min (27.7 min) | 27.7 min (13.9 min) | 13.9 min (6.9 min) | 5.5 min (2.8 min) |
| 28 | 17.7 min | 66.6 s | 14.8 h (7.4 h) | 7.4 h (3.7 h) | 3.7 h (110.9 min) | 88.7 min (44.4 min) |
| 30 | 71.0 min | 4.4 min | 2.5 dias (29.6 h) | 29.6 h (14.8 h) | 14.8 h (7.4 h) | 5.9 h (3.0 h) |
| 32 | 4.7 h | 17.7 min | 9.9 dias (4.9 dias) | 4.9 dias (2.5 dias) | 2.5 dias (29.6 h) | 23.7 h (11.8 h) |
| 34 | 18.9 h | 71.0 min | 39.4 dias (19.7 dias) | 19.7 dias (9.9 dias) | 9.9 dias (4.9 dias) | 3.9 dias (47.3 h) |
| 36 | 3.2 dias | 4.7 h | 157.8 dias (78.9 dias) | 78.9 dias (39.4 dias) | 39.4 dias (19.7 dias) | 15.8 dias (7.9 dias) |

Razão entre o custo de um escape e o de uma aprovação honesta: 800× com e = 0.50%; 400× com e = 1.0%; 200× com e = 2.0%; 80× com e = 5.0%. Não depende de d: o d escolhe o preço absoluto, a cota escolhe a razão.

Chance de escape com um orçamento de CPU (todos os 12 núcleos):

| d | orçamento | identidades | tentativas | P(escape), e = 0.50% | P(escape), e = 1.0% | P(escape), e = 2.0% | P(escape), e = 5.0% |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 28 | 24 h | 345 | 1.380 | > 99.9% | > 99.9% | > 99.9% | 100.0% |
| 28 | 168 h | 2.416 | 9.664 | 100.0% | 100.0% | 100.0% | 100.0% |
| 30 | 24 h | 86 | 344 | 82.2% | 96.8% | > 99.9% | > 99.9% |
| 30 | 168 h | 604 | 2.416 | > 99.9% | > 99.9% | 100.0% | 100.0% |
| 32 | 24 h | 21 | 84 | 34.4% | 57.0% | 81.7% | 98.7% |
| 32 | 168 h | 151 | 604 | 95.2% | 99.8% | > 99.9% | > 99.9% |
| 34 | 24 h | 5 | 20 | 9.5% | 18.2% | 33.2% | 64.2% |
| 34 | 168 h | 37 | 148 | 52.4% | 77.4% | 95.0% | > 99.9% |
| 36 | 24 h | 1 | 4 | 2.0% | 3.9% | 7.8% | 18.5% |
| 36 | 168 h | 9 | 36 | 16.5% | 30.4% | 51.7% | 84.2% |

## Conferências

- ✅ cada identidade de atacante aceita exatamente 4 reprovados e depois recebe 402
- ✅ 10 identidades dão 40 tentativas, nem uma a mais
- ✅ só com inconclusivos, 8 tentativas e depois 402
- ✅ o honesto faz 16 aprovações por identidade e depois recebe 402
- ✅ os truques são recusados (prova reaproveitada, chave repetida, sem assinatura, repetição)
- ✅ jobs que falham não gastam cota
