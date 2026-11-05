# T-208 · Vazão do Qwen2.5-0.5B em 4 CPUs e custo de S1

Medido em 2026-11-05 com `experiments/bench_throughput.py` (gerador da T-205, medidor da
T-207, registro da T-206). Comprimento forçado, 8 prompts seguros do XSTest, 3 repetições,
float32, 4 threads fixadas em 2 núcleos P com HT (`taskset -c 0-3`), mesmo formato de uma
VM de 4 vCPU. Dados: [T-208_vazao.json](T-208_vazao.json).

## Vazão e estimativa (pior caso: toda resposta até o teto)

Vazão medida: Intel(R) Core(TM) 7 150U, CPUs [0, 1, 2, 3], 4 threads, commit `05a27fd`, run `t208_20261105T163912_f9420c`.

| Tokens | Lote 1 (tok/s) | Lote 4 (tok/s) | Lote 8 (tok/s) |
|---|---|---|---|
| 64 | 19.8 ± 0.4 | 39.9 ± 0.4 | 57.0 ± 0.8 |
| 512 | 20.0 ± 0.2 | 37.1 ± 0.1 | 50.4 ± 2.9 |

Custo de geração de S1 (pior caso, 250 itens, 12 configurações, estágio 2 em 100% dos itens, sem o avaliador):

| Lote | Estágio 1 (min/config) | Estágio 2 (min/config) | Por config (min) | Veredito (min) | Cabe em 80 min? |
|---|---|---|---|---|---|
| 1 | 13.5 | 106.6 | 106.6 (geração única) | 1279 | não (16.0×) |
| 4 | 6.7 | 57.5 | 57.5 (geração única) | 690 | não (8.6×) |
| 8 | 4.7 | 42.3 | 42.3 (geração única) | 508 | não (6.4×) |

Variante em dois estágios (E13), com o estágio 2 em 30% dos itens:

| Lote | Estágio 1 (min/config) | Estágio 2 (min/config) | Por config (min) | Veredito (min) | Cabe em 80 min? |
|---|---|---|---|---|---|
| 1 | 13.5 | 32.0 | 45.4 (dois estágios) | 545 | não (6.8×) |
| 4 | 6.7 | 17.3 | 23.9 (dois estágios) | 287 | não (3.6×) |
| 8 | 4.7 | 12.7 | 17.4 (dois estágios) | 209 | não (2.6×) |

## Leitura

- **No pior caso, a geração de S1 não cabe nos 80 min** (E14 §6.2) com nenhum lote:
  6–16× acima com geração única, 2,6–6,8× com dois estágios. Só o estágio 1 de 64 tokens
  nas 12 configurações já dá 56–162 min. E isso ainda não inclui o avaliador.
- O pior caso exagera: respostas gulosas param no EOS, e recusas são curtas. O custo real
  depende do comprimento médio das respostas do derivado, que ainda não foi medido nos
  nocivos. Como referência, nos 10 prompts seguros do XSTest com teto de 128 tokens, a
  média foi de 105 tokens.
- O lote ajuda até 2,5×, mas o lote canônico do veredito é 1 (T-205). No base, o lote 4
  deu o mesmo texto que o lote 1 nos 10 prompts conferidos.
- Os números são otimistas: núcleos P de notebook a até 5,4 GHz, contra os ~3 GHz de um
  Xeon de nuvem. A repetição na VM real fica para a T-210.

## Alavancas (para T-314 e T-1601)

1. Medir o comprimento médio real das respostas nos nocivos (base e um derivado abliterado).
2. Lote > 1 no veredito, se o texto não mudar em relação ao lote 1 numa amostra maior.
3. Dois estágios (E13) ou menos itens por configuração (subir δ até 0,15, E14).
4. Menos configurações: C_job ou formatos em cache quando o derivado for idêntico.
5. Mais vCPUs por veredito (T-1601).

## Comprimento real das respostas (base, lote 1, teto de 512)

Medido em 2026-11-05 com `experiments/measure_lengths.py`, commit `def5d4d`, nas duas
condições fixas da E14 §6.2. Dados: [T-208_comprimento.json](T-208_comprimento.json).

| Condição | Conjunto | Itens | Média (tokens) | Mediana | No teto | s/item |
|---|---|---|---|---|---|---|
| vazio | StrongREJECT small | 60 | 239 | 224 | 13% | 11,6 |
| vazio | XSTest seguros | 25 | 188 | 161 | 4% | 9,0 |
| vazio | XSTest contrastes inseguros | 25 | 79 | 53 | 0% | 3,9 |
| padrão | StrongREJECT small | 60 | 205 | 178 | 10% | 10,2 |
| padrão | XSTest seguros | 25 | 199 | 217 | 4% | 9,8 |
| padrão | XSTest contrastes inseguros | 25 | 68 | 49 | 0% | 3,4 |

- As respostas reais têm cerca de 40–45% do teto nos nocivos: o custo real é ~2,3× menor que
  o pior caso, mas **ainda não cabe**.
- O base é pouco alinhado: por uma heurística grosseira (resposta que começa com "I'm sorry",
  "I can't" etc.), recusa só 20/60 (vazio) e 30/60 (padrão) dos nocivos. Respostas longas
  nos nocivos são, em boa parte, cumprimento. Isso também dimensiona as âncoras: ~1/3 a 1/2
  do StrongREJECT por condição.

### Custo reestimado (12 configurações, sem o avaliador, lote 1)

| Cenário | min/config | Veredito | × 80 min |
|---|---|---|---|
| A · 250 itens por config, na mistura medida (60 nocivos : 25 seguros : 25 contrastes) | 37,0 | 444 min | 5,6× |
| B · só âncoras (48) + 50 do XSTest; respostas do pai em cache | 14,1 | 169 min | 2,1× |
| B · só âncoras (68, δ = 0,10) + 50 do XSTest | 17,7 | 213 min | 2,7× |
| B (48 âncoras) com lote 4 | — | ~91 min | ~1,1× |

O cenário B supõe que o derivado só precisa responder às âncoras (itens que o pai recusa,
já em cache) e a uma amostra do XSTest. **Essa suposição de desenho precisa ser confirmada**
na especificação da bateria (T-302, T-303). O ganho do lote 4 foi medido com comprimento
forçado; com comprimentos variados, o padding reduz o ganho.
