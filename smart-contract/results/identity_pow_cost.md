# Custo da prova de trabalho por dificuldade (T-1705)

Máquina: Intel(R) Core(TM) 7 150U, 12 CPUs lógicas, Node v22.22.1, linux 7.0.0-43-generic.
Taxa medida: 0.242 milhões de hashes por segundo, um núcleo.

| d (bits) | repetições | média (s) | mediana (s) | mín (s) | máx (s) | esperado 2^d ÷ taxa (s) |
|---:|---:|---:|---:|---:|---:|---:|
| 12 | 5 | 0.0525 | 0.0480 | 0.0127 | 0.1232 | 0.0169 |
| 13 | 5 | 0.0277 | 0.0147 | 0.0130 | 0.0502 | 0.0339 |
| 14 | 5 | 0.0196 | 0.0176 | 0.0134 | 0.0311 | 0.0678 |
| 15 | 5 | 0.0594 | 0.0378 | 0.0049 | 0.1321 | 0.1355 |
| 16 | 5 | 0.4431 | 0.2344 | 0.0005 | 1.12 | 0.2711 |
| 17 | 5 | 1.38 | 1.50 | 0.0871 | 2.41 | 0.5422 |
| 18 | 5 | 0.7927 | 0.8495 | 0.2383 | 1.59 | 1.08 |
| 19 | 5 | 2.42 | 3.01 | 0.2222 | 5.03 | 2.17 |
| 20 | 5 | 7.91 | 7.68 | 3.06 | 12.24 | 4.34 |
| 21 | 5 | 10.61 | 11.74 | 3.11 | 19.78 | 8.68 |
| 22 | 5 | 9.52 | 10.80 | 3.17 | 13.49 | 17.35 |
| 23 | 5 | 41.76 | 36.22 | 17.84 | 75.13 | 34.70 |
| 24 | 5 | 46.51 | 22.46 | 12.57 | 104 | 69.40 |

O tempo de uma prova é geométrico: média 2^d hashes e desvio quase igual à média. Com poucas
repetições a média medida oscila bastante; a coluna esperada é a estimativa para o modelo de custo.

medido numa máquina local; a medida em VM de 4 vCPU fica para a T-210.
