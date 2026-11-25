#!/usr/bin/env python3
"""Testes do executor: retomada, registro de falha, tempo esgotado, pré-voo e acompanhamento.

    python3 -I tools/testes/test_executor.py      (ou make testes-executor)

Roda com MODEL_GATE_DATA e a pasta do acompanhamento numa pasta temporária: não toca nos dados reais.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


class ExecutorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODEL_GATE_DATA"] = self.tmp.name
        import executor
        self.ex = importlib.reload(executor)
        self.ex.ACOMP_DIR = Path(self.tmp.name) / "acomp"
        self.ex.HEARTBEAT_S = 1

    def tearDown(self):
        self.tmp.cleanup()

    def fazer(self, passos, **kw):
        ex = self.ex
        return ex.Teste(id="T99", nome="falso", perguntas="P0", objetivo="teste do executor", gabarito=("nada",),
                        passos=passos, **kw)

    def run_t(self, t, *args):
        r = self.ex.Runner(t, "mini", unfrozen=True, novo="--novo" in args, refazer=set(), echo=False, campanha="x")
        return r, r.run()

    def test_retoma_e_registra(self):
        ex = self.ex
        flag = Path(self.tmp.name) / "deixa_passar"
        passos = [ex.Passo("a", "escreve no PASSO_DIR", 'echo oi && echo "{\\"v\\": 1}" > $PASSO_DIR/r.json'),
                  ex.Passo("b", "falha até existir a bandeira", f'echo "erro de verdade" >&2; test -f {flag}')]
        t = self.fazer(passos, conferir=lambda ctx: [ex.check("v", (ctx.resultado("a", "r.json") or {}).get("v") == 1)])
        r, rc = self.run_t(t)
        self.assertEqual(rc, 1)
        st = json.loads((r.dir / "estado.json").read_text())
        self.assertEqual(st["passos"]["a"]["estado"], "ok")
        self.assertEqual(st["passos"]["b"]["estado"], "falhou")
        self.assertTrue(any("erro de verdade" in x for x in st["passos"]["b"]["ultimas_linhas"]))
        log = (r.dir / "logs" / "b.log").read_text()
        self.assertIn("ERR erro de verdade", log)
        self.assertEqual(json.loads((r.dir / "resumo.json").read_text())["estado"], "falhou")
        flag.touch()
        r2, rc2 = self.run_t(t)
        self.assertEqual(rc2, 0)
        st = json.loads((r2.dir / "estado.json").read_text())
        self.assertEqual(st["passos"]["a"]["tentativas"], 1)   # não refez o que deu certo
        self.assertEqual(st["passos"]["b"]["tentativas"], 2)
        self.assertEqual(len(st["execucoes"]), 2)
        ev = [json.loads(x)["evento"] for x in (r2.dir / "eventos.jsonl").read_text().splitlines()]
        self.assertEqual(ev.count("inicio"), 3)
        acomp = json.loads((ex.ACOMP_DIR / "acompanhamento.json").read_text())
        self.assertEqual(acomp["T99"]["ultima"]["mini"]["estado"], "ok")
        self.assertIn("T99", (ex.ACOMP_DIR / "ACOMPANHAMENTO.md").read_text())

    def test_tempo_esgotado_e_conferencia_divergente(self):
        ex = self.ex
        t = self.fazer([ex.Passo("lento", "dorme", "sleep 30", timeout_min=0.03)])
        r, rc = self.run_t(t)
        st = json.loads((r.dir / "estado.json").read_text())
        self.assertEqual(st["passos"]["lento"]["codigo"], 124)
        t2 = self.fazer([ex.Passo("ok", "passa", "true")], conferir=lambda ctx: [ex.check("algo", False, 1, 2)])
        r2, rc2 = self.ex.Runner(t2, "mini", unfrozen=True, novo=True, refazer=set(), echo=False, campanha="y"), None
        rc2 = r2.run()
        self.assertEqual(rc2, 4)
        self.assertEqual(json.loads((r2.dir / "resumo.json").read_text())["estado"], "divergiu")

    def test_passo_sem_saida_e_morto(self):
        ex = self.ex
        os.environ["TESTES_SILENCIO_MIN"] = "0.05"   # 3 s sem escrever nada
        try:
            t = self.fazer([ex.Passo("mudo", "escreve uma vez e trava", "echo comecei; sleep 60")])
            r, rc = self.run_t(t)
        finally:
            del os.environ["TESTES_SILENCIO_MIN"]
        st = json.loads((r.dir / "estado.json").read_text())
        self.assertEqual(st["passos"]["mudo"]["codigo"], 124)
        self.assertLess(st["passos"]["mudo"]["segundos"], 30)
        self.assertIn("SEM SAÍDA", (r.dir / "logs" / "mudo.log").read_text())

    def test_copia_de_seguranca_depois_de_cada_passo(self):
        ex = self.ex
        dest = Path(self.tmp.name) / "bucket"
        os.environ["TESTES_BACKUP"] = f'mkdir -p {dest} && cp -r "$TESTE_DIR"/. {dest}/'
        try:
            t = self.fazer([ex.Passo("a", "um", "echo um"), ex.Passo("b", "dois", "echo dois")])
            r, rc = self.run_t(t)
        finally:
            del os.environ["TESTES_BACKUP"]
        self.assertEqual(rc, 0)
        self.assertTrue((dest / "resumo.json").exists())          # a última cópia leva o resumo
        self.assertIn("fim do T99", (dest / "logs" / "backup.log").read_text())
        ev = [json.loads(x)["evento"] for x in (r.dir / "eventos.jsonl").read_text().splitlines()]
        self.assertGreaterEqual(ev.count("backup"), 2)

    def test_preflight(self):
        ex = self.ex
        t = self.fazer([ex.Passo("p", "pendente", None, pendente="falta X"),
                        ex.Passo("q", "precisa de arquivo", "true", requer=(ex.exists("/nao/existe"),))], depende=("T1",))
        r = ex.Runner(t, "mini", unfrozen=True, novo=False, refazer=set(), echo=False, campanha="z")
        probs = r.preflight()
        self.assertTrue(any("depende de T1" in p for p in probs))
        self.assertTrue(any("falta X" in p for p in probs))
        self.assertTrue(any("/nao/existe" in p for p in probs))
        self.assertEqual(r.run(), 2)


if __name__ == "__main__":
    unittest.main()
