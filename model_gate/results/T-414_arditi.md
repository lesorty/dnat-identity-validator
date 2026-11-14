# Direção de recusa pelo procedimento de Arditi et al. (T-414)

local, verificação de funcionamento; a decisão oficial é regerada na nuvem com o código congelado. Procedimento: Arditi et al. 2024 (NeurIPS), §2.1, App. B (filtro) e App. C.1 (regra). Desvio: template do Qwen2.5 com bloco de sistema vazio; o artigo (Qwen 1) não tem.

Validação filtrada pelo base: 8 de 32 nocivos (refusal_metric > 0) e 31 de 32 inócuos (< 0).

Candidatos: 95 (5 posições × 20 camadas com l < 0,8·L). Passam em induce > 0 e kl < 0,1: 0.

**Nenhum candidato passa na regra.**

## Os 12 candidatos de menor bypass

| Posição | Camada | bypass | induce | KL | passa |
|---|---|---|---|---|---|
| -1 | 1 | -9.32 | -5.64 | 8.326 | não |
| -1 | 18 | -6.07 | -0.92 | 0.277 | não |
| -1 | 19 | -5.87 | -1.05 | 0.154 | não |
| -1 | 14 | -5.80 | -0.82 | 0.396 | não |
| -4 | 14 | -5.56 | -0.60 | 0.414 | não |
| -1 | 17 | -5.00 | -0.84 | 0.101 | não |
| -1 | 15 | -4.90 | -1.32 | 0.176 | não |
| -2 | 18 | -4.55 | -4.05 | 0.305 | não |
| -4 | 15 | -4.27 | -3.84 | 0.301 | não |
| -2 | 19 | -4.10 | -4.11 | 0.167 | não |
| -1 | 16 | -3.89 | -1.09 | 0.157 | não |
| -2 | 17 | -3.74 | -3.93 | 0.121 | não |

## Recusa gerada nos 32 nocivos (detector, 32 tokens)

| Condição | Taxa |
|---|---|
| base | 0.34 |
| ablado_t402 | 0.34 |

## S2 dos abliterados da T-908 na direção lida

| Direção | Posição | Camada | Modelo | Camada da abliteração | razão do gap |
|---|---|---|---|---|---|
| t402 | -1 | 6 | fumaca-abl-d6-a1-todas | 6 | -0.000 |
| t402 | -1 | 6 | fumaca-abl-d12-a1-todas | 12 | 0.927 |
