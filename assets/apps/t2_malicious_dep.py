#!/usr/bin/env python3
"""T2 - Teste de ataque de supply chain (build plane / CVM2).

Esta aplicacao declara uma dependencia maliciosa (malicious-pkg). O objetivo e
exercitar o plano de build: durante a resolucao/instalacao da dependencia, o
codigo do pacote roda dentro da microVM de build efemera da CVM2. Combinada com
o pacote em assets/malicious_wheel/, ela cobre dois vetores:

  - Build-time: setup.py executa quando o pip constroi o sdist no build microVM.
  - Import-time: malicious_pkg/__init__.py executa quando esta aplicacao o
    importa durante a execucao na CVM3.

Para registrar com a dependencia maliciosa, use o campo de dependencias:
    dependencies = "malicious-pkg"
e garanta que o pacote esteja disponivel no cache de wheels da CVM2
(ver assets/malicious_wheel/seed_cache.sh).

O ponto cientifico: o que quer que o payload alcance, ele esta CONTIDO no plano
de build (CVM2, que persiste apenas wheels) e nao no control plane (CVM1, que
guarda IPFS, chaves e estado do marketplace). No baseline centralizado, o mesmo
payload cairia no namespace que tambem ve esses ativos sensiveis.

Contrato: python3 code/application.py --dataset data/dataset.csv
"""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="DNAT T2 supply-chain dependency probe")
    parser.add_argument("--dataset", default="data/dataset.csv")
    parser.add_argument("--output", default="")
    args, _unknown = parser.parse_known_args()

    report = {"test": "T2-supply-chain", "import_ran": False, "payload": None}

    # O import dispara o payload de import-time do pacote malicioso, se ele foi
    # de fato empacotado no artefato da aplicacao pela CVM2.
    try:
        import malicious_pkg  # noqa: F401

        report["import_ran"] = True
        report["payload"] = getattr(malicious_pkg, "LAST_PROBE", None)
        print("[T2] malicious_pkg imported -> import-time payload executed in execution VM")
    except ModuleNotFoundError:
        print("[T2] malicious_pkg NOT installed (dependency not resolved/bundled)")
    except Exception as exc:  # noqa: BLE001
        report["payload_error"] = f"{type(exc).__name__}: {exc}"
        print(f"[T2] malicious_pkg import raised: {exc}")

    print("[T2] JSON " + json.dumps(report))

    if args.output:
        try:
            Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
