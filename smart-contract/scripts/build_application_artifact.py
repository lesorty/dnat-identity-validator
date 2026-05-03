#!/usr/bin/env python3

import argparse
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

MIN_IMAGE_BYTES = 16 * 1024 * 1024
EXTRA_IMAGE_BYTES = 8 * 1024 * 1024
IMAGE_HEADROOM_FACTOR = 4


def compute_directory_size(root: Path) -> int:
    total = 0
    for entry in root.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total


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
    args = parser.parse_args()

    source_file = Path(args.source_file).resolve()
    output_image = Path(args.output_image).resolve()

    if not source_file.is_file():
        raise SystemExit(f"Source file not found: {source_file}")

    output_image.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="dnat-app-artifact-") as temp_dir:
        root_dir = Path(temp_dir) / "rootfs"
        app_dir = root_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(source_file, app_dir / "application.py")
        (root_dir / "dnat-application.marker").write_text("dnat-application\n", encoding="utf-8")

        manifest = {
            "title": args.title,
            "description": args.description,
            "framework": args.framework,
            "dependencies": args.dependencies,
            "entrypoint": "/app/application.py",
            "sourceFileName": source_file.name,
        }
        (app_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

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
