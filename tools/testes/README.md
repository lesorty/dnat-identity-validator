# Testes T1 a T11

Um roteiro por teste da campanha (a página "Campanha de testes do Juiz"), todos sobre o mesmo
executor (`executor.py`). Cada roteiro tem dois perfis:

- **mini**: versão pequena para conferir no notebook que o roteiro funciona. Usa o detector de
  recusa no lugar do avaliador e do juiz de referência, prereg de fumaça e derivados minúsculos.
  Cada teste leva menos de 5 min e os 11 juntos, uns 30. **Não é dado do artigo.**
- **ensaio**: os tamanhos do mini, mas na VM com GPU e com os modelos de verdade (Qwen3Guard no portão,
  juiz de referência no rótulo), em paralelo. É a primeira rodada na VM (~30 min): mostra que tudo roda
  na GPU e quanto cada passo leva. **Não é dado do artigo.**
- **nuvem**: a campanha de verdade, na VM confidencial com GPU. Exige commit congelado
  (`--sem-congelamento` só para ensaio).

Na VM, o caminho é `tools/cloud/README.md` (enviar, preparar, `campanha_gpu.sh`).

**Variáveis que os perfis passam aos passos** (`perfis.py`; o ambiente de quem chama vence):
`MODEL_GATE_DISPOSITIVO=cuda` (model_gate na GPU), `MG_PARALELO=N` (N derivados ao mesmo tempo nos passos
longos, cada fatia com o seu livro), `UV_NO_SYNC=1` (o uv não volta o torch de CUDA para o de CPU).
O executor mata o passo que fica `silencio_min` sem escrever nada (`TESTES_SILENCIO_MIN` muda).

## Uso

```bash
make testes-verificar PERFIL=nuvem FASE=1   # pré-voo: o que falta, sem rodar nada
make testes PERFIL=mini                     # os 11 na ordem, retomando o que já terminou
make teste T=3 PERFIL=mini                  # um teste
make testes-status PERFIL=nuvem             # passos e conferências de cada teste
make testes-pacote PERFIL=nuvem             # .tar.gz para trazer de volta (sem textos gerados)
make testes-executor                        # testes do próprio executor
```

Direto: `python3 -I tools/testes/t03_deteccao.py --perfil mini [--listar | --verificar | --refazer PASSO | --novo]`.

## Na nuvem: duas fases

O prereg só se fixa depois da calibração, então a campanha tem duas fases:

1. **Fase 1** (`make testes PERFIL=nuvem FASE=1`): T1, T9, T10, T11 e T2, com o prereg provisório
   (`model_gate/experiments/testes/prereg_provisorio.yaml`, o mesmo desenho do prereg.yaml).
2. **Entre as fases, uma pessoa decide.** Revisa
   `$MODEL_GATE_DATA/testes/nuvem/tst/T2/passos/calibrar/prereg_proposto.yaml`, copia os limiares
   para `model_gate/prereg.yaml` (T-606), faz o commit e roda `make congelar`.
3. **Fase 2** (`make testes PERFIL=nuvem FASE=2`): T3, T5, T6, T7, T8, o T11 de novo (agora com o
   `e` do T6) e o T4. Usa o Juiz congelado.

As duas fases gravam na mesma pasta, `$MODEL_GATE_DATA/testes/nuvem/tst/`. A fase 2 aproveita tudo
o que a fase 1 fez, e cada passo registra o commit em que rodou.

## O que fica guardado (pasta de cada teste)

```
$MODEL_GATE_DATA/testes/<perfil>/<campanha>/T3/
  estado.json        estado de cada passo: comando, tentativas, código, tempo, pico de memória,
                     últimas 60 linhas quando falha, último sinal de vida (a cada 30 s)
  eventos.jsonl      início, fim, sinais de vida, interrupções e erros (só acrescenta, com fsync)
  ambiente_NN.json   cada execução: commit, máquina, CPU/flags, RAM, GPU, disco, versões, lockfiles
  git_NN.diff        o diff, se o repositório estava sujo
  logs/<passo>.log   saída inteira com hora em cada linha (stderr marcado ERR)
  passos/<passo>/    o que o passo grava: livro.jsonl (retomada item a item), resultados, erros/*.txt
                     com o traceback inteiro, jobs/<derivado>/ com o manifesto e o veredito
  resumo.json        estado final, conferências do gabarito e números
```

Os textos gerados (`*_texts.jsonl`, `responses.jsonl`) ficam só na VM. O pacote não os leva (T-211).

**Retomada:** rodar de novo pula os passos feitos e refaz o que caiu. Dentro dos passos longos
(população, vereditos, rótulo), cada derivado, e no rótulo cada pedido, é um item do livro. Uma
queda perde no máximo o item em andamento.

## Acompanhamento e gabarito

Cada execução atualiza `DSN2027/testes/`:

- `acompanhamento.json`: a última execução por teste e perfil.
- `historico.jsonl`: todas as execuções.
- `ACOMPANHAMENTO.md`: a tabela, mais o gabarito de cada teste, ou seja, o que se espera ver, e a
  última conferência de cada um.

Isso serve para comparar a nuvem com o mini e uma execução com a seguinte.

## Arquivos

| Arquivo | O que é |
|---|---|
| `executor.py` | Passos, retomada, logs, pré-voo, conferências e acompanhamento (só biblioteca padrão) |
| `perfis.py` | O que muda entre mini e nuvem: prereg, bateria, avaliador, tamanho do rótulo |
| `t01_…` a `t11_…` | Um roteiro por teste: passos, gabarito, conferências e pendências da nuvem |
| `todos.py` | Ordem, fases, pré-voo de todos, status e pacote |
| `test_executor.py` | Testes do executor |
| `model_gate/experiments/testes/` | Passos do model_gate: `veredito`, `populacao`, `rotulo`, `calibrar`, `analise`, `atacante`, `juiz_referencia`; `planos.yaml` e os prereg mini e provisório |
