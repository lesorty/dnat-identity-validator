# Números do artigo

Gerado por `tools/numeros.py` (`make numeros`). Origem: **nuvem** (pacote importado, commit congelado) ou **local** (verificação de funcionamento, marcado em vermelho no PDF).

| Macro | Valor | Origem | Descrição | Arquivo |
|---|---|---|---|---|
| `\numGasReciboAprovado` | 494,028 | local | gás do recibo de um aprovado (T-709) | `smart-contract/results/gas.json` |
| `\numGasReciboReprovado` | 474,140 | local | gás do recibo de um reprovado (T-709) | `smart-contract/results/gas.json` |
| `\numGasRevogacao` | 56,288 | local | gás da revogação (T-709) | `smart-contract/results/gas.json` |
| `\numHashesPorSegundo` | 241,744 | local | hashes SHA-256 por segundo, 1 núcleo (T-1705) | `smart-contract/results/identity_pow_cost.json` |
| `\numProvaDvinteSegundos` | 7.7 | local | mediana da prova de trabalho com d = 20, em s (T-1705) | `smart-contract/results/identity_pow_cost.json` |
| `\numIdentidadeDUmaHora` | 30 | local | menor d em que criar uma identidade custa 1 h de um núcleo (Teste 10) | `smart-contract/results/T10_preco_identidade.json` |
| `\numIdentidadeConferirMicrossegundos` | 4.1 | local | tempo de conferir uma prova, em µs (Teste 10) | `smart-contract/results/T10_preco_identidade.json` |
| `\numAtacanteTentativasPorIdentidade` | 4 | local | tentativas reprovadas que uma identidade consegue (Teste 11) | `smart-contract/results/T11_atacante_sybil.json` |
| `\numHonestoAprovacoesPorIdentidade` | 16 | local | aprovações que uma identidade honesta consegue (Teste 11) | `smart-contract/results/T11_atacante_sybil.json` |
| `\numRazaoEscapeHonestoUmPorCento` | 400 | local | custo de um escape ÷ custo de uma aprovação honesta, com e = 1% (Teste 11) | `smart-contract/results/T11_atacante_sybil.json` |
| `\numVazaoLoteUm` | 19.8 | local | tokens/s em 4 vCPU, lote 1 (T-208) | `model_gate/results/T-208_vazao.json` |
| `\numVazaoLoteQuatro` | 39.9 | local | tokens/s em 4 vCPU, lote 4 (T-208) | `model_gate/results/T-208_vazao.json` |
| `\numAvaliadorMinutosVeredito` | 264 | local | minutos do avaliador por veredito (T-309) | `model_gate/results/T-309_avaliador.json` |
| `\numAvaliadorSegundosItem` | 50.1 | local | segundos do avaliador por item (T-309) | `model_gate/results/T-309_avaliador.json` |
| `\numAncorasTotal` | 143 | local | âncoras recusadas nas duas condições (T-301) | `model_gate/results/T-301_ancoras.json` |
| `\numArditiCandidatos` | 95 | local | candidatos de direção avaliados (T-414) | `model_gate/results/T-414_arditi.json` |
| `\numArditiPassam` | 0 | local | candidatos que passam na regra de Arditi (T-414) | `model_gate/results/T-414_arditi.json` |
| `\numArditiNocivosRecusados` | 8 of 32 | local | nocivos da validação que o base recusa (T-414) | `model_gate/results/T-414_arditi.json` |
| `\numTreinoPicoRssGB` | 6.3 | local | pico de RSS do treino LoRA na CVM de uso único, GB (T-806) | `smart-contract/results/T-806_lora_uso_unico.json` |
| `\numTreinoSegundos` | 163 | local | segundos de treino LoRA, 10 passos (T-806) | `smart-contract/results/T-806_lora_uso_unico.json` |
