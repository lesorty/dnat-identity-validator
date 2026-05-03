#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
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

attempt_1_stdout="$(mktemp)"
attempt_1_stderr="$(mktemp)"
attempt_2_stdout="$(mktemp)"
attempt_2_stderr="$(mktemp)"
attempt_3_stdout="$(mktemp)"
attempt_3_stderr="$(mktemp)"

if python3 code/application.py --dataset data/dataset.csv --output result.json >"$attempt_1_stdout" 2>"$attempt_1_stderr"; then
    cat "$attempt_1_stdout"
    cat "$attempt_1_stderr" >&2
    exit 0
fi

if python3 code/application.py data/dataset.csv >"$attempt_2_stdout" 2>"$attempt_2_stderr"; then
    cat "$attempt_2_stdout"
    cat "$attempt_2_stderr" >&2
    exit 0
fi

if python3 code/application.py >"$attempt_3_stdout" 2>"$attempt_3_stderr"; then
    cat "$attempt_3_stdout"
    cat "$attempt_3_stderr" >&2
    exit 0
fi

echo "All execution strategies failed." >&2
echo "--- attempt 1: python3 code/application.py --dataset data/dataset.csv --output result.json" >&2
cat "$attempt_1_stdout"
cat "$attempt_1_stderr" >&2
echo "--- attempt 2: python3 code/application.py data/dataset.csv" >&2
cat "$attempt_2_stdout"
cat "$attempt_2_stderr" >&2
echo "--- attempt 3: python3 code/application.py" >&2
cat "$attempt_3_stdout"
cat "$attempt_3_stderr" >&2
exit 1
"""
    elif use_application_artifact:
        run_sh = """#!/bin/bash
set -euo pipefail

cd /tmp/exec/workspace

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

if python3 "$APP" --dataset data/dataset.csv --output result.json >"$attempt_1_stdout" 2>"$attempt_1_stderr"; then
    cat "$attempt_1_stdout"
    cat "$attempt_1_stderr" >&2
    exit 0
fi

if python3 "$APP" data/dataset.csv >"$attempt_2_stdout" 2>"$attempt_2_stderr"; then
    cat "$attempt_2_stdout"
    cat "$attempt_2_stderr" >&2
    exit 0
fi

if python3 "$APP" >"$attempt_3_stdout" 2>"$attempt_3_stderr"; then
    cat "$attempt_3_stdout"
    cat "$attempt_3_stderr" >&2
    exit 0
fi

echo "All execution strategies failed." >&2
echo "--- attempt 1: python3 $APP --dataset data/dataset.csv --output result.json" >&2
cat "$attempt_1_stdout"
cat "$attempt_1_stderr" >&2
echo "--- attempt 2: python3 $APP data/dataset.csv" >&2
cat "$attempt_2_stdout"
cat "$attempt_2_stderr" >&2
echo "--- attempt 3: python3 $APP" >&2
cat "$attempt_3_stdout"
cat "$attempt_3_stderr" >&2
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


def submit_bundle(executor_url: str, bundle_path: pathlib.Path) -> dict:
    request = Request(
        normalize_executor_url(executor_url),
        data=bundle_path.read_bytes(),
        method="POST",
        headers={"Content-Type": "application/gzip"},
    )
    with urlopen(request, timeout=750) as response:  # nosec B310 - trusted executor URL in this project
        raw = response.read().decode("utf-8")
    return json.loads(raw)


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
        "stdoutPath": str((execution_dir / "stdout.txt").resolve()),
        "stderrPath": str((execution_dir / "stderr.txt").resolve()),
        "createdAtUtc": utc_now().isoformat().replace("+00:00", "Z"),
    }
    if error:
        metadata["error"] = error
    return metadata


def write_execution_files(execution_dir: pathlib.Path, vm_result: dict) -> None:
    (execution_dir / "stdout.txt").write_text(vm_result.get("stdout", "") or "", encoding="utf-8")
    (execution_dir / "stderr.txt").write_text(vm_result.get("stderr", "") or "", encoding="utf-8")
    (execution_dir / "result.json").write_text(json.dumps(vm_result, indent=2), encoding="utf-8")


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

    try:
        if args.local_dataset_path:
            dataset_bytes = pathlib.Path(args.local_dataset_path).resolve().read_bytes()
        else:
            dataset_bytes = download_from_ipfs(args.ipfs_api_url, args.dataset_cid)

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
        vm_result = submit_bundle(args.executor_url, bundle_path)

        write_execution_files(execution_dir, vm_result)

        metadata = build_metadata(
            execution_id,
            args.dataset_cid,
            args.application_cid or args.script_cid,
            args.ipfs_api_url,
            args.executor_url,
            execution_dir,
            status="success" if vm_result.get("returncode") == 0 else "script_failed",
            return_code=vm_result.get("returncode"),
            used_application_artifact=application_artifact_path is not None,
        )
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(json.dumps(metadata, indent=2))
        return int(vm_result.get("returncode", 1))

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
        )
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(json.dumps(metadata, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
