# Ida ao GCP: o que está pronto, o que falta e onde fica cada coisa

Estado em 26/11/2026 (o piloto vem antes da campanha; o tamanho da campanha se decide com o orientador depois dele). Atualize este arquivo a cada mudança. Horas de GPU por teste e os três perfis
(robusto, mediano, simples): `HORAS_GPU.md`. Os comandos estão em
`tools/cloud/README.md` e o funcionamento dos roteiros em `tools/testes/README.md`.

## 1. Pode começar?

| Rodada | Pode rodar? | O que segura |
|---|---|---|
| **Ensaio** (`campanha_gpu.sh iniciar ensaio`, ~30 min, não é dado; **T-1415**) | **Sim**, assim que a VM existir (T-1603) | nada no código; o ensaio é justamente a conferência da GPU |
| **Piloto** (`campanha_gpu.sh iniciar piloto`, ~3 h de GPU, não é dado; decidido em 26/11) | **Sim**, é a **primeira** rodada (o ensaio fica opcional) | nada: prereg e bateria próprios, sem congelamento nem revisão humana; o tamanho de cada teste está em `HORAS_GPU.md` §0 |
| **Fase 1** (T1, T9, T10, T11, T2) | **Não** | bateria final e parte secreta (**T-304**): o T1 empacota a bateria da campanha, e o T2 depende do T1; congelar o commit (`make congelar`) antes de rodar |
| **Fase 2** (T3, T5, T6, T7, T8, T11, T4) | Não | a fase 1, a revisão humana da proposta do T2, o `prereg.yaml` preenchido (T-606) e o commit congelado |

Decisões que são suas (sem elas a fase 1 não começa ou o resultado não vale):

1. **Bateria da campanha** (T-301/T-304): composição e parte secreta. Rodar a fase 1 com a bateria
   padrão e trocá-la depois obriga a refazer a calibração.
2. **GPU na campanha** (D2, 25/11, proposta; **T-1612**): medir na GPU, com a CPU como cronômetro da meta G1 e
   como conferência no T1.
3. **Avaliador do portão** (T-309): os roteiros usam o Qwen3Guard-Gen-4B.
4. **Juiz de referência:** o tipo está decidido (aberto, dentro da CVM). O modelo exato está em aberto;
   o configurado é o gpt-oss-20b.
5. **Plano da população** (`model_gate/experiments/testes/planos.yaml`): uma proposta para confirmar
   com o orientador.

## 2. O que combinamos (página dos testes) contra o que os roteiros fazem

| Teste | Combinado | Nos roteiros | Diferença |
|---|---|---|---|
| T1 | base 2×, huihui v3, cronômetro em 4 vCPU (≤ 80 min) | base 2× e huihui na GPU; huihui na CPU de 4 vCPU (cronômetro G1 e conferência CPU × GPU) | — |
| T2 | 12 derivados (6 H, 6 C), δ com ~5% de falso alarme, prereg commitado antes | igual; a proposta sai em `prereg_proposto.yaml` e uma pessoa congela | — |
| T3 | 20 derivados, **F0**, F1, F2, F3, doses, linha de base de Hurtado | 20 derivados F1, F2, F3 com as doses; Hurtado na análise (z-soma, Youden no T2) | **falta F0** (endurecido): precisa do conjunto de recusas estendidas (Abu Shairah); **T-909** |
| T4 | os 13 Llama do T5 dão o primeiro sinal | pendente | **Llama sob custódia** (**T-212**), licença da Meta (T-1103), população (T-913) |
| T5 | 21 do campo (8 Qwen + 13 Llama); dá para começar pelos 8 Qwen | os 8 Qwen; compara taxas e distribuição de S1, ρ e E1 com o T3 | os 13 Llama (mesmo bloqueio do T4: T-212) |
| T6 | abliteração + **LoRA de disfarce**, 3 rodadas, só o veredito, custo em cota | 3 rodadas de abliteração com bisseção de α; rótulo nos aprovados; cota gasta | **falta o LoRA de disfarce** (é a LoRA de cura da **T-1203**) |
| T7 | casos A, B, C; ablação S1/S2/S3; VM comum × CVM | igual; o overhead roda nesta VM e numa VM comum à parte | a VM comum é uma segunda VM |
| T8 | reprovado retido, aprovado com recibo, auditor abre o registro, revogação de aprovado **e de base em cascata** | igual (a cascata entrou em 25/11, nos dois roteiros) | — |
| T9 | casos fixos de identidade e cota | igual | — |
| T10 | d de 16 a 27, 3 repetições, 1 núcleo e todos, **GPU se houver** | igual; a taxa de SHA-256 da GPU vem do hashcat (passo opcional) | — |
| T11 | d = 20, e do T6, preço do T10 | igual; refeito na fase 2 com o e do T6 | — |

Todas essas pendências estão no backlog e na fila (`DSN2027/backlog/FILA.md`): T-1612 e T-304 entre os
desbloqueios humanos; T-1415 e T-212 na etapa do sistema na nuvem; T-909, T-913 e T-1203 nas etapas da
população e dos testes.

## 3. O que fica salvo e onde

Fica tudo na VM, em `$MODEL_GATE_DATA/testes/<perfil>/<campanha>/T*/`:
- `estado.json` e `eventos.jsonl` (com fsync);
- `ambiente_NN.json` e `git_NN.diff` de cada execução;
- `logs/<passo>.log`, com hora em cada linha e erros marcados;
- `passos/<passo>/`: livro de retomada, resultados, `erros/*.txt` com o traceback inteiro e `jobs/<derivado>/`;
- `resumo.json`, com as conferências do gabarito e os números.

Para fora da VM:

| O quê | Quando | Leva | Destino |
|---|---|---|---|
| Cópia para o bucket (`DNAT_BUCKET=gs://...` ao iniciar) | depois de **cada passo** e no fim de cada teste | tudo dos testes (com textos), o acompanhamento, o log do serviço e a ficha | bucket do projeto (fora do git) |
| Pacote leve (`make testes-pacote`) | no fim da rodada (automático) | tudo, menos textos gerados e respostas dos jobs (T-211) | `make importar` → `resultados_nuvem/` → git |
| Pacote completo (`make testes-pacote ARGS=--completo`) | no fim da rodada (automático) | também textos, respostas, referências do pai, adaptadores LoRA e log do serviço; só pesos grandes (> 50 MB) ficam de fora, porque se refazem pela receita | notebook e bucket, **fora do git** |
| Acompanhamento (`DSN2027/testes/`) | a cada teste | tabela, gabarito, última conferência, histórico | git |

O disco da VM sobrevive à preempção (Spot com término STOP), mas não a apagar a VM. Por isso use o
bucket. A VM precisa de escopo de escrita no Storage.

## 4. Verificado e não verificado

- **Verificado no notebook (25/11):**
  - Os 11 testes passam no mini, também com 2 processos por passo (16,4 min).
  - Na CPU, o veredito sai idêntico bit a bit ao de antes.
  - Testes do model_gate (318), do executor (5) e do contrato (158).
  - O envio por git bundle, numa VM simulada.
  - A cascata de revogação no T8.
  - A linha de base de Hurtado no T3.
  - Os dois pacotes.
- **Só a VM vai mostrar:**
  - Se o driver e o torch com CUDA sobem.
  - Se alguma operação na GPU recusa o modo determinístico. A saída é `MODEL_GATE_DETERMINISMO=aviso`, que fica registrado.
  - Se 2 vereditos cabem juntos na H100.
  - O tempo real de cada passo, que o ensaio mede.
  - O hashcat.
  - O serviço do systemd.
  - A cópia para o bucket.

## 5. Criar a VM

**Antes da a3, o disco pronto:** prepare uma imagem numa VM barata (`preparar_testes.sh --disco --populacao piloto`), crie a a3 a partir dela e, na a3, rode só o `preparar_testes.sh --so-gpu`. Os comandos estão em `tools/cloud/README.md`, na seção "Disco pronto". A a3 fica ~5–15 min no preparo, em vez de ~1 h.

- **Máquina:** `a3-highgpu-1g`, com Confidential VM (TDX) e GPU confidencial.
- **Zona:** us-central1-a, us-east5-a ou europe-west4-c.
- **Provisionamento:** Spot com término **STOP**.
- **Disco:** 200 GB.
- **Imagem:** Ubuntu 22.04/24.04 com TDX.
- **Escopo:** escrita no Storage.
- **T7:** uma segunda VM, comum, do mesmo tamanho.
