#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import uuid
from urllib.parse import quote
from urllib.request import Request, urlopen


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def normalize_cid(cid_or_uri: str) -> str:
    value = (cid_or_uri or "").strip()
    if value.startswith("ipfs://"):
        return value[len("ipfs://") :]
    return value


def download_from_ipfs(ipfs_api_url: str, cid_or_uri: str) -> bytes:
    cid = normalize_cid(cid_or_uri)
    if not cid:
        raise ValueError("CID is required")
    base = ipfs_api_url.rstrip("/")
    url = f"{base}/api/v0/cat?arg={quote(cid)}"
    # Kubo HTTP API endpoints are invoked with POST.
    request = Request(url, method="POST")
    with urlopen(request) as response:  # nosec B310 - trusted local IPFS node in this project
        return response.read()


def run_script(script_path: pathlib.Path, dataset_path: pathlib.Path, result_path: pathlib.Path) -> subprocess.CompletedProcess:
    # First try a richer contract commonly used by ML scripts.
    primary_cmd = [
        sys.executable,
        str(script_path),
        "--dataset",
        str(dataset_path),
        "--output",
        str(result_path),
    ]
    primary = subprocess.run(primary_cmd, capture_output=True, text=True)
    if primary.returncode == 0:
        return primary

    # Fallback to positional dataset argument.
    fallback_cmd = [sys.executable, str(script_path), str(dataset_path)]
    return subprocess.run(fallback_cmd, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download dataset and script from IPFS CIDs, execute script, and store result artifacts."
    )
    parser.add_argument("--dataset-cid", required=True, help="IPFS CID for CSV dataset")
    parser.add_argument("--script-cid", required=True, help="IPFS CID for Python script")
    parser.add_argument(
        "--ipfs-api-url",
        default=os.getenv("IPFS_API_URL", "http://localhost:5001"),
        help="IPFS API base URL (default: http://localhost:5001)",
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

    dataset_path = execution_dir / "dataset.csv"
    script_path = execution_dir / "application.py"
    result_path = execution_dir / "result.json"
    stdout_path = execution_dir / "stdout.txt"
    stderr_path = execution_dir / "stderr.txt"
    metadata_path = execution_dir / "metadata.json"

    try:
        dataset_bytes = download_from_ipfs(args.ipfs_api_url, args.dataset_cid)
        script_bytes = download_from_ipfs(args.ipfs_api_url, args.script_cid)
    except Exception as exc:
        error_payload = {
            "executionId": execution_id,
            "status": "download_failed",
            "error": str(exc),
            "datasetCid": normalize_cid(args.dataset_cid),
            "scriptCid": normalize_cid(args.script_cid),
            "ipfsApiUrl": args.ipfs_api_url,
            "createdAtUtc": utc_now().isoformat().replace("+00:00", "Z"),
        }
        metadata_path.write_text(json.dumps(error_payload, indent=2), encoding="utf-8")
        print(json.dumps(error_payload, indent=2))
        return 1

    dataset_path.write_bytes(dataset_bytes)
    script_path.write_bytes(script_bytes)

    run = run_script(script_path, dataset_path, result_path)

    stdout_path.write_text(run.stdout or "", encoding="utf-8")
    stderr_path.write_text(run.stderr or "", encoding="utf-8")

    metadata = {
        "executionId": execution_id,
        "status": "success" if run.returncode == 0 else "script_failed",
        "returnCode": run.returncode,
        "datasetCid": normalize_cid(args.dataset_cid),
        "scriptCid": normalize_cid(args.script_cid),
        "ipfsApiUrl": args.ipfs_api_url,
        "datasetPath": str(dataset_path),
        "scriptPath": str(script_path),
        "resultPath": str(result_path),
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
        "createdAtUtc": utc_now().isoformat().replace("+00:00", "Z"),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps(metadata, indent=2))
    return 0 if run.returncode == 0 else run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
