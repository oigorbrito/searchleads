from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any


DEFAULT_PACKAGES = (
    "pytest",
    "followthemoney",
    "nomenklatura",
    "crawlee",
    "rigour",
    "python-stdnum",
    "yente",
)


def _git_sha() -> str | None:
    github_sha = os.environ.get("GITHUB_SHA")
    if github_sha:
        return github_sha
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value or None


def _package_versions(packages: tuple[str, ...]) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in packages:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def build_manifest(packages: tuple[str, ...] = DEFAULT_PACKAGES) -> dict[str, Any]:
    return {
        "schema_version": "searchleads_chassis_environment_manifest_v1",
        "repository_sha": _git_sha(),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "runtime": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "dependencies": _package_versions(packages),
        "ci": {
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "github_job": os.environ.get("GITHUB_JOB"),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write the chassis bake-off environment manifest.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--package", action="append", dest="packages")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packages = tuple(args.packages) if args.packages else DEFAULT_PACKAGES
    manifest = build_manifest(packages)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
