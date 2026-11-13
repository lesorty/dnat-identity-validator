# model_gate

Código do Juiz do DNAT (DSN 2027): avalia um modelo derivado contra o base custodiado
e emite um veredito de três estados. A especificação está na E14 (D6).

O mesmo pacote roda no piloto, nas máquinas da campanha e na CVM de job de uso único.

## Layout

```
model_gate/
├── pyproject.toml          pacote instalável (src layout)
├── src/model_gate/         O JUIZ: entra no artefato com hash fixado (T-808)
│   ├── io/                 carregar modelo (base ou derivado) e gerar com parâmetros fixos
│   ├── battery/            S1: instrumento comportamental (bateria, parte secreta, juiz do portão)
│   ├── signals/            S2 (gap de recusa) e S3 (energia rank-1)
│   ├── formats/            quantizações e formatos liberados (D5)
│   └── verdict/            escada do veredito (combine.py): veto δ, integridade, guardas, segunda linha
├── experiments/            EXPERIMENTO: fora do artefato do Juiz
│   ├── population/         treino e abliteração dos derivados F0–F3
│   ├── campaign/           orquestração da campanha e análise
│   ├── runlog.py, timer.py registro de execuções e medidor por etapa
│   └── fetch_*, bench_*    downloads e medições
├── models/, data/          manifestos com digest (versionados)
├── results/                resultados agregados (versionados)
└── tests/
```

## Regras de importação

1. `experiments/` importa `model_gate`; `model_gate` **nunca** importa `experiments`.
2. Dentro de `model_gate`, `verdict` pode importar `battery`, `signals` e `formats`;
   esses três podem importar `io`; `io` não importa nenhum deles.
3. Importações sempre absolutas (`from model_gate.io import ...`). O subpacote
   `model_gate.io` não conflita com o `io` da biblioteca padrão.

O hash do Juiz (T-808) é calculado sobre `src/model_gate/` inteiro. Por isso, qualquer
código que não seja o Juiz vai para `experiments/`.

## Dados fora do git (T-211)

**Regra: no git só vão IDs, hashes e métricas agregadas.** Gerações, pesos, prompts
nocivos e arquivos brutos de datasets ficam em `$MODEL_GATE_DATA`.

- Registros de execução e gerações vão para `$MODEL_GATE_DATA/runs/`. Gerações nocivas
  nunca entram no git.
- O `.gitignore` da raiz bloqueia `*.safetensors`, `*.gguf` e `*.bin`.
- Pesos de modelo ficam fora do git; só os manifestos com digest são versionados (T-203).

Pasta de dados: `$MODEL_GATE_DATA` (padrão `~/model_gate_data`), fora do repositório.

## Ambiente (T-202)

Tudo em CPU (D2), com versões fixadas no `uv.lock` e Python 3.12 (`.python-version`).
O torch vem do índice CPU do PyTorch (sem CUDA). Requisito: [uv](https://docs.astral.sh/uv/).

```bash
./setup.sh                 # cria .venv do zero a partir do lock (uv sync --frozen)
uv run pytest              # fumaça: importa tudo e roda um forward de um Qwen2 minúsculo
```

| Pacote | Versão |
|---|---|
| Python | 3.12.14 |
| torch | 2.15.0+cpu |
| transformers | 5.22.1 |
| peft | 0.21.2 |
| accelerate | 1.15.0 |
| safetensors | 0.8.0 |
| datasets | 5.1.0 |
| huggingface-hub | 2.4.0 |

Instalação limpa medida em 2026-11-05 num container `ubuntu:24.04` com `--cpus=4`
(cota de CPU, não CPUs dedicadas): **67 s** do `setup.sh`, testes verdes. A repetição
numa VM real de 4 vCPU fica para a T-210.

Para mudar uma dependência: editar `pyproject.toml`, rodar `uv lock` e commitar os dois.

## Modelo base (T-203)

```bash
uv run python -m experiments.fetch_base           # baixa e grava models/base.manifest.json
uv run python -m experiments.fetch_base --check   # outra máquina: baixa e confere o digest
```

`Qwen/Qwen2.5-0.5B-Instruct` no commit fixo do HF. O digest cobre pesos, configuração e
tokenizador (regra em `model_gate.io.digest`); o hash dos pesos é conferido contra o
SHA-256 publicado pelo HF. O download simula o depósito do dono do base, por isso o
script está em `experiments/`; o cálculo do digest está no Juiz (`model_gate.io.digest`).

## Carga e geração (T-205)

- `model_gate.io.load.load_model(path, digest)`: carrega um modelo cheio (safetensors) ou um
  adaptador LoRA (`adapter_config.json`), que é mesclado no base custodiado. O digest é
  conferido antes da carga (`DigestMismatch` se divergir); no LoRA, o do base também.
  O digest de um diretório cobre todos os arquivos, menos ocultos, `README*` e `LICENSE*`.
- `model_gate.io.generate.generate(model, tok, prompts, GenConfig(...))`: decodificação
  gulosa, chat template do tokenizer, float32, 4 threads, seed fixa e algoritmos
  determinísticos. `GenConfig.record()` devolve os parâmetros para o registro (R5).
- Lote canônico do veredito: 1. Lotes maiores usam padding à esquerda e servem para medir
  vazão (T-208).

Verificação no base real:

```bash
uv run python -m experiments.check_determinism
```

Resultado em 2026-11-05 (12 CPUs, `threads=4`, 128 tokens, 10 prompts seguros do XSTest):
duas execuções em processos separados deram o mesmo hash dos textos (`a928f231…`), as duas
gerações de cada execução saíram iguais, e o lote 4 deu o mesmo texto que o lote 1.
Vazão de 15,6–17,7 tok/s com lote 1 (medida grosseira; a medição formal é a T-208).

## Registro de execuções (T-206)

`experiments.runlog.RunLog` grava um JSONL por execução em `$MODEL_GATE_DATA/runs/<run_id>.jsonl`,
só acrescentando. Esquema de cada linha:

| Campo | Conteúdo |
|---|---|
| `run_id`, `ts` | identificador da execução e data/hora |
| `model_digest` | digest do modelo avaliado |
| `git_commit`, `dirty` | commit do código e se havia mudança não commitada |
| `seed`, `gen` | seed e parâmetros de geração (`GenConfig.record()`) |
| `instrument`, `metric`, `value` | o que foi medido e o valor |
| `extra` | campos livres (categoria, repetição etc.) |

Repositório sujo grava `dirty=true`; `RunLog(..., require_clean=True)` recusa, para a campanha.
Só métricas: texto gerado nunca vai para o registro.

## Medidor por etapa (T-207)

```python
with stage("gerar", log) as s:
    ...
```

Mede tempo de parede, tempo de CPU e pico de RSS da etapa (no Linux, o pico é zerado no
início de cada etapa) e grava no registro. `timer.report(read(log.path))` gera a tabela
etapa × minutos × GiB.

## Vazão e custo de S1 (T-208)

```bash
taskset -c 0-3 uv run python -m experiments.bench_throughput   # results/T-208_vazao.json
uv run python -m experiments.estimate_s1 [--stage2-frac 0.3]   # extrapola o custo de S1
```

Lote 1: ~20 tok/s; lote 8: 50–57 tok/s. No pior caso (toda resposta até o teto), a geração
de S1 não cabe nos 80 min. Nota completa: [results/T-208_vazao.md](results/T-208_vazao.md).

## Datasets (T-204)

```bash
uv run python -m experiments.fetch_datasets           # baixa e grava data/datasets.manifest.json
uv run python -m experiments.fetch_datasets --check
```

| Conjunto | Fonte (commit fixo) | Licença | Itens |
|---|---|---|---|
| StrongREJECT | `alexandrasouly/strongreject` | MIT | 313 (6 categorias); versão pequena com 60 |
| XSTest | `paul-rottger/xstest` | CC BY 4.0 | 450 (250 seguros, 200 contrastes inseguros; 18 tipos) |

As duas licenças permitem redistribuir. Mesmo assim, os arquivos brutos ficam fora do git
(T-211); o manifesto guarda fonte, commit, licença, hashes e contagens. Parte do
StrongREJECT vem de outros conjuntos (coluna `source`), cuja licença não foi conferida
item a item.
