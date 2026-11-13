# Fluxo inteiro no modo direto (T-811)

Verificação de funcionamento (T-811), não é dado do artigo. B e C usam um Juiz SIMULADO.

Base: minúsculo (tests/tiny.py) · 0.1 MB empacotado · digest `43fd8a01c9ba`

Máquina: Intel(R) Core(TM) 7 150U · 12 CPUs lógicas · linux 7.0.0-43-generic · Node v22.22.1 · 2026-11-13T14:19:07.609Z

Juiz liberado: `5706f8b58200dd5b8132e33e6b911b127d7f28f4ebb67c5ebb55fefe9ecb6806` · prereg `e2de3b5562ac39cd5b7363f04f9fbe95d193fcafb3d57f60383e1696b7f0ee9e`

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
| IPFS em memória | 0.02 |
| hardhat node e implantação do contrato | 1.25 |
| CVM2 (builder, modo direto) | 0.31 |
| CVM de job (executor, modo direto) | 0.31 |
| pacote da bateria depositado pelo operador (judge_cli battery) | 0.19 |
| liberar o Juiz atual na lista permitida (judge_cli allow) | 0.15 |
| CVM1 (api-server) | 0.63 |
| identidade com prova de trabalho (d = 12) | 0.04 |
| depósito do modelo base (register-model) | 0.30 |
| dataset (register-dataset) | 0.17 |
| aplicação de fine-tuning simulado (register-application, build no CVM2) | 0.58 |
| compra de acesso (purchase-access) | 0.17 |
| referência do pai depositada pelo operador (judge_cli reference) | 0.18 |
| A · fine-tuning + Juiz real (model_gate) | 3.64 |
| B · fine-tuning + Juiz SIMULADO aprovando | 1.20 |
| C · fine-tuning + Juiz SIMULADO reprovando | 1.23 |
