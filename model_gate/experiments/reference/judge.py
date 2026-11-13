"""Juiz da verdade de referência (T-1002): gpt-oss-20b com a rubrica do StrongREJECT e o XSTest.

É o procedimento independente que rotula a população (R12, T-1003, T-1004): outro modelo, de outra
família e mais forte que o avaliador do portão. Fica em experiments/: não é o Juiz e não entra no
hash dele (T-808). Roda na nuvem (regra do projeto); aqui ficam a configuração fixada
(judge.yaml), o manifesto com os hashes (models/reference_judge.manifest.json) e o código.

Diferenças em relação aos avaliadores do portão (battery/judge.py), todas por causa do formato
harmony do gpt-oss:
- o prompt é renderizado pelo chat template com o esforço de raciocínio fixado, e a linha
  "Current date" que o template preenche com a data do dia é trocada pela data fixada no YAML;
- a saída tem um canal de análise e um final; só o final é lido (parse_rubric e parse_xstest do
  portão), e o de análise é descartado.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

from model_gate.battery.judge import XSTEST_SYSTEM, Score, XSTestLabel, parse_rubric, parse_xstest

CONFIG_PATH = Path(__file__).with_name("judge.yaml")
_DATE = re.compile(r"Current date: \d{4}-\d{2}-\d{2}")
_FINAL = re.compile(r"<\|channel\|>final<\|message\|>(.*?)(?:<\|return\|>|<\|end\|>|<\|call\|>|$)", re.S)


@dataclass(frozen=True)
class ReferenceConfig:
    repo_id: str
    revision: str
    manifest: str
    max_new_tokens: int
    reasoning_effort: str
    pinned_date: str
    threads: int

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "ReferenceConfig":
        c = yaml.safe_load(Path(path).read_text())
        m, d = c["modelo"], c["decodificacao"]
        if d.get("do_sample") is not False:
            raise ValueError("o juiz de referência decodifica guloso (do_sample: false)")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d["data_fixada"])):
            raise ValueError("data_fixada tem de ser AAAA-MM-DD")
        return cls(m["repo_id"], m["revisao"], m["manifesto"], int(d["max_new_tokens"]),
                   str(d["esforco_de_raciocinio"]), str(d["data_fixada"]), int(d["threads"]))


def render(tokenizer, messages: list[dict], cfg: ReferenceConfig) -> str:
    """Prompt harmony com o esforço fixado e a data trocada pela fixada (o resto do template intacto)."""
    text = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False,
                                         reasoning_effort=cfg.reasoning_effort)
    if len(_DATE.findall(text)) != 1:
        raise ValueError("o template mudou: esperava exatamente uma linha 'Current date'")
    return _DATE.sub(f"Current date: {cfg.pinned_date}", text)


def final_channel(raw: str) -> str | None:
    """Texto do canal final de uma saída harmony decodificada com os tokens especiais; None se não há."""
    m = _FINAL.search(raw)
    return m.group(1).strip() if m else None


class ReferenceJudge:
    """Pontua dano (rubrica do StrongREJECT) e classifica o XSTest com o gpt-oss, guloso."""

    def __init__(self, model, tokenizer, rubric_template: str, xstest_template: str, cfg: ReferenceConfig):
        self.model, self.tok, self.cfg = model.eval(), tokenizer, cfg
        self.rubric_template, self.xstest_template = rubric_template, xstest_template

    def _generate(self, messages: list[dict]) -> tuple[str | None, float, int, int]:
        import torch
        torch.set_num_threads(self.cfg.threads)
        prompt = render(self.tok, messages, self.cfg)
        ids = self.tok(prompt, return_tensors="pt", add_special_tokens=False)
        t0 = time.perf_counter()
        with torch.inference_mode():
            out = self.model.generate(**ids, do_sample=False, max_new_tokens=self.cfg.max_new_tokens,
                                      temperature=None, top_p=None, top_k=None)
        dt = time.perf_counter() - t0
        new = out[0, ids["input_ids"].shape[1]:]
        raw = self.tok.decode(new, skip_special_tokens=False)
        return final_channel(raw), dt, int(ids["input_ids"].shape[1]), int(new.numel())

    def score(self, prompt: str, response: str) -> Score:
        """Sem canal final (o raciocínio estourou max_new_tokens): falha do avaliador, nota NaN."""
        msgs = [{"role": "user", "content": self.rubric_template.format(prompt=prompt, response=response)}]
        text, dt, n_in, n_new = self._generate(msgs)
        harm, refused = parse_rubric(text) if text is not None else (float("nan"), None)
        return Score(harm, refused, text or "", dt, n_in, n_new)

    def classify(self, prompt: str, response: str) -> XSTestLabel:
        msgs = [{"role": "system", "content": XSTEST_SYSTEM},
                {"role": "user", "content": self.xstest_template.format(prompt=prompt, response=response)}]
        text, dt, n_in, n_new = self._generate(msgs)
        return XSTestLabel(parse_xstest(text) if text is not None else None, text or "", dt, n_in, n_new)
