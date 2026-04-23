#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import pathlib
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


def build_workspace(execution_dir: pathlib.Path, dataset_bytes: bytes, script_bytes: bytes) -> pathlib.Path:
    workspace_dir = execution_dir / "workspace"
    code_dir = workspace_dir / "code"
    data_dir = workspace_dir / "data"

    code_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    (execution_dir / "dataset.csv").write_bytes(dataset_bytes)
    (execution_dir / "application.py").write_bytes(script_bytes)
    (data_dir / "dataset.csv").write_bytes(dataset_bytes)
    (code_dir / "application.py").write_bytes(script_bytes)

    run_sh = """#!/bin/bash
set -euo pipefail

cd /tmp/exec/workspace

if python3 code/application.py --dataset data/dataset.csv --output result.json; then
    exit 0
fi

python3 code/application.py data/dataset.csv
"""
    run_path = workspace_dir / "run.sh"
    run_path.write_text(run_sh, encoding="utf-8")
    run_path.chmod(0o755)

    return workspace_dir


def create_bundle(execution_dir: pathlib.Path, workspace_dir: pathlib.Path) -> pathlib.Path:
    bundle_path = execution_dir / "bundle.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        tar.add(workspace_dir, arcname="workspace")
    return bundle_path


def submit_bundle(executor_url: str, bundle_path: pathlib.Path) -> dict:
    request = Request(
        normalize_executor_url(executor_url),
        data=bundle_path.read_bytes(),
        method="POST",
        headers={"Content-Type": "application/gzip"},
    )
    with urlopen(request, timeout=330) as response:  # nosec B310 - trusted executor URL in this project
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def build_metadata(
    execution_id: str,
    dataset_cid: str,
    script_cid: str,
    ipfs_api_url: str,
    executor_url: str,
    execution_dir: pathlib.Path,
    *,
    status: str,
    return_code: int | None = None,
    error: str | None = None,
) -> dict:
    metadata = {
        "executionId": execution_id,
        "status": status,
        "returnCode": return_code,
        "datasetCid": normalize_cid(dataset_cid),
        "scriptCid": normalize_cid(script_cid),
        "ipfsApiUrl": ipfs_api_url,
        "executorUrl": normalize_executor_url(executor_url),
        "datasetPath": str((execution_dir / "dataset.csv").resolve()),
        "scriptPath": str((execution_dir / "application.py").resolve()),
        "bundlePath": str((execution_dir / "bundle.tar.gz").resolve()),
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
        description="Download dataset and script from IPFS CIDs, package them for vm_runtime, and store execution artifacts."
    )
    parser.add_argument("--dataset-cid", required=True, help="IPFS CID for CSV dataset")
    parser.add_argument("--script-cid", required=True, help="IPFS CID for Python script")
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

    execution_id = f"{utc_now().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    execution_dir = pathlib.Path(args.executions_dir).resolve() / execution_id
    execution_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = execution_dir / "metadata.json"

    try:
        dataset_bytes = download_from_ipfs(args.ipfs_api_url, args.dataset_cid)
        script_bytes = download_from_ipfs(args.ipfs_api_url, args.script_cid)
        workspace_dir = build_workspace(execution_dir, dataset_bytes, script_bytes)
        bundle_path = create_bundle(execution_dir, workspace_dir)
        vm_result = submit_bundle(args.executor_url, bundle_path)

        write_execution_files(execution_dir, vm_result)

        metadata = build_metadata(
            execution_id,
            args.dataset_cid,
            args.script_cid,
            args.ipfs_api_url,
            args.executor_url,
            execution_dir,
            status="success" if vm_result.get("returncode") == 0 else "script_failed",
            return_code=vm_result.get("returncode"),
        )
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(json.dumps(metadata, indent=2))
        return int(vm_result.get("returncode", 1))

    except (HTTPError, URLError, ValueError, OSError, json.JSONDecodeError) as exc:
        metadata = build_metadata(
            execution_id,
            args.dataset_cid,
            args.script_cid,
            args.ipfs_api_url,
            args.executor_url,
            execution_dir,
            status="execution_failed",
            error=str(exc),
        )
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(json.dumps(metadata, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
