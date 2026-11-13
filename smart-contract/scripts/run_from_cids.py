#!/usr/bin/env python3
import argparse
import base64
import binascii
import datetime as dt
import hashlib
import io
import json
import math
import os
import pathlib
import shutil
import socket
import tarfile
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def normalize_cid(cid_or_uri: str) -> str:
    value = (cid_or_uri or "").strip()
    if value.startswith("ipfs://"):
        return value[len("ipfs://") :]
    return value


def normalize_executor_url(raw_url: str) -> str:
    value = (raw_url or "").strip().rstrip("/")
    if not value:
        raise ValueError("Executor URL is required")
    if value.endswith("/execute"):
        return value
    return f"{value}/execute"


# Prefixo do envelope AES-256-GCM escrito pelo plano de controle (api-server.js).
ENCRYPTED_ENVELOPE_MAGIC = b"DNATENC2"

# Onde o script do job grava o derivado (T-803); o agente da CVM de job o devolve so a CVM1.
JOB_DERIVATIVE_DIR = "/tmp/exec/workspace/derivative"

# --- T-804: saida de esquema fixo -------------------------------------------------------------
# Espelha vm_runtime/job_output.py (a CVM1 nao tem vm_runtime/ na imagem). O agente ja descarta
# stdout e stderr; aqui a CVM1 confere de novo e recusa o que nao for exatamente este esquema.
JOB_OUTPUT_SCHEMA_ID = "dnat.job-output.v1"
JOB_OUTPUT_KEYS = frozenset({
    "schema", "status", "returncode", "elapsed_seconds", "job_timeout_seconds",
    "metrics", "metrics_error", "error",
})
JOB_STATUSES = ("ok", "script_failed", "timeout", "agent_error")
METRICS_ERRORS = ("missing", "not_regular_file", "too_large", "invalid_json", "not_object", "unknown_field", "bad_value")
AGENT_ERRORS = (
    "busy", "bundle_not_found", "bundle_extract_failed", "workspace_missing", "microvm_failed",
    "microvm_timeout", "agent_timeout", "runner_output_invalid", "runner_error",
)
DEFAULT_METRICS_SCHEMA = {"loss": "number", "steps": "integer", "train_seconds": "number"}
# Teto da resposta do agente sem o derivado, em bytes do JSON compacto.
DEFAULT_JOB_OUTPUT_MAX_BYTES = 4096
_MAX_SAFE_INT = 2**53

# --- T-802: tempos limite ---------------------------------------------------------------------
# A CVM1 pede ao agente um limite para o script, le em /health a margem do agente e espera
# job + margem do agente + a propria folga: fica sempre acima do agente.
JOB_TIMEOUT_HEADER = "X-DNAT-Job-Timeout"
DEFAULT_JOB_TIMEOUT = 600
DEFAULT_AGENT_MARGIN = 120
DEFAULT_CVM1_MARGIN = 30
# Estados de metadata.json que viram inconclusivo por falha (E14 §9, T-107). O recibo do tipo
# falha e as tres tentativas sao de quem registra o veredito (T-703, T-807).
FAILURE_STATUSES = ("script_failed", "timeout", "agent_error", "output_rejected", "execution_failed")


def download_from_ipfs(ipfs_api_url: str, cid_or_uri: str) -> bytes:
    cid = normalize_cid(cid_or_uri)
    if not cid:
        raise ValueError("CID is required")
    base = ipfs_api_url.rstrip("/")
    url = f"{base}/api/v0/cat?arg={quote(cid)}"
    request = Request(url, method="POST")
    with urlopen(request) as response:  # nosec B310 - trusted local IPFS node in this project
        return response.read()


def build_workspace(
    execution_dir: pathlib.Path,
    dataset_bytes: bytes,
    *,
    script_bytes: bytes | None = None,
    use_application_artifact: bool = False,
) -> pathlib.Path:
    workspace_dir = execution_dir / "workspace"
    code_dir = workspace_dir / "code"
    data_dir = workspace_dir / "data"

    code_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    (execution_dir / "dataset.csv").write_bytes(dataset_bytes)
    (data_dir / "dataset.csv").write_bytes(dataset_bytes)

    if script_bytes is not None:
        (execution_dir / "application.py").write_bytes(script_bytes)
        (code_dir / "application.py").write_bytes(script_bytes)

        run_sh = """#!/bin/bash
set -euo pipefail

cd /tmp/exec/workspace
export DNAT_DERIVATIVE_DIR="/tmp/exec/workspace/derivative"
# T-804: unica saida do script que chega ao usuario; stdout e stderr sao descartados pelo agente.
export DNAT_METRICS_PATH="/tmp/exec/workspace/metrics.json"

attempt_1_stdout="$(mktemp)"
attempt_1_stderr="$(mktemp)"
attempt_2_stdout="$(mktemp)"
attempt_2_stderr="$(mktemp)"
attempt_3_stdout="$(mktemp)"
attempt_3_stderr="$(mktemp)"
attempt_4_stdout="$(mktemp)"
attempt_4_stderr="$(mktemp)"

if python3 code/application.py --dataset data/dataset.csv >"$attempt_1_stdout" 2>"$attempt_1_stderr"; then
    cat "$attempt_1_stdout"
    cat "$attempt_1_stderr" >&2
    exit 0
fi

if python3 code/application.py --dataset data/dataset.csv --output result.json >"$attempt_2_stdout" 2>"$attempt_2_stderr"; then
    cat "$attempt_2_stdout"
    cat "$attempt_2_stderr" >&2
    exit 0
fi

if python3 code/application.py data/dataset.csv >"$attempt_3_stdout" 2>"$attempt_3_stderr"; then
    cat "$attempt_3_stdout"
    cat "$attempt_3_stderr" >&2
    exit 0
fi

if python3 code/application.py >"$attempt_4_stdout" 2>"$attempt_4_stderr"; then
    cat "$attempt_4_stdout"
    cat "$attempt_4_stderr" >&2
    exit 0
fi

echo "All execution strategies failed." >&2
echo "--- attempt 1: python3 code/application.py --dataset data/dataset.csv" >&2
cat "$attempt_1_stdout"
cat "$attempt_1_stderr" >&2
echo "--- attempt 2: python3 code/application.py --dataset data/dataset.csv --output result.json" >&2
cat "$attempt_2_stdout"
cat "$attempt_2_stderr" >&2
echo "--- attempt 3: python3 code/application.py data/dataset.csv" >&2
cat "$attempt_3_stdout"
cat "$attempt_3_stderr" >&2
echo "--- attempt 4: python3 code/application.py" >&2
cat "$attempt_4_stdout"
cat "$attempt_4_stderr" >&2
exit 1
"""
    elif use_application_artifact:
        run_sh = """#!/bin/bash
set -euo pipefail

cd /tmp/exec/workspace
export DNAT_DERIVATIVE_DIR="/tmp/exec/workspace/derivative"
# T-804: unica saida do script que chega ao usuario; stdout e stderr sao descartados pelo agente.
export DNAT_METRICS_PATH="/tmp/exec/workspace/metrics.json"

APP="/mnt/dnat-app/app/application.py"
test -f "$APP"

if [ -d /mnt/dnat-app/app/site-packages ]; then
    export PYTHONPATH="/mnt/dnat-app/app/site-packages${PYTHONPATH:+:$PYTHONPATH}"
fi

attempt_1_stdout="$(mktemp)"
attempt_1_stderr="$(mktemp)"
attempt_2_stdout="$(mktemp)"
attempt_2_stderr="$(mktemp)"
attempt_3_stdout="$(mktemp)"
attempt_3_stderr="$(mktemp)"
attempt_4_stdout="$(mktemp)"
attempt_4_stderr="$(mktemp)"

if python3 "$APP" --dataset data/dataset.csv >"$attempt_1_stdout" 2>"$attempt_1_stderr"; then
    cat "$attempt_1_stdout"
    cat "$attempt_1_stderr" >&2
    exit 0
fi

if python3 "$APP" --dataset data/dataset.csv --output result.json >"$attempt_2_stdout" 2>"$attempt_2_stderr"; then
    cat "$attempt_2_stdout"
    cat "$attempt_2_stderr" >&2
    exit 0
fi

if python3 "$APP" data/dataset.csv >"$attempt_3_stdout" 2>"$attempt_3_stderr"; then
    cat "$attempt_3_stdout"
    cat "$attempt_3_stderr" >&2
    exit 0
fi

if python3 "$APP" >"$attempt_4_stdout" 2>"$attempt_4_stderr"; then
    cat "$attempt_4_stdout"
    cat "$attempt_4_stderr" >&2
    exit 0
fi

echo "All execution strategies failed." >&2
echo "--- attempt 1: python3 $APP --dataset data/dataset.csv" >&2
cat "$attempt_1_stdout"
cat "$attempt_1_stderr" >&2
echo "--- attempt 2: python3 $APP --dataset data/dataset.csv --output result.json" >&2
cat "$attempt_2_stdout"
cat "$attempt_2_stderr" >&2
echo "--- attempt 3: python3 $APP data/dataset.csv" >&2
cat "$attempt_3_stdout"
cat "$attempt_3_stderr" >&2
echo "--- attempt 4: python3 $APP" >&2
cat "$attempt_4_stdout"
cat "$attempt_4_stderr" >&2
exit 1
"""
    else:
        raise ValueError("Either script bytes or an application artifact is required")

    run_path = workspace_dir / "run.sh"
    run_path.write_text(run_sh, encoding="utf-8")
    run_path.chmod(0o755)

    return workspace_dir


def create_bundle(
    execution_dir: pathlib.Path,
    workspace_dir: pathlib.Path,
    *,
    application_artifact_path: pathlib.Path | None = None,
) -> pathlib.Path:
    bundle_path = execution_dir / "bundle.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        tar.add(workspace_dir, arcname="workspace")
        if application_artifact_path is not None:
            tar.add(application_artifact_path, arcname="artifacts/application.ext4")
    return bundle_path


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default
    return value if value > 0 else default


def fetch_agent_timeouts(executor_url: str) -> dict | None:
    """Limites que o agente anuncia em /health (job_default, job_max, agent_margin), ou None."""
    url = normalize_executor_url(executor_url)[: -len("/execute")] + "/health"
    try:
        with urlopen(Request(url, method="GET"), timeout=10) as response:  # nosec B310
            timeouts = json.loads(response.read().decode("utf-8")).get("timeouts")
    except (HTTPError, URLError, OSError, ValueError, AttributeError):
        return None
    if not isinstance(timeouts, dict):
        return None
    keys = ("job_default_seconds", "job_max_seconds", "agent_margin_seconds")
    if not all(isinstance(timeouts.get(k), int) and not isinstance(timeouts.get(k), bool) and timeouts[k] > 0 for k in keys):
        return None
    return {k: timeouts[k] for k in keys}


def plan_timeouts(requested: int | None, agent: dict | None, cvm1_margin: int) -> dict:
    """Limite do script, do agente e da CVM1, com a CVM1 sempre acima do agente."""
    job = requested if requested and requested > 0 else (agent or {}).get("job_default_seconds", DEFAULT_JOB_TIMEOUT)
    if agent:
        job = min(job, agent["job_max_seconds"])
    agent_seconds = job + (agent or {}).get("agent_margin_seconds", DEFAULT_AGENT_MARGIN)
    cvm1_margin = cvm1_margin if cvm1_margin > 0 else DEFAULT_CVM1_MARGIN
    return {"jobSeconds": job, "agentSeconds": agent_seconds, "cvm1Seconds": agent_seconds + cvm1_margin}


class CvmTimeout(Exception):
    """A CVM1 desistiu de esperar o agente: o job vira falha por tempo, sem travar."""


def _is_timeout(exc: BaseException) -> bool:
    return isinstance(exc, (TimeoutError, socket.timeout)) or (
        isinstance(exc, URLError) and isinstance(exc.reason, (TimeoutError, socket.timeout))
    )


def submit_bundle(executor_url: str, bundle_path: pathlib.Path, *, job_timeout: int | None = None, wait_seconds: float = 750) -> dict:
    headers = {"Content-Type": "application/gzip"}
    if job_timeout:
        headers[JOB_TIMEOUT_HEADER] = str(int(job_timeout))
    request = Request(
        normalize_executor_url(executor_url),
        data=bundle_path.read_bytes(),
        method="POST",
        headers=headers,
    )
    try:
        with urlopen(request, timeout=wait_seconds) as response:  # nosec B310 - trusted executor URL in this project
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        # O agente responde 503 "busy" no mesmo esquema fixo; outro erro HTTP sobe como antes.
        if exc.code != 503:
            raise
        raw = exc.read().decode("utf-8", errors="replace")
    except (URLError, OSError) as exc:
        if _is_timeout(exc):
            raise CvmTimeout(f"CVM1 waited {wait_seconds} s for the agent") from exc
        raise
    return json.loads(raw)


class JobOutputRejected(ValueError):
    """A resposta do agente nao segue o esquema fixo; nada dela chega ao usuario."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def load_metrics_schema() -> dict:
    raw = os.environ.get("DNAT_METRICS_SCHEMA", "").strip()
    if not raw:
        return dict(DEFAULT_METRICS_SCHEMA)
    schema = json.loads(raw)
    if not isinstance(schema, dict) or not schema or any(t not in ("number", "integer") for t in schema.values()):
        raise ValueError('DNAT_METRICS_SCHEMA must be a JSON object {"field": "number"|"integer"}')
    return schema


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and abs(value) <= _MAX_SAFE_INT


def _is_number(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and abs(value) <= 1e300)


def _check_metrics(metrics, schema: dict) -> dict:
    if not isinstance(metrics, dict):
        raise JobOutputRejected("metrics_not_object")
    out = {}
    for key, value in metrics.items():
        kind = schema.get(key)
        if kind is None:
            raise JobOutputRejected("metrics_unknown_field")
        if kind == "integer" and not _is_int(value):
            raise JobOutputRejected("metrics_bad_value")
        if kind == "number" and not _is_number(value):
            raise JobOutputRejected("metrics_bad_value")
        if (key == "steps" or key.endswith("_seconds")) and value < 0:
            raise JobOutputRejected("metrics_bad_value")
        out[key] = int(value) if kind == "integer" else float(f"{float(value):.6g}")
    return out


def validate_job_output(response, *, schema: dict | None = None, max_bytes: int | None = None) -> dict:
    """Confere a resposta do agente (ja sem o derivado) contra o esquema fixo e o teto de bytes.

    Devolve so as chaves do esquema. Qualquer chave a mais (stdout, stderr, logs), tipo errado,
    metrica fora do esquema ou excesso de bytes recusa a resposta inteira.
    """
    schema = load_metrics_schema() if schema is None else schema
    max_bytes = _env_int("DNAT_JOB_OUTPUT_MAX_BYTES", DEFAULT_JOB_OUTPUT_MAX_BYTES) if max_bytes is None else max_bytes
    if not isinstance(response, dict):
        raise JobOutputRejected("not_object")
    try:
        size = len(json.dumps(response, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    except ValueError as exc:
        raise JobOutputRejected("not_json") from exc
    if size > max_bytes:
        raise JobOutputRejected("too_large")
    if set(response) - JOB_OUTPUT_KEYS:
        raise JobOutputRejected("unexpected_field")
    if JOB_OUTPUT_KEYS - set(response):
        raise JobOutputRejected("missing_field")
    if response["schema"] != JOB_OUTPUT_SCHEMA_ID:
        raise JobOutputRejected("schema_id")
    if response["status"] not in JOB_STATUSES:
        raise JobOutputRejected("status")
    if response["returncode"] is not None and not _is_int(response["returncode"]):
        raise JobOutputRejected("returncode")
    if response["status"] == "ok" and response["returncode"] != 0:
        raise JobOutputRejected("returncode")
    for key in ("elapsed_seconds", "job_timeout_seconds"):
        value = response[key]
        if value is not None and (not _is_number(value) or value < 0):
            raise JobOutputRejected(key)
    if response["metrics_error"] is not None and response["metrics_error"] not in METRICS_ERRORS:
        raise JobOutputRejected("metrics_error")
    if response["error"] is not None and response["error"] not in AGENT_ERRORS:
        raise JobOutputRejected("error")
    out = {key: response[key] for key in sorted(JOB_OUTPUT_KEYS)}
    out["metrics"] = None if response["metrics"] is None else _check_metrics(response["metrics"], schema)
    return out


def rejected_output(job_timeout: int | None = None) -> dict:
    """O que fica em result.json quando a resposta do agente e recusada: nenhum dado dela."""
    return {
        "schema": JOB_OUTPUT_SCHEMA_ID, "status": "agent_error", "returncode": None,
        "elapsed_seconds": None, "job_timeout_seconds": job_timeout, "metrics": None,
        "metrics_error": None, "error": None,
    }


class DerivativeError(ValueError):
    """O derivado devolvido pela CVM de job nao confere com o digest declarado."""


def _set_digest(entries: list[dict]) -> str:
    # Mesma regra de model_gate.io.digest e de vm_runtime/derivative.py.
    h = hashlib.sha256()
    for e in sorted(entries, key=lambda e: e["path"]):
        h.update(f"{e['path']}\0{e['sha256']}\n".encode())
    return h.hexdigest()


def verify_derivative(derivative: dict) -> bytes:
    """Confere o pacote do derivado contra a lista de arquivos e o digest; devolve o tar.gz."""
    try:
        archive = base64.b64decode(derivative["archive"], validate=True)
        declared = {e["path"]: e["sha256"] for e in derivative["files"]}
        digest = derivative["digest"]
    except (KeyError, TypeError, binascii.Error) as exc:
        raise DerivativeError(f"malformed derivative: {exc}") from exc

    entries = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar:
            name = member.name
            if not member.isreg() or name.startswith("/") or ".." in pathlib.PurePosixPath(name).parts:
                raise DerivativeError(f"unexpected entry in derivative archive: {name}")
            h = hashlib.sha256()
            with tar.extractfile(member) as f:
                while chunk := f.read(1 << 20):
                    h.update(chunk)
            entries.append({"path": name, "sha256": h.hexdigest()})

    got = {e["path"]: e["sha256"] for e in entries}
    if len(got) != len(entries) or got != declared:
        raise DerivativeError("derivative archive does not match the declared files")
    if _set_digest(entries) != digest:
        raise DerivativeError("derivative digest mismatch")
    return archive


def retain_derivative(
    derivative: dict | None, derivative_out: str, *, job_succeeded: bool, failure_reason: str = "job failed"
) -> dict | None:
    """Separa o derivado da saida do job (T-803).

    Os pesos nunca vao para result.json, stdout.txt ou metadata.json. Se o job terminou bem e o
    digest confere, o tar.gz vai para derivative_out, um caminho temporario do plano de controle,
    que o cifra, guarda no IPFS e apaga o arquivo. Devolve so o resumo (digest e estado).
    """
    if not derivative:
        return None
    summary = {"digest": str(derivative.get("digest", "")) if isinstance(derivative, dict) else ""}
    if not job_succeeded:
        return {**summary, "status": "discarded", "reason": failure_reason}
    if not derivative_out:
        return {**summary, "status": "discarded", "reason": "no retention target"}
    try:
        archive = verify_derivative(derivative)
    except (DerivativeError, tarfile.TarError, OSError) as exc:
        return {**summary, "status": "invalid", "error": str(exc)}
    out = pathlib.Path(derivative_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(archive)
    return {**summary, "status": "received"}


def build_metadata(
    execution_id: str,
    dataset_cid: str,
    application_cid: str,
    ipfs_api_url: str,
    executor_url: str,
    execution_dir: pathlib.Path,
    *,
    status: str,
    return_code: int | None = None,
    error: str | None = None,
    used_application_artifact: bool = False,
    derivative: dict | None = None,
    timeouts: dict | None = None,
) -> dict:
    metadata = {
        "executionId": execution_id,
        "status": status,
        "returnCode": return_code,
        "datasetCid": normalize_cid(dataset_cid),
        "applicationCid": normalize_cid(application_cid),
        "ipfsApiUrl": ipfs_api_url,
        "executorUrl": normalize_executor_url(executor_url),
        "datasetPath": str((execution_dir / "dataset.csv").resolve()),
        "bundlePath": str((execution_dir / "bundle.tar.gz").resolve()),
        "applicationArtifactPath": str((execution_dir / "application.ext4").resolve()) if used_application_artifact else None,
        "scriptPath": str((execution_dir / "application.py").resolve()) if (execution_dir / "application.py").exists() else None,
        "resultPath": str((execution_dir / "result.json").resolve()),
        # T-802/T-107: toda falha (inclusive tempo estourado) e inconclusivo por falha, sem merito.
        "outcome": "inconclusive_failure" if status in FAILURE_STATUSES else "completed",
        "createdAtUtc": utc_now().isoformat().replace("+00:00", "Z"),
    }
    if timeouts:
        metadata["timeouts"] = timeouts
    if error:
        metadata["error"] = error
    if derivative:
        metadata["derivative"] = derivative
    return metadata


def write_execution_files(execution_dir: pathlib.Path, job_output: dict) -> None:
    """So o JSON de esquema fixo vai ao disco da execucao (T-804): sem stdout.txt nem stderr.txt."""
    (execution_dir / "result.json").write_text(json.dumps(job_output, indent=2), encoding="utf-8")


_STATUS_FROM_AGENT = {"ok": "success", "script_failed": "script_failed", "timeout": "timeout", "agent_error": "agent_error"}


def _failure_message(job_output: dict) -> str | None:
    if job_output["status"] == "timeout":
        return f"job exceeded the agent time limit ({job_output['job_timeout_seconds']} s)"
    if job_output["status"] == "agent_error":
        return f"agent error: {job_output['error']}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare dataset and application artifacts for vm_runtime and store execution artifacts."
    )
    parser.add_argument("--dataset-cid", default="", help="IPFS CID for dataset")
    parser.add_argument("--application-cid", default="", help="IPFS CID for application artifact")
    parser.add_argument("--script-cid", default="", help="Legacy IPFS CID for plain Python script")
    parser.add_argument("--local-dataset-path", default="", help="Local dataset path, bypassing IPFS download")
    parser.add_argument("--application-artifact-path", default="", help="Local application ext4 artifact path")
    parser.add_argument(
        "--ipfs-api-url",
        default=os.getenv("IPFS_API_URL", "http://localhost:5001"),
        help="IPFS API base URL (default: http://localhost:5001)",
    )
    parser.add_argument(
        "--executor-url",
        default=os.getenv("EXECUTOR_URL", "http://localhost:5000"),
        help="vm_runtime executor base URL (default: http://localhost:5000)",
    )
    parser.add_argument(
        "--derivative-out",
        default="",
        help="Where the control plane wants the verified derivative archive (T-803); without it the derivative is discarded",
    )
    parser.add_argument(
        "--job-timeout",
        type=int,
        default=_env_int("DNAT_JOB_TIMEOUT_SECONDS", 0) or None,
        help="Time limit for the job script, in seconds (T-802); default: the agent's own default",
    )
    parser.add_argument(
        "--cvm1-margin",
        type=int,
        default=_env_int("DNAT_CVM1_MARGIN_SECONDS", DEFAULT_CVM1_MARGIN),
        help="How much longer than the agent the CVM1 waits, in seconds (T-802)",
    )
    parser.add_argument(
        "--executions-dir",
        default=str(pathlib.Path(__file__).resolve().parents[1] / "executions"),
        help="Where execution artifacts are stored",
    )
    args = parser.parse_args()

    if not args.local_dataset_path and not args.dataset_cid:
        raise SystemExit("Either --local-dataset-path or --dataset-cid is required")
    if not args.application_artifact_path and not args.script_cid:
        raise SystemExit("Either --application-artifact-path or --script-cid is required")

    execution_id = f"{utc_now().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    execution_dir = pathlib.Path(args.executions_dir).resolve() / execution_id
    execution_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = execution_dir / "metadata.json"
    timeouts = None

    try:
        if args.local_dataset_path:
            dataset_bytes = pathlib.Path(args.local_dataset_path).resolve().read_bytes()
        else:
            dataset_bytes = download_from_ipfs(args.ipfs_api_url, args.dataset_cid)
            # A chave de cifra vive so no plano de controle, entao o runner nao decifra:
            # falha alto em vez de entregar ciphertext como se fosse o dataset.
            if dataset_bytes.startswith(ENCRYPTED_ENVELOPE_MAGIC):
                raise SystemExit(
                    "Dataset is encrypted; fetch it through the control plane "
                    "(which passes --local-dataset-path) instead of --dataset-cid."
                )

        script_bytes = None
        application_artifact_path = None

        if args.application_artifact_path:
            source_artifact = pathlib.Path(args.application_artifact_path).resolve()
            application_artifact_path = execution_dir / "application.ext4"
            shutil.copyfile(source_artifact, application_artifact_path)
        elif args.script_cid:
            script_bytes = download_from_ipfs(args.ipfs_api_url, args.script_cid)

        workspace_dir = build_workspace(
            execution_dir,
            dataset_bytes,
            script_bytes=script_bytes,
            use_application_artifact=application_artifact_path is not None,
        )
        bundle_path = create_bundle(
            execution_dir,
            workspace_dir,
            application_artifact_path=application_artifact_path,
        )
        timeouts = plan_timeouts(args.job_timeout, fetch_agent_timeouts(args.executor_url), args.cvm1_margin)
        try:
            vm_result = submit_bundle(
                args.executor_url, bundle_path, job_timeout=timeouts["jobSeconds"], wait_seconds=timeouts["cvm1Seconds"]
            )
        except CvmTimeout as exc:
            write_execution_files(execution_dir, rejected_output(timeouts["jobSeconds"]) | {"status": "timeout"})
            metadata = build_metadata(
                execution_id,
                args.dataset_cid,
                args.application_cid or args.script_cid,
                args.ipfs_api_url,
                args.executor_url,
                execution_dir,
                status="timeout",
                error=str(exc),
                used_application_artifact=application_artifact_path is not None,
                timeouts=timeouts,
            )
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            print(json.dumps(metadata, indent=2))
            return 124

        # O derivado sai da resposta antes de qualquer arquivo da execucao ser escrito.
        raw_derivative = vm_result.pop("derivative", None) if isinstance(vm_result, dict) else None
        try:
            job_output = validate_job_output(vm_result)
            status = _STATUS_FROM_AGENT[job_output["status"]]
            error = _failure_message(job_output)
        except JobOutputRejected as exc:
            # Nada da resposta recusada e gravado nem devolvido; so o codigo do motivo.
            job_output = rejected_output(timeouts["jobSeconds"])
            status = "output_rejected"
            error = f"agent output rejected: {exc.code}"
        derivative = retain_derivative(
            raw_derivative,
            args.derivative_out,
            job_succeeded=status == "success",
            failure_reason="output rejected" if status == "output_rejected" else "job failed",
        )
        write_execution_files(execution_dir, job_output)

        metadata = build_metadata(
            execution_id,
            args.dataset_cid,
            args.application_cid or args.script_cid,
            args.ipfs_api_url,
            args.executor_url,
            execution_dir,
            status=status,
            return_code=job_output["returncode"],
            error=error,
            used_application_artifact=application_artifact_path is not None,
            derivative=derivative,
            timeouts=timeouts,
        )
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(json.dumps(metadata, indent=2))
        if status == "success":
            return 0
        if status == "timeout":
            return 124
        return job_output["returncode"] if job_output["returncode"] else 1

    except (HTTPError, URLError, ValueError, OSError, json.JSONDecodeError) as exc:
        metadata = build_metadata(
            execution_id,
            args.dataset_cid,
            args.application_cid or args.script_cid,
            args.ipfs_api_url,
            args.executor_url,
            execution_dir,
            status="execution_failed",
            error=str(exc),
            used_application_artifact=bool(args.application_artifact_path),
            timeouts=timeouts,
        )
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(json.dumps(metadata, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
