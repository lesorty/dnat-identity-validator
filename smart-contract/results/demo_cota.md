# Demonstração da identidade e da cota (T-1707)

Demonstração do Teste 9 (T-1707), sem cadeia nem executor; veredito SIMULADO no corpo do job.

| Passo | HTTP | Cobrado | Saldo | Erro |
|---|---|---|---|---|
| 1. identidade registrada com prova de trabalho | 201 | - | 20 | - |
| 2a. job sem assinatura | 401 | - | - | - |
| 2b. job com carimbo de 10 min atrás | 401 | - | - | - |
| 3. job que falha: reserva devolvida | 200 | 0 | 20 | - |
| 4.1 job reprovado | 200 | 5 | 15 | - |
| 4.2 job reprovado | 200 | 5 | 10 | - |
| 4.3 job reprovado | 200 | 5 | 5 | - |
| 4.4 job reprovado | 200 | 5 | 0 | - |
| 5. 5º job, sem saldo para a reserva | 402 | - | - | insufficient quota: balance 0, a job reserves 5 |

## Conferências

- ✅ registro abre saldo Q = 20
- ✅ sem assinatura e carimbo velho: 401
- ✅ falha devolve a reserva (saldo continua 20)
- ✅ 4 reprovados esgotam o saldo
- ✅ o 5º job é recusado com 402
- ✅ contagens: 4 reprovados, 1 falha
