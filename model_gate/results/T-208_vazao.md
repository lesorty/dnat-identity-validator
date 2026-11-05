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
