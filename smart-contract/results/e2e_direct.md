# Fluxo inteiro no modo direto (T-811)

Verificação de funcionamento (T-811), não é dado do artigo. B e C usam um Juiz SIMULADO.

Máquina: Intel(R) Core(TM) 7 150U · 12 CPUs lógicas · linux 7.0.0-43-generic · Node v22.22.1 · 2026-11-13T12:28:02.018Z

Juiz liberado: `5706f8b58200dd5b8132e33e6b911b127d7f28f4ebb67c5ebb55fefe9ecb6806` · prereg `088cdb1829e2518b29d3bd10d81405847fc394a3b1f6cf6f3a09ef48c5a259fa`

## Desfechos

| Cenário | Saída do job | Derivado | Veredito | Alerta | Asset | Saldo depois |
|---|---|---|---|---|---|---|
| A | 0 | retained | failure | judge_failure | - | 20 |
| B | 0 | released | approved | - | 4 | 19 |
| C | 0 | retained | rejected | - | 5 | 14 |

A: Juiz real. B e C: Juiz SIMULADO (e2e/simulated_judge.js), só para exercitar recibo e cota.

## Conferências

- ✅ A: Juiz real termina em falha (prereg sem valores, T-606)
- ✅ A: reserva devolvida (saldo 20)
- ✅ B: aprovado, derivado usável no contrato
- ✅ B: cota 1 (saldo 19)
- ✅ C: reprovado, derivado inativo
- ✅ C: cota 5 (saldo 14)

## Tempo por etapa (s)

| Etapa | s |
|---|---|
| IPFS em memória | 0.01 |
| hardhat node e implantação do contrato | 4.30 |
| CVM2 (builder, modo direto) | 0.32 |
| CVM de job (executor, modo direto) | 0.32 |
| pacote da bateria depositado pelo operador (judge_cli battery) | 0.66 |
| liberar o Juiz atual na lista permitida (judge_cli allow) | 0.49 |
| CVM1 (api-server) | 1.85 |
| identidade com prova de trabalho (d = 12) | 0.13 |
| depósito do modelo base (register-model) | 0.59 |
| dataset (register-dataset) | 0.21 |
| aplicação de fine-tuning simulado (register-application, build no CVM2) | 1.33 |
| compra de acesso (purchase-access) | 0.18 |
| referência do pai depositada pelo operador (judge_cli reference) | 0.65 |
| A · fine-tuning + Juiz real (model_gate) | 10.44 |
| B · fine-tuning + Juiz SIMULADO aprovando | 2.57 |
| C · fine-tuning + Juiz SIMULADO reprovando | 2.56 |
