#!/usr/bin/env python3

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version

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


def resolve_required_binary(name: str, fallbacks: list[str] | None = None) -> str:
    resolved = shutil.which(name)
    if resolved:
        return resolved

    for candidate in fallbacks or []:
        if Path(candidate).is_file():
            return candidate

    raise FileNotFoundError(f"Required binary not found: {name}")


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


def latest_cached_versions_by_package(wheel_cache_dir: Path | None) -> dict[str, Version]:
    if wheel_cache_dir is None or not wheel_cache_dir.is_dir():
        return {}

    latest: dict[str, Version] = {}
    for entry in wheel_cache_dir.iterdir():
        if not entry.is_file() or entry.suffix != ".whl":
            continue
        try:
            name, version, _, _ = parse_wheel_filename(entry.name)
        except Exception:  # noqa: BLE001 - skip malformed cache entries
            continue
        current = latest.get(name)
        if current is None or version > current:
            latest[name] = version
    return latest


def pin_unversioned_dependencies_from_cache(
    dependencies: list[str],
    wheel_cache_dir: Path | None,
) -> list[str]:
    if not dependencies:
        return []

    latest_cached = latest_cached_versions_by_package(wheel_cache_dir)
    resolved: list[str] = []

    for raw_dependency in dependencies:
        try:
            requirement = Requirement(raw_dependency)
        except InvalidRequirement:
            resolved.append(raw_dependency)
            continue

        if requirement.url or str(requirement.specifier):
            resolved.append(raw_dependency)
            continue

        cached_version = latest_cached.get(canonicalize_name(requirement.name))
        if cached_version is None:
            resolved.append(raw_dependency)
            continue

        extras = f"[{','.join(sorted(requirement.extras))}]" if requirement.extras else ""
        marker = f"; {requirement.marker}" if requirement.marker else ""
        resolved.append(f"{requirement.name}{extras}=={cached_version}{marker}")

    return resolved


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


def clear_directory_contents(target_dir: Path) -> None:
    if not target_dir.exists():
        return

    for child in target_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def pip_install(
    target_dir: Path,
    dependencies: list[str],
    *,
    find_links: list[Path],
    no_index: bool,
) -> None:
    command = [
        "python3",
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--target",
        str(target_dir),
    ]
    if no_index:
        command.append("--no-index")
    for link_dir in find_links:
        if link_dir.is_dir():
            command.extend(["--find-links", str(link_dir)])
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

    # Fast path: if the cache already has a complete wheel set, install
    # directly from it and skip rebuilding wheelhouse contents.
    if wheel_cache_dir is not None and wheel_cache_dir.is_dir():
        try:
            pip_install(
                target_dir,
                dependencies,
                find_links=[wheel_cache_dir],
                no_index=True,
            )
            return
        except subprocess.CalledProcessError:
            clear_directory_contents(target_dir)

    build_wheels(
        dependencies,
        wheel_cache_dir=wheel_cache_dir,
        output_wheelhouse_dir=output_wheelhouse_dir,
    )

    link_dirs: list[Path] = []
    if output_wheelhouse_dir is not None:
        link_dirs.append(output_wheelhouse_dir)
    if wheel_cache_dir is not None:
        link_dirs.append(wheel_cache_dir)

    pip_install(
        target_dir,
        dependencies,
        find_links=link_dirs,
        no_index=True,
    )


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
    resolved_dependencies = pin_unversioned_dependencies_from_cache(dependencies, wheel_cache_dir)
    output_image.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="dnat-app-artifact-") as temp_dir:
        root_dir = Path(temp_dir) / "rootfs"
        app_dir = root_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(source_file, app_dir / "application.py")
        (root_dir / "dnat-application.marker").write_text("dnat-application\n", encoding="utf-8")
        install_python_dependencies(
            app_dir / SITE_PACKAGES_DIRNAME,
            resolved_dependencies,
            wheel_cache_dir=wheel_cache_dir,
            output_wheelhouse_dir=output_wheelhouse_dir,
        )

        manifest = {
            "title": args.title,
            "description": args.description,
            "framework": args.framework,
            "dependencies": resolved_dependencies,
            "requestedDependencies": dependencies,
            "entrypoint": "/app/application.py",
            "pythonVersion": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "sourceFileName": source_file.name,
        }
        (app_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        if resolved_dependencies:
            (app_dir / "requirements.lock.txt").write_text("\n".join(resolved_dependencies) + "\n", encoding="utf-8")
            if dependencies != resolved_dependencies:
                (app_dir / "requirements.requested.txt").write_text("\n".join(dependencies) + "\n", encoding="utf-8")
            frozen = freeze_installed_dependencies(app_dir / SITE_PACKAGES_DIRNAME)
            if frozen:
                (app_dir / "requirements.installed.txt").write_text(frozen + "\n", encoding="utf-8")

        dir_size = compute_directory_size(root_dir)
        image_size = max(MIN_IMAGE_BYTES, dir_size * IMAGE_HEADROOM_FACTOR + EXTRA_IMAGE_BYTES)

        if output_image.exists():
            output_image.unlink()

        truncate_bin = resolve_required_binary("truncate", ["/usr/bin/truncate", "/bin/truncate"])
        mkfs_ext4_bin = resolve_required_binary("mkfs.ext4", ["/usr/sbin/mkfs.ext4", "/sbin/mkfs.ext4"])

        subprocess.run([truncate_bin, "-s", str(image_size), str(output_image)], check=True)
        subprocess.run(
            [mkfs_ext4_bin, "-q", "-F", "-d", str(root_dir), str(output_image)],
            check=True,
        )

    print(json.dumps({"artifactPath": str(output_image), "sizeBytes": output_image.stat().st_size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
