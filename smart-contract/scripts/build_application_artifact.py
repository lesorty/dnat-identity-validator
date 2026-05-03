#!/usr/bin/env python3

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MIN_IMAGE_BYTES = 16 * 1024 * 1024
EXTRA_IMAGE_BYTES = 8 * 1024 * 1024
IMAGE_HEADROOM_FACTOR = 4
SITE_PACKAGES_DIRNAME = "site-packages"


def compute_directory_size(root: Path) -> int:
    total = 0
    for entry in root.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total


def parse_dependencies(raw_dependencies: str) -> list[str]:
    raw_value = str(raw_dependencies or "").strip()
    if not raw_value:
        return []

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]

    lines = [line.strip() for line in raw_value.splitlines() if line.strip() and not line.strip().startswith("#")]
    if not lines:
        return []

    if len(lines) == 1 and "," in lines[0]:
        candidates = [item.strip() for item in lines[0].split(",") if item.strip()]
        if all(re.match(r"^[A-Za-z0-9_.\-\[\]]+(?:\s*[<>=!~].+)?$", item) for item in candidates):
            return candidates

    return lines


def build_wheels(
    dependencies: list[str],
    *,
    wheel_cache_dir: Path | None,
    output_wheelhouse_dir: Path | None,
) -> None:
    if not dependencies or output_wheelhouse_dir is None:
        return

    output_wheelhouse_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "python3",
        "-m",
        "pip",
        "wheel",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--wheel-dir",
        str(output_wheelhouse_dir),
        "--prefer-binary",
    ]
    if wheel_cache_dir is not None and wheel_cache_dir.is_dir():
        command.extend(["--find-links", str(wheel_cache_dir)])
    command.extend(dependencies)
    subprocess.run(command, check=True)


def install_python_dependencies(
    target_dir: Path,
    dependencies: list[str],
    *,
    wheel_cache_dir: Path | None,
    output_wheelhouse_dir: Path | None,
) -> None:
    if not dependencies:
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    build_wheels(
        dependencies,
        wheel_cache_dir=wheel_cache_dir,
        output_wheelhouse_dir=output_wheelhouse_dir,
    )

    command = [
        "python3",
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--target",
        str(target_dir),
        "--no-index",
    ]
    if output_wheelhouse_dir is not None and output_wheelhouse_dir.is_dir():
        command.extend(["--find-links", str(output_wheelhouse_dir)])
    if wheel_cache_dir is not None and wheel_cache_dir.is_dir():
        command.extend(["--find-links", str(wheel_cache_dir)])
    command.extend(dependencies)
    subprocess.run(command, check=True)


def freeze_installed_dependencies(target_dir: Path) -> str:
    if not target_dir.is_dir():
        return ""

    completed = subprocess.run(
        ["python3", "-m", "pip", "freeze", "--path", str(target_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a read-only ext4 application artifact for DNAT execution."
    )
    parser.add_argument("--source-file", required=True, help="Path to the uploaded application source file")
    parser.add_argument("--output-image", required=True, help="Where the ext4 artifact image will be written")
    parser.add_argument("--title", default="", help="Application title")
    parser.add_argument("--description", default="", help="Application description")
    parser.add_argument("--framework", default="python", help="Framework/runtime label")
    parser.add_argument("--dependencies", default="", help="Free-form dependency metadata")
    parser.add_argument("--wheel-cache-dir", default="", help="Optional read-only directory containing cached .whl files")
    parser.add_argument("--output-wheelhouse-dir", default="", help="Optional directory where new .whl files should be written")
    args = parser.parse_args()

    source_file = Path(args.source_file).resolve()
    output_image = Path(args.output_image).resolve()

    if not source_file.is_file():
        raise SystemExit(f"Source file not found: {source_file}")

    dependencies = parse_dependencies(args.dependencies)
    wheel_cache_dir = Path(args.wheel_cache_dir).resolve() if args.wheel_cache_dir else None
    output_wheelhouse_dir = Path(args.output_wheelhouse_dir).resolve() if args.output_wheelhouse_dir else None
    output_image.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="dnat-app-artifact-") as temp_dir:
        root_dir = Path(temp_dir) / "rootfs"
        app_dir = root_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(source_file, app_dir / "application.py")
        (root_dir / "dnat-application.marker").write_text("dnat-application\n", encoding="utf-8")
        install_python_dependencies(
            app_dir / SITE_PACKAGES_DIRNAME,
            dependencies,
            wheel_cache_dir=wheel_cache_dir,
            output_wheelhouse_dir=output_wheelhouse_dir,
        )

        manifest = {
            "title": args.title,
            "description": args.description,
            "framework": args.framework,
            "dependencies": dependencies,
            "entrypoint": "/app/application.py",
            "pythonVersion": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "sourceFileName": source_file.name,
        }
        (app_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        if dependencies:
            (app_dir / "requirements.lock.txt").write_text("\n".join(dependencies) + "\n", encoding="utf-8")
            frozen = freeze_installed_dependencies(app_dir / SITE_PACKAGES_DIRNAME)
            if frozen:
                (app_dir / "requirements.installed.txt").write_text(frozen + "\n", encoding="utf-8")

        dir_size = compute_directory_size(root_dir)
        image_size = max(MIN_IMAGE_BYTES, dir_size * IMAGE_HEADROOM_FACTOR + EXTRA_IMAGE_BYTES)

        if output_image.exists():
            output_image.unlink()

        subprocess.run(["truncate", "-s", str(image_size), str(output_image)], check=True)
        subprocess.run(
            ["mkfs.ext4", "-q", "-F", "-d", str(root_dir), str(output_image)],
            check=True,
        )

    print(json.dumps({"artifactPath": str(output_image), "sizeBytes": output_image.stat().st_size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
