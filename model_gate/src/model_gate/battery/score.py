"""Pontuação por item do S1 (T-310): dano nas respostas a nocivos e classe do XSTest nas respostas a seguros.

Entrada: as respostas de s1.respond (pai no depósito, derivado no veredito), por condição.
Saída: uma linha por item, configuração (formato × condição) e modelo (digest). É a tabela de
notas por item que a T-311 agrega e que vai para o registro (`record`).

- **Dano**: nota do avaliador do portão (judge.RubricJudge ou judge.GuardJudge, T-309) em [0, 1];
  NaN quando a saída do avaliador não segue o formato. A binarização (nota ≥ τ) e a agregação
  por categoria ficam na T-311, com τ do prereg.yaml (T-606).
- **Recusa excessiva**: classe do XSTest (cumpre, recusa_total, recusa_parcial) dada por
  judge.XSTestJudge; None quando a saída está fora do formato. Serve aos seguros e, se um dia
  entrarem, aos contrastes (a classe é a mesma; o que muda é a leitura na T-311).
- Junto vai a marca do detector de recusa (refusal.is_refusal, T-307), para comparar com a do
  avaliador.

Falha do avaliador (NaN ou None) nunca vira nota: fica na linha, e o veredito trata como falha
do instrumento (inconclusivo, T-107).

A linha leva a saída crua do avaliador em `judge_raw`, porque a rubrica pode citar a resposta e
o chamador precisa dela para conferir saídas fora do formato. Ela fica fora do git (T-211):
`record` grava no registro tudo menos `judge_raw`.
"""

from __future__ import annotations

import math

from model_gate.battery.judge import XSTEST_CLASSES

HARM = "harm"
XSTEST = "xstest"
KINDS = (HARM, XSTEST)
CLASSES = tuple(XSTEST_CLASSES.values())

# Blocos de s1.parent_reference (pai, no depósito) e de s1.derivative_responses (derivado, no
# veredito). No pai, "anchors" é o mapa categoria -> IDs, não respostas, e não é pontuado.
PARENT_BLOCKS = {"harmful": HARM, "safe": XSTEST}
DERIVATIVE_BLOCKS = {"anchors": HARM, "safe": XSTEST}
# Com os codificados (T-305), quando o plano do veredito os tem.
DERIVATIVE_BLOCKS_ENCODED = DERIVATIVE_BLOCKS | {"encoded": HARM}

TEXT_FIELDS = ("judge_raw",)  # nunca vão para o registro


def _check_key(model_digest: str, fmt: str) -> None:
    if not model_digest or not fmt:
        raise ValueError(f"model_digest e formato são obrigatórios (veio {model_digest!r}, {fmt!r})")


def score_block(kind: str, judge, judge_id: str, prompts: dict[int, str], responses: list[dict], *,
                model_digest: str, fmt: str, condition: str, block: str) -> list[dict]:
    """Uma linha por resposta do bloco, na ordem dada.

    judge: com .score(prompt, response) -> judge.Score para HARM; com .classify(prompt, response)
    -> judge.XSTestLabel para XSTEST. prompts: ID -> pedido (o mesmo texto que o modelo viu).
    """
    if kind not in KINDS:
        raise ValueError(f"tipo de pontuação desconhecido: {kind!r} (esperava um de {KINDS})")
    _check_key(model_digest, fmt)
    ids = [r["id"] for r in responses]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{condition}/{block}: ID repetido no bloco")
    rows = []
    for r in responses:
        if r["condition"] != condition:
            raise ValueError(f"{condition}/{block}: resposta {r['id']} é da condição {r['condition']!r}")
        row = {"model_digest": model_digest, "format": fmt, "condition": condition, "block": block,
               "id": r["id"], "kind": kind, "judge_id": judge_id, "n_tokens": r["n_tokens"],
               "detector_refused": r["refused"]}
        prompt = prompts[r["id"]]
        if kind == HARM:
            s = judge.score(prompt, r["text"])
            if not (math.isnan(s.harm) or 0.0 <= s.harm <= 1.0):
                raise ValueError(f"{condition}/{block}/{r['id']}: nota {s.harm} fora de [0, 1]")
            row |= {"harm": s.harm, "judge_refused": s.refused}
        else:
            s = judge.classify(prompt, r["text"])
            if s.cls is not None and s.cls not in CLASSES:
                raise ValueError(f"{condition}/{block}/{r['id']}: classe {s.cls!r} fora de {CLASSES}")
            row |= {"xstest_class": s.cls}
        row |= {"judge_seconds": s.seconds, "judge_prompt_tokens": s.n_prompt_tokens,
                "judge_new_tokens": s.n_new_tokens, "judge_raw": s.raw}
        rows.append(row)
    return rows


def score_run(run: dict, blocks: dict[str, str], prompts: dict[str, dict[int, str]],
              judges: dict[str, tuple[str, object]], *, model_digest: str, fmt: str) -> list[dict]:
    """Pontua uma execução do S1 num formato: todas as condições, os blocos pedidos.

    run: condição -> bloco -> respostas (saída de s1.parent_reference ou s1.derivative_responses).
    blocks: bloco -> HARM ou XSTEST (PARENT_BLOCKS ou DERIVATIVE_BLOCKS).
    prompts: bloco -> (ID -> pedido).
    judges: HARM e/ou XSTEST -> (identificação do avaliador, avaliador). A identificação entra
    em cada linha (ex.: repositório e revisão do modelo, precisão).
    Bloco pedido que falta na execução, ou sem pedidos, levanta KeyError.
    """
    rows = []
    for condition in sorted(run):
        for block in sorted(blocks):
            kind = blocks[block]
            judge_id, judge = judges[kind]
            rows += score_block(kind, judge, judge_id, prompts[block], run[condition][block],
                                model_digest=model_digest, fmt=fmt, condition=condition, block=block)
    return rows


def record(log, rows: list[dict], instrument: str = "s1") -> None:
    """Grava a tabela no registro, uma linha por item: métrica "harm" ou "xstest_class".

    log: qualquer objeto com .log(instrument, metric, value, **extra), como experiments.runlog.RunLog
    (o Juiz não importa experiments). Os campos de texto (TEXT_FIELDS) não vão.
    """
    for row in rows:
        metric = "harm" if row["kind"] == HARM else "xstest_class"
        value = row["harm"] if row["kind"] == HARM else row["xstest_class"]
        extra = {k: v for k, v in row.items() if k not in TEXT_FIELDS and k not in ("harm", "xstest_class")}
        log.log(instrument, metric, value, **extra)
