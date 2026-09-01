from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from searchleads.release_hygiene import assess_repository_hygiene, assess_tracked_filenames


def _tracked_paths() -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return tuple(
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    )


def _tracked_text(paths: tuple[str, ...]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for relative in paths:
        path = Path(relative)
        try:
            payload[relative] = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return payload


def main() -> int:
    paths = _tracked_paths()
    filename_assessment = assess_tracked_filenames(paths)
    content_assessment = assess_repository_hygiene(_tracked_text(paths))
    violations = filename_assessment.violations + content_assessment.violations
    if violations:
        for violation in violations:
            print(f"{violation.code}: {violation.path}: {violation.detail}")
        return 1
    print("RC_HYGIENE_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
