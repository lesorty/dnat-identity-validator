# Teste 10: o preço da identidade

Teste 10 (P6): o preço da identidade. Medido na máquina onde rodou; o d acima do medido é extrapolado de 2^d ÷ taxa.

Máquina: Intel(R) Core(TM) 7 150U, 12 CPUs lógicas, Node v22.22.1. Commit `183d193`.

## Taxas de hash

| Quem | Hashes SHA-256 por segundo |
|---|---:|
| 1 núcleo | 252.053 |
| 12 núcleos | 1.072.429 |

## Prova medida num núcleo

| d | repetições | mediana | média | esperado (2^d ÷ taxa) |
|---:|---:|---:|---:|---:|
| 16 | 5 | 166.3 ms | 149.1 ms | 260.0 ms |
| 17 | 5 | 258.5 ms | 341.6 ms | 520.0 ms |
| 18 | 5 | 661.5 ms | 1.2 s | 1.0 s |
| 19 | 5 | 2.8 s | 2.8 s | 2.1 s |
| 20 | 5 | 2.9 s | 4.0 s | 4.2 s |
| 21 | 5 | 8.7 s | 10.8 s | 8.3 s |
| 22 | 5 | 11.3 s | 13.1 s | 16.6 s |
| 23 | 5 | 12.1 s | 21.0 s | 33.3 s |
| 24 | 5 | 42.5 s | 60.6 s | 66.6 s |

Lei do custo: inclinação de log2(hashes) em d = **0.997 ± 0.107** (esperado 1), razão Σhashes ÷ Σ2^d = **0.86** (esperado 1), com 45 provas.

## Conferir custa um hash, em qualquer d

| d | conferências | tempo por conferência |
|---:|---:|---:|
| 8 | 100.000 | 4.07 µs |
| 12 | 100.000 | 3.89 µs |
| 16 | 100.000 | 4.12 µs |

## Tempo para criar uma identidade (extrapolado de 2^d ÷ taxa)

| d | 1 núcleo | 12 núcleos |
|---:|---:|---:|
| 20 | 4.2 s | 977.8 ms |
| 24 | 66.6 s | 15.6 s |
| 26 | 4.4 min | 62.6 s |
| 28 | 17.7 min | 4.2 min |
| 30 | 71.0 min | 16.7 min |
| 32 | 4.7 h | 66.7 min |
| 36 | 3.2 dias | 17.8 h |

**d de referência** (menor d em que uma identidade custa pelo menos o alvo):

| Alvo | 1 núcleo | 12 núcleos |
|---|---:|---:|
| 1 h | 30 | 32 |
| 5 h | 33 | 35 |

Razão criar ÷ conferir em d = 30, num núcleo: **1.03e+9**.

## A prova não se reaproveita

| Caso | HTTP | Esperado |
|---|---:|---:|
| a prova de A registra A | 201 | 201 |
| a mesma prova não registra outra chave | 400 | 400 |
| prova feita para outra implantação é recusada | 400 | 400 |
| a mesma chave não registra duas vezes | 409 | 409 |

## Conferências

- ✅ a lei do custo vale: inclinação de log2(hashes) em d a até 3 erros-padrão de 1
- ✅ a média de hashes tem a ordem de 2^d: razão agregada entre 1/3 e 3
- ✅ conferir não depende de d: o maior tempo é menos que 3× o menor
- ✅ conferir custa menos de 1 ms
- ✅ todas as provas conferidas eram válidas
- ✅ a prova não se reaproveita (outra chave, outra implantação, chave repetida)
- ✅ os núcleos juntos fazem mais hashes que um núcleo
