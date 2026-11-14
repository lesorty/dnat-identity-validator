# Fluxo inteiro no modo direto (T-811)

Verificação de funcionamento (T-811), não é dado do artigo. B e C usam um Juiz SIMULADO.

Base: minúsculo (tests/tiny.py) · 0.1 MB empacotado · digest `43fd8a01c9ba`

Máquina: Intel(R) Core(TM) 7 150U · 12 CPUs lógicas · linux 7.0.0-43-generic · Node v22.22.1 · 2026-11-13T18:36:40.284Z

Juiz liberado: `5706f8b58200dd5b8132e33e6b911b127d7f28f4ebb67c5ebb55fefe9ecb6806` · prereg `e2de3b5562ac39cd5b7363f04f9fbe95d193fcafb3d57f60383e1696b7f0ee9e`

## Desfechos

| Cenário | Saída do job | Derivado | Veredito | Alerta | Asset | Saldo depois |
|---|---|---|---|---|---|---|
| A | 0 | retained | failure | judge_failure | - | 20 |
| B | 0 | released | approved | - | 4 | 19 |
| C | 0 | retained | rejected | - | 5 | 14 |

A: Juiz real. B e C: Juiz SIMULADO (e2e/simulated_judge.js), só para exercitar recibo e cota.

## CVM de job de uso único (T-801)

| Cenário | CVM | Do warm pool | Subida (s) | Pico do cgroup (MB) | Pico RSS do job (MB) | Destruída |
|---|---|---|---|---|---|---|
| A | dnat-job-231e9294-be3 | sim | 0.6 | 47 | 22 | sim |
| B | dnat-job-76e43e7e-0f7 | não | 0.5 | 46 | 22 | sim |
| C | dnat-job-e0ee391f-8c4 | não | 1.3 | 46 | 22 | sim |

## Conferências

- ✅ A: Juiz real termina em falha (prereg sem valores, T-606)
- ✅ A: reserva devolvida (saldo 20)
- ✅ B: aprovado, derivado usável no contrato
- ✅ B: cota 1 (saldo 19)
- ✅ C: reprovado, derivado inativo
- ✅ C: cota 5 (saldo 14)
- ✅ uso único: três jobs em três CVMs diferentes
- ✅ uso único: cada CVM destruída depois do job, com um job só
- ✅ uso único: memória de pico registrada

## Tempo por etapa (s)

| Etapa | s |
|---|---|
| IPFS em memória | 0.01 |
| hardhat node e implantação do contrato | 1.45 |
| CVM2 (builder, modo direto) | 0.31 |
| pacote da bateria depositado pelo operador (judge_cli battery) | 0.18 |
| liberar o Juiz atual na lista permitida (judge_cli allow) | 0.17 |
| CVM1 (api-server) | 0.62 |
| identidade com prova de trabalho (d = 12) | 0.11 |
| depósito do modelo base (register-model) | 0.28 |
| dataset (register-dataset) | 0.17 |
| aplicação de fine-tuning simulado (register-application, build no CVM2) | 0.60 |
| compra de acesso (purchase-access) | 0.16 |
| referência do pai depositada pelo operador (judge_cli reference) | 0.18 |
| A · fine-tuning + Juiz real (model_gate) | 3.95 |
| B · fine-tuning + Juiz SIMULADO aprovando | 1.78 |
| C · fine-tuning + Juiz SIMULADO reprovando | 2.76 |
