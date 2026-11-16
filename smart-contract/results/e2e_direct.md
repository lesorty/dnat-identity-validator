# Fluxo inteiro no modo direto (T-811)

Verificação de funcionamento (T-811), não é dado do artigo. B e C usam um Juiz SIMULADO.

Base: minúsculo (tests/tiny.py) · 0.1 MB empacotado · digest `43fd8a01c9ba`

Máquina: Intel(R) Core(TM) 7 150U · 12 CPUs lógicas · linux 7.0.0-43-generic · Node v22.22.1 · 2026-11-16T17:27:48.213Z

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
- ✅ B e C: registro do Juiz selado, aberto pelo operador e igual ao hash do recibo

## Tempo por etapa (s)

| Etapa | s |
|---|---|
| IPFS em memória | 0.02 |
| hardhat node e implantação do contrato | 2.30 |
| CVM2 (builder, modo direto) | 0.32 |
| CVM de job (executor, modo direto) | 0.32 |
| pacote da bateria depositado pelo operador (judge_cli battery) | 0.36 |
| liberar o Juiz atual na lista permitida (judge_cli allow) | 0.30 |
| CVM1 (api-server) | 0.93 |
| identidade com prova de trabalho (d = 12) | 0.04 |
| depósito do modelo base (register-model) | 0.41 |
| dataset (register-dataset) | 0.20 |
| aplicação de fine-tuning simulado (register-application, build no CVM2) | 2.34 |
| compra de acesso (purchase-access) | 0.17 |
| referência do pai depositada pelo operador (judge_cli reference) | 0.34 |
| A · fine-tuning + Juiz real (model_gate) | 7.20 |
| B · fine-tuning + Juiz SIMULADO aprovando | 2.71 |
| C · fine-tuning + Juiz SIMULADO reprovando | 2.57 |
