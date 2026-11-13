# Fluxo inteiro no modo direto (T-811)

Verificação de funcionamento (T-811), não é dado do artigo. B e C usam um Juiz SIMULADO.

Máquina: Intel(R) Core(TM) 7 150U · 12 CPUs lógicas · linux 7.0.0-43-generic · Node v22.22.1 · 2026-11-13T11:35:17.530Z

Juiz liberado: `5eed9f73f298cf8cd820d282e43f2eb2803cdb43c13804328f8462f7720ab2a7` · prereg `088cdb1829e2518b29d3bd10d81405847fc394a3b1f6cf6f3a09ef48c5a259fa`

## Desfechos

| Cenário | Saída do job | Derivado | Veredito | Alerta | Asset | Saldo depois |
|---|---|---|---|---|---|---|
| A | 0 | retained | failure | judge_failure | - | 20 |
| B | 0 | released | approved | - | 4 | 19 |
| C | 0 | retained | rejected | - | 5 | 14 |

A: Juiz real. B e C: Juiz SIMULADO (e2e/simulated_judge.js), só para exercitar recibo e cota.

## Conferências

- ✅ A: Juiz real termina em falha (estágios da nuvem)
- ✅ A: reserva devolvida (saldo 20)
- ✅ B: aprovado, derivado usável no contrato
- ✅ B: cota 1 (saldo 19)
- ✅ C: reprovado, derivado inativo
- ✅ C: cota 5 (saldo 14)

## Tempo por etapa (s)

| Etapa | s |
|---|---|
| IPFS em memória | 0.00 |
| hardhat node e implantação do contrato | 2.21 |
| CVM2 (builder, modo direto) | 0.32 |
| CVM de job (executor, modo direto) | 0.32 |
| liberar o Juiz atual na lista permitida (judge_cli allow) | 0.27 |
| CVM1 (api-server) | 0.93 |
| identidade com prova de trabalho (d = 12) | 0.04 |
| depósito do modelo base (register-model) | 0.41 |
| dataset (register-dataset) | 0.20 |
| aplicação de fine-tuning simulado (register-application, build no CVM2) | 0.90 |
| compra de acesso (purchase-access) | 0.17 |
| referência do pai depositada pelo operador (judge_cli reference) | 0.30 |
| A · fine-tuning + Juiz real (model_gate) | 6.57 |
| B · fine-tuning + Juiz SIMULADO aprovando | 1.51 |
| C · fine-tuning + Juiz SIMULADO reprovando | 1.47 |
