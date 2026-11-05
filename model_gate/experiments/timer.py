"""Medidor de tempo e memória por etapa (T-207).

    with stage("gerar", log) as s:
        ...
    s.result  # {"wall_s", "cpu_s", "peak_rss_gib"}

Pico de RSS por etapa: no Linux, zera o pico do processo (/proc/self/clear_refs) no
início e lê VmHWM no fim; sem isso, cai no pico do processo inteiro (ru_maxrss).
Cada medição vai para o registro da T-206 com o nome da etapa.
"""

from __future__ import annotations

import resource
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from experiments.runlog import RunLog

_STATUS = Path("/proc/self/status")
_CLEAR = Path("/proc/self/clear_refs")


def _reset_peak() -> bool:
    try:
        _CLEAR.write_text("5")
        return True
    except OSError:
        return False


def _peak_rss_gib(per_stage: bool) -> float:
    if per_stage:
        for line in _STATUS.read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) / 2**20
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20  # KiB no Linux


@dataclass
class Stage:
    name: str
    result: dict = field(default_factory=dict)


@contextmanager
def stage(name: str, log: RunLog | None = None, **extra):
    s = Stage(name)
    per_stage = _reset_peak()
    w0, c0 = time.perf_counter(), time.process_time()
    try:
        yield s
    finally:
        s.result = {
            "wall_s": round(time.perf_counter() - w0, 3),
            "cpu_s": round(time.process_time() - c0, 3),
            "peak_rss_gib": round(_peak_rss_gib(per_stage), 3),
            "peak_scope": "stage" if per_stage else "process",
        }
        if log is not None:
            log.log("timer", name, s.result, **extra)


def report(rows: list[dict]) -> str:
    """Tabela etapa × minutos × GiB a partir das linhas do registro."""
    lines = ["| Etapa | Min (parede) | Min (CPU) | Pico GiB |", "|---|---|---|---|"]
    total = 0.0
    for r in rows:
        if r["instrument"] != "timer":
            continue
        v = r["value"]
        total += v["wall_s"]
        lines.append(f"| {r['metric']} | {v['wall_s'] / 60:.2f} | {v['cpu_s'] / 60:.2f} | {v['peak_rss_gib']:.2f} |")
    lines.append(f"| **total** | **{total / 60:.2f}** | | |")
    return "\n".join(lines)
