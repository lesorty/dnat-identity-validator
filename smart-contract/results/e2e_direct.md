# Fluxo inteiro no modo direto (T-811)

Verificação de funcionamento (T-811), não é dado do artigo. B e C usam um Juiz SIMULADO.

Base: minúsculo (tests/tiny.py) · 0.1 MB empacotado · digest `43fd8a01c9ba`

Máquina: Intel(R) Core(TM) 7 150U · 12 CPUs lógicas · linux 7.0.0-43-generic · Node v22.22.1 · 2026-11-15T19:06:43.445Z

Juiz liberado: `957f0ec05637eee3d8629cab36dbf5a3f69cc23426bb1cc2285c9be51cc32392` · prereg `e2de3b5562ac39cd5b7363f04f9fbe95d193fcafb3d57f60383e1696b7f0ee9e`

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
| hardhat node e implantação do contrato | 2.21 |
| CVM2 (builder, modo direto) | 0.33 |
| CVM de job (executor, modo direto) | 0.32 |
| pacote da bateria depositado pelo operador (judge_cli battery) | 0.55 |
| liberar o Juiz atual na lista permitida (judge_cli allow) | 0.27 |
| CVM1 (api-server) | 1.27 |
| identidade com prova de trabalho (d = 12) | 0.17 |
| depósito do modelo base (register-model) | 0.45 |
| dataset (register-dataset) | 0.22 |
| aplicação de fine-tuning simulado (register-application, build no CVM2) | 2.87 |
| compra de acesso (purchase-access) | 0.16 |
| referência do pai depositada pelo operador (judge_cli reference) | 0.60 |
| A · fine-tuning + Juiz real (model_gate) | 8.63 |
| B · fine-tuning + Juiz SIMULADO aprovando | 3.79 |
| C · fine-tuning + Juiz SIMULADO reprovando | 3.10 |
