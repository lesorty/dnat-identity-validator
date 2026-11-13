#!/usr/bin/env python3
"""Saída de esquema fixo e tempos limite do agente da CVM de job (T-804, T-802).

Saída (T-804). O script do job não é confiável (T-105) e pode tentar exfiltrar pesos ou gerações
pelo que imprime. Por isso o agente:

- descarta stdout, stderr e logs brutos do script (vão para /dev/null, nem chegam ao disco);
- lê só o arquivo de métricas que o script grava em $DNAT_METRICS_PATH (workspace/metrics.json),
  com teto de bytes, e aceita só os campos numéricos do esquema;
- devolve à CVM1 um JSON de chaves fixas (`agent_output`), com o derivado à parte (T-803).

Esquema padrão das métricas (E14 §10.2: loss, passos, tempo), todos opcionais:
    loss           número finito
    steps          inteiro >= 0
    train_seconds  número finito >= 0
Configurável por DNAT_METRICS_SCHEMA (JSON {"campo": "number"|"integer"}) e o teto do arquivo por
DNAT_METRICS_MAX_BYTES (padrão 1024). Só há números: texto livre seria um canal largo de saída.
Os números são arredondados a 6 algarismos significativos, o que estreita o canal que sobra.

Tempos limite (T-802), em segundos, lidos do ambiente do agente:
    DNAT_JOB_TIMEOUT_SECONDS       limite do script quando a CVM1 não pede outro (padrão 600)
    DNAT_JOB_TIMEOUT_MAX_SECONDS   teto do que a CVM1 pode pedir (padrão 86400, 24 h)
    DNAT_AGENT_MARGIN_SECONDS      folga do agente sobre o script: boot e desligamento da microVM,
                                   coleta do derivado (padrão 120; nunca abaixo de
                                   DNAT_VM_BOOT_MARGIN_SECONDS + SHUTDOWN_GRACE_SECONDS + 10)
O agente corta em job + margem; a CVM1 lê esses valores em /health e espera job + margem + a sua
própria folga, então fica sempre acima do agente. Com os padrões, os números antigos se mantêm:
script 600 s (runner), microVM 660 s (run-vm.sh), executor 720 s, CVM1 750 s.
"""

from __future__ import annotations

import json
import math
import os
import stat
from pathlib import Path

OUTPUT_SCHEMA_ID = "dnat.job-output.v1"
METRICS_FILENAME = "metrics.json"

DEFAULT_METRICS_SCHEMA = {"loss": "number", "steps": "integer", "train_seconds": "number"}
DEFAULT_METRICS_MAX_BYTES = 1024
_MAX_SAFE_INT = 2**53
_SIGNIFICANT_DIGITS = 6

DEFAULT_JOB_TIMEOUT = 600
DEFAULT_JOB_TIMEOUT_MAX = 86400
DEFAULT_AGENT_MARGIN = 120

# Estados e códigos que o agente pode devolver: conjuntos fechados, nunca texto vindo do script.
STATUSES = ("ok", "script_failed", "timeout", "agent_error")
METRICS_ERRORS = ("missing", "not_regular_file", "too_large", "invalid_json", "not_object", "unknown_field", "bad_value")
AGENT_ERRORS = (
    "busy",
    "bundle_not_found",
    "bundle_extract_failed",
    "workspace_missing",
    "microvm_failed",
    "microvm_timeout",
    "agent_timeout",
    "runner_output_invalid",
    "runner_error",
)
OUTPUT_KEYS = (
    "schema",
    "status",
    "returncode",
    "elapsed_seconds",
    "job_timeout_seconds",
    "metrics",
    "metrics_error",
    "error",
    "derivative",
)

# Mensagens dos runners (run-direct.sh, run-vm.sh) -> código fixo. Qualquer outra vira runner_error.
_RUNNER_ERROR_CODES = {
    "Bundle not found": "bundle_not_found",
    "failed to extract bundle": "bundle_extract_failed",
    "workspace missing from execution bundle": "workspace_missing",
    "microVM execution timed out": "microvm_timeout",
    "no persisted result": "microvm_failed",
    "invalid persisted result payload": "microvm_failed",
    "firecracker socket not created": "microvm_failed",
    "firecracker api error": "microvm_failed",
}


# ---------------------------------------------------------------- configuração


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= minimum else default


def load_timeouts() -> dict:
    job_max = _env_int("DNAT_JOB_TIMEOUT_MAX_SECONDS", DEFAULT_JOB_TIMEOUT_MAX)
    job_default = _env_int("DNAT_JOB_TIMEOUT_SECONDS", DEFAULT_JOB_TIMEOUT)
    # A margem do agente cobre o que run-vm.sh espera além do script (boot e desligamento da
    # microVM), com folga; nunca fica abaixo disso, para o executor não cortar antes do runner.
    vm_overhead = _env_int("DNAT_VM_BOOT_MARGIN_SECONDS", 60) + _env_int("SHUTDOWN_GRACE_SECONDS", 20) + 10
    return {
        "job_default_seconds": min(job_default, job_max),
        "job_max_seconds": job_max,
        "agent_margin_seconds": max(_env_int("DNAT_AGENT_MARGIN_SECONDS", DEFAULT_AGENT_MARGIN), vm_overhead),
    }


def effective_job_timeout(requested: str | int | None, timeouts: dict) -> int:
    """Limite do script: o que a CVM1 pediu, se for um inteiro positivo, até o teto do agente."""
    try:
        value = int(str(requested).strip()) if requested is not None else 0
    except ValueError:
        value = 0
    if value <= 0:
        value = timeouts["job_default_seconds"]
    return min(value, timeouts["job_max_seconds"])


def load_metrics_schema() -> dict:
    raw = os.environ.get("DNAT_METRICS_SCHEMA", "").strip()
    if not raw:
        return dict(DEFAULT_METRICS_SCHEMA)
    schema = json.loads(raw)
    if not isinstance(schema, dict) or not schema or any(t not in ("number", "integer") for t in schema.values()):
        raise ValueError('DNAT_METRICS_SCHEMA must be a JSON object {"field": "number"|"integer"}')
    return schema


def metrics_max_bytes() -> int:
    return _env_int("DNAT_METRICS_MAX_BYTES", DEFAULT_METRICS_MAX_BYTES)


# ---------------------------------------------------------------- métricas


def _round(value: float) -> float:
    return float(f"{value:.{_SIGNIFICANT_DIGITS}g}")


def _reject_constant(name: str):
    raise ValueError(f"non-finite number: {name}")


def validate_metrics(obj, schema: dict | None = None) -> tuple[dict | None, str | None]:
    """Confere um objeto de métricas contra o esquema. Devolve (métricas normalizadas, erro)."""
    schema = load_metrics_schema() if schema is None else schema
    if not isinstance(obj, dict):
        return None, "not_object"
    if any(key not in schema for key in obj):
        return None, "unknown_field"
    out = {}
    for key, value in obj.items():
        kind = schema[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, "bad_value"
        if kind == "integer":
            if isinstance(value, float) or abs(value) > _MAX_SAFE_INT:
                return None, "bad_value"
            if key == "steps" and value < 0:
                return None, "bad_value"
            out[key] = int(value)
        else:
            value = float(value)
            if not math.isfinite(value) or abs(value) > 1e300:
                return None, "bad_value"
            if key.endswith("_seconds") and value < 0:
                return None, "bad_value"
            out[key] = _round(value)
    return out, None


def parse_metrics_bytes(data: bytes, schema: dict | None = None, max_bytes: int | None = None) -> tuple[dict | None, str | None]:
    max_bytes = metrics_max_bytes() if max_bytes is None else max_bytes
    if len(data) > max_bytes:
        return None, "too_large"
    try:
        obj = json.loads(data.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError):
        return None, "invalid_json"
    return validate_metrics(obj, schema)


def read_metrics_file(path: Path, schema: dict | None = None, max_bytes: int | None = None) -> tuple[dict | None, str | None]:
    """Lê o arquivo de métricas do script sem seguir link, sem travar em FIFO e com teto de bytes."""
    max_bytes = metrics_max_bytes() if max_bytes is None else max_bytes
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None, "missing"
    except OSError:
        return None, "not_regular_file"
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None, "not_regular_file"
        data = os.read(fd, max_bytes + 1)
    finally:
        os.close(fd)
    return parse_metrics_bytes(data, schema, max_bytes)


# ---------------------------------------------------------------- saída do agente


def agent_output(
    *,
    status: str,
    returncode: int | None = None,
    elapsed_seconds: float | None = None,
    job_timeout_seconds: int | None = None,
    metrics: dict | None = None,
    metrics_error: str | None = None,
    error: str | None = None,
    derivative: dict | None = None,
) -> dict:
    """A única forma de resposta do agente à CVM1. `derivative` vai só à CVM1 (T-803)."""
    assert status in STATUSES, status
    assert metrics_error is None or metrics_error in METRICS_ERRORS, metrics_error
    assert error is None or error in AGENT_ERRORS, error
    return {
        "schema": OUTPUT_SCHEMA_ID,
        "status": status,
        "returncode": returncode,
        "elapsed_seconds": None if elapsed_seconds is None else round(float(elapsed_seconds), 1),
        "job_timeout_seconds": job_timeout_seconds,
        "metrics": metrics,
        "metrics_error": metrics_error,
        "error": error,
        "derivative": derivative,
    }


def _error_code(message) -> str:
    text = str(message or "")
    for prefix, code in _RUNNER_ERROR_CODES.items():
        if text.startswith(prefix):
            return code
    return "runner_error"


def sanitize_runner_output(raw, job_timeout_seconds: int) -> dict:
    """Reduz o JSON do runner ao esquema fixo; stdout, stderr, logs e chaves estranhas somem aqui.

    O runner direto (run-direct.sh) já manda `metrics`/`metrics_error`; o guest da microVM manda o
    texto do arquivo em `metrics_text`. Em ambos o agente revalida antes de devolver.
    """
    if not isinstance(raw, dict):
        return agent_output(status="agent_error", error="runner_output_invalid", job_timeout_seconds=job_timeout_seconds)
    if "error" in raw:
        code = _error_code(raw.get("error"))
        status = "timeout" if code == "microvm_timeout" else "agent_error"
        return agent_output(status=status, error=code, job_timeout_seconds=job_timeout_seconds)

    returncode = raw.get("returncode")
    if isinstance(returncode, bool) or not isinstance(returncode, int):
        return agent_output(status="agent_error", error="runner_output_invalid", job_timeout_seconds=job_timeout_seconds)
    elapsed = raw.get("elapsed_seconds")
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed):
        elapsed = None

    if raw.get("timed_out") is True:
        status = "timeout"
    else:
        status = "ok" if returncode == 0 else "script_failed"

    metrics, metrics_error = None, None
    if isinstance(raw.get("metrics_text"), str):
        metrics, metrics_error = parse_metrics_bytes(raw["metrics_text"].encode("utf-8"))
    elif raw.get("metrics") is not None:
        metrics, metrics_error = validate_metrics(raw["metrics"])
    elif raw.get("metrics_error") in METRICS_ERRORS:
        metrics_error = raw["metrics_error"]
    else:
        metrics_error = "missing"

    derivative = raw.get("derivative") if status == "ok" and isinstance(raw.get("derivative"), dict) else None
    return agent_output(
        status=status,
        returncode=returncode,
        elapsed_seconds=elapsed,
        job_timeout_seconds=job_timeout_seconds,
        metrics=metrics,
        metrics_error=metrics_error,
        derivative=derivative,
    )
