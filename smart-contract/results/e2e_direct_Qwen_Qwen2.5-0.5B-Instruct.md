# Fluxo inteiro no modo direto (T-811)

Verificação de funcionamento (T-811), não é dado do artigo. B e C usam um Juiz SIMULADO.

Base: Qwen__Qwen2.5-0.5B-Instruct · 786.3 MB empacotado · digest `05b61d72bec3`

Máquina: Intel(R) Core(TM) 7 150U · 12 CPUs lógicas · linux 7.0.0-43-generic · Node v22.22.1 · 2026-11-13T14:04:16.906Z

Juiz liberado: `5706f8b58200dd5b8132e33e6b911b127d7f28f4ebb67c5ebb55fefe9ecb6806` · prereg `e2de3b5562ac39cd5b7363f04f9fbe95d193fcafb3d57f60383e1696b7f0ee9e`

## Desfechos

| Cenário | Saída do job | Derivado | Veredito | Alerta | Asset | Saldo depois |
|---|---|---|---|---|---|---|
| A | 0 | retained | failure | custody_error | - | 20 |
| B | 0 | retained | failure | custody_error | - | 20 |
| C | 0 | retained | failure | custody_error | - | 20 |

A: Juiz real. B e C: Juiz SIMULADO (e2e/simulated_judge.js), só para exercitar recibo e cota.

## Conferências

- ✅ A: Juiz real termina em falha (prereg sem valores, T-606)
- ✅ A: reserva devolvida (saldo 20)
- ❌ B: aprovado, derivado usável no contrato
- ❌ B: cota 1 (saldo 19)
- ❌ C: reprovado, derivado inativo
- ❌ C: cota 5 (saldo 14)

## Tempo por etapa (s)

| Etapa | s |
|---|---|
| IPFS em memória | 0.00 |
| hardhat node e implantação do contrato | 1.27 |
| CVM2 (builder, modo direto) | 0.31 |
| CVM de job (executor, modo direto) | 0.32 |
| pacote da bateria depositado pelo operador (judge_cli battery) | 0.18 |
| liberar o Juiz atual na lista permitida (judge_cli allow) | 0.15 |
| CVM1 (api-server) | 0.63 |
| identidade com prova de trabalho (d = 12) | 0.02 |
| depósito do modelo base (register-model) | 64.05 |
| dataset (register-dataset) | 0.18 |
| aplicação de fine-tuning simulado (register-application, build no CVM2) | 0.67 |
| compra de acesso (purchase-access) | 0.17 |
| referência do pai depositada pelo operador (judge_cli reference) | 0.25 |
| A · fine-tuning + Juiz real (model_gate) | 199.60 |
| B · fine-tuning + Juiz SIMULADO aprovando | 197.91 |
| C · fine-tuning + Juiz SIMULADO reprovando | 189.26 |
