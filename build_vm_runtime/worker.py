#!/usr/bin/env python3
"""Ephemeral worker process for a single DNAT build request."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


WHEEL_CACHE_DIR = Path(os.getenv("WHEEL_CACHE_SOURCE_DIR", "/var/dnat/wheel-cache")).resolve()
WHEEL_CACHE_MAX_BYTES = int(os.getenv("WHEEL_CACHE_MAX_BYTES", str(2 * 1024 * 1024 * 1024)))
WHEEL_CACHE_MAX_FILE_BYTES = int(os.getenv("WHEEL_CACHE_MAX_FILE_BYTES", str(250 * 1024 * 1024)))


def compute_sha256_hex(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def validate_wheel_filename(file_name: str) -> str:
    base = Path(file_name).name
    if not base or base != file_name:
        raise ValueError(f"Invalid wheel filename: {file_name}")
    if not base.endswith(".whl"):
        raise ValueError(f"Only .whl files may enter the wheel cache: {file_name}")
    if "/" in base or "\\" in base:
        raise ValueError(f"Unsafe wheel filename: {file_name}")
    return base


def ensure_wheel_cache_dir() -> Path:
    WHEEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return WHEEL_CACHE_DIR


def list_cached_wheel_entries() -> list[dict]:
    ensure_wheel_cache_dir()
    entries = []
    for entry in WHEEL_CACHE_DIR.iterdir():
        if not entry.is_file() or entry.suffix != ".whl":
            continue
        stats = entry.stat()
        entries.append({"path": entry, "size": stats.st_size, "mtime_ns": stats.st_mtime_ns})
    return entries


def prune_wheel_cache() -> None:
    entries = sorted(list_cached_wheel_entries(), key=lambda item: item["mtime_ns"])
    total_bytes = sum(item["size"] for item in entries)
    for entry in entries:
        if total_bytes <= WHEEL_CACHE_MAX_BYTES:
            break
        entry["path"].unlink(missing_ok=True)
        total_bytes -= entry["size"]


def ingest_built_wheelhouse(wheelhouse_dir: Path) -> list[dict]:
    if not wheelhouse_dir.is_dir():
        return []

    ensure_wheel_cache_dir()
    stored = []
    for entry in wheelhouse_dir.iterdir():
        if not entry.is_file():
            continue

        wheel_name = validate_wheel_filename(entry.name)
        stats = entry.stat()
        if stats.st_size > WHEEL_CACHE_MAX_FILE_BYTES:
            continue

        data = entry.read_bytes()
        digest = compute_sha256_hex(data)
        target_path = WHEEL_CACHE_DIR / wheel_name
        if target_path.exists():
            existing_digest = compute_sha256_hex(target_path.read_bytes())
            if existing_digest != digest:
                continue
        else:
            target_path.write_bytes(data)

        stored.append(
            {
                "fileName": wheel_name,
                "sha256": digest,
                "sizeBytes": stats.st_size,
            }
        )

    prune_wheel_cache()
    return stored


def package_response(response_dir: Path, application_artifact: Path, build_result_path: Path) -> None:
    with tarfile.open(response_dir / "response.tar.gz", "w:gz") as bundle:
        bundle.add(application_artifact, arcname="application.ext4")
        if build_result_path.is_file():
            bundle.add(build_result_path, arcname="build-result.json")


def run_worker(input_bundle: Path, output_bundle: Path) -> int:
    with tempfile.TemporaryDirectory(prefix="dnat-builder-worker-") as temp_dir:
        temp_root = Path(temp_dir)
        worker_input = temp_root / "request.tar.gz"
        worker_output = temp_root / "build-output.tar.gz"
        extracted_output = temp_root / "extracted"
        extracted_output.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(input_bundle, worker_input)

        result = subprocess.run(
            ["bash", str(Path(__file__).parent / "vm" / "build-vm.sh"), str(worker_input), str(worker_output)],
            capture_output=True,
            text=True,
            timeout=2400,
        )

        if result.returncode != 0:
            print(result.stdout or result.stderr, end="")
            return result.returncode

        with tarfile.open(worker_output, "r:gz") as bundle:
            bundle.extractall(extracted_output)

        app_ext4 = extracted_output / "application.ext4"
        build_result_path = extracted_output / "build-result.json"
        wheelhouse_dir = extracted_output / "wheelhouse"
        if not app_ext4.is_file():
            print(json.dumps({"error": "worker missing application.ext4"}))
            return 1

        cached_wheels = ingest_built_wheelhouse(wheelhouse_dir)
        if build_result_path.is_file():
            try:
                build_result = json.loads(build_result_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                build_result = {}
            build_result["cachedWheels"] = cached_wheels
            build_result_path.write_text(json.dumps(build_result, indent=2), encoding="utf-8")

        response_dir = temp_root / "response"
        response_dir.mkdir(parents=True, exist_ok=True)
        package_response(response_dir, app_ext4, build_result_path)
        shutil.copyfile(response_dir / "response.tar.gz", output_bundle)
        return 0


def main() -> int:
    import sys

    if len(sys.argv) != 3:
        print("usage: worker.py <request-bundle.tar.gz> <response-bundle.tar.gz>", file=sys.stderr)
        return 2

    input_bundle = Path(sys.argv[1]).resolve()
    output_bundle = Path(sys.argv[2]).resolve()
    return run_worker(input_bundle, output_bundle)


if __name__ == "__main__":
    raise SystemExit(main())
