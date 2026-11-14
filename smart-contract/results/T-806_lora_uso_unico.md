# Fine-tuning LoRA numa CVM de uso único (T-806)

Verificação de funcionamento (T-806), não é dado do artigo.

Base: Qwen2.5-0.5B-Instruct `05b61d72bec3` · 10 passos, 32 exemplos, script da T-901 · máquina: Intel(R) Core(TM) 7 150U, 12 CPUs

| Item | Valor |
|---|---|
| Aplicação cifrada no IPFS | 317 MB |
| Perda final / passos | 0.00003 / 10 |
| Tempo do script (train_seconds) | 162.608 s |
| Derivado (adaptador) cifrado no IPFS | 15 MB · digest `cb6d0feeda78` |
| CVM de job | dnat-job-89cc64c3-618 · subida 1.8 s · pico do cgroup (com cache de página) 8192 MB · pico RSS 6472 MB · destruída sim |

## Conferências

- ✅ o job de treino termina com sucesso e devolve só as métricas permitidas
- ✅ derivado retido, com digest
- ✅ no IPFS o derivado só existe cifrado (envelope DNATENC2)
- ✅ CVM de uso único destruída depois do job, com a memória de pico registrada
- ✅ sem Juiz liberado nem referência: a reserva da cota volta (saldo 20)

## Tempo por etapa (s)

| Etapa | s |
|---|---|
| IPFS em disco | 0.0 |
| hardhat node e implantação do contrato | 5.5 |
| CVM1 (api-server) com CVMs de job de uso único | 2.2 |
| identidade com prova de trabalho (d = 12) | 0.2 |
| depósito do Qwen2.5-0.5B (register-model) | 133.5 |
| dataset benigno (register-dataset) | 0.3 |
| aplicação LoRA (register-application: builder com torch, transformers e peft) | 684.0 |
| compra de acesso (purchase-access) | 0.2 |
| fine-tuning LoRA (10 passos) numa CVM de uso único | 777.4 |
