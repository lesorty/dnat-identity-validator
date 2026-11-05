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
│   └── verdict/            z-soma, limiar, inconclusivo, δ
├── experiments/            EXPERIMENTO: fora do artefato do Juiz
│   ├── population/         treino e abliteração dos derivados F0–F3
│   ├── campaign/           orquestração da campanha e análise
│   └── runs/               registros de execução (ignorados pelo git)
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

## Dados fora do git

- `experiments/runs/` é ignorado. Gerações nocivas nunca entram no git (T-211).
- Pesos de modelo ficam fora do git; só os manifestos com digest são versionados (T-203).

## Instalação

Ambiente e dependências: T-202. Para desenvolver:

```bash
pip install -e model_gate
```
