from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Iterable, Mapping


_SEND_TOKENS = (
    "import smtplib",
    "from smtplib",
    "sendgrid",
    "mailgun",
    "sendmail(",
    "send_message(",
    "boto3.client(\"ses\"",
    "boto3.client('ses'",
)

_EXPERIMENTAL_DEPENDENCY_TOKENS = (
    "followthemoney",
    "nomenklatura",
    "rigour",
    "crawlee",
    "yente",
)

_STRONG_SECRET_PATTERNS = (
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("AWS_ACCESS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GITHUB_CLASSIC_PAT", re.compile(r"\bghp_[A-Za-z0-9]{30,}\b")),
    ("GITHUB_FINE_GRAINED_PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
)

_FORBIDDEN_TRACKED_NAMES = (
    ".env",
    ".coverage",
)

_FORBIDDEN_TRACKED_SUFFIXES = (
    ".sqlite",
    ".sqlite3",
    ".db",
    ".pyc",
)


@dataclass(frozen=True, slots=True)
class RepositoryHygieneViolation:
    code: str
    path: str
    detail: str

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.path.strip() or not self.detail.strip():
            raise ValueError("hygiene violation fields must be non-blank")


@dataclass(frozen=True, slots=True)
class RepositoryHygieneAssessment:
    violations: tuple[RepositoryHygieneViolation, ...]

    @property
    def ready(self) -> bool:
        return not self.violations


def assess_repository_hygiene(
    tracked_files: Mapping[str, str],
) -> RepositoryHygieneAssessment:
    """Fail closed on high-confidence RC hygiene violations.

    `tracked_files` maps repository-relative POSIX paths to UTF-8 text. Binary files
    should be omitted by the caller; their filenames are still checked separately by
    `assess_tracked_filenames`.
    """

    violations: list[RepositoryHygieneViolation] = []
    for path, content in sorted(tracked_files.items()):
        normalized = PurePosixPath(path).as_posix()
        if normalized.startswith("src/"):
            lowered = content.lower()
            for token in _SEND_TOKENS:
                if token.lower() in lowered:
                    violations.append(
                        RepositoryHygieneViolation(
                            "DIRECT_SEND_PATH",
                            normalized,
                            f"production source contains direct-send token: {token}",
                        )
                    )
            for token in _EXPERIMENTAL_DEPENDENCY_TOKENS:
                if re.search(rf"(^|[^a-z0-9_]){re.escape(token)}([^a-z0-9_]|$)", lowered):
                    violations.append(
                        RepositoryHygieneViolation(
                            "EXPERIMENTAL_DEPENDENCY_IN_PRODUCTION",
                            normalized,
                            f"production source references experimental dependency: {token}",
                        )
                    )
        for pattern_name, pattern in _STRONG_SECRET_PATTERNS:
            if pattern.search(content):
                violations.append(
                    RepositoryHygieneViolation(
                        "STRONG_SECRET_PATTERN",
                        normalized,
                        f"tracked text matches secret pattern: {pattern_name}",
                    )
                )
    return RepositoryHygieneAssessment(tuple(violations))


def assess_tracked_filenames(paths: Iterable[str]) -> RepositoryHygieneAssessment:
    violations: list[RepositoryHygieneViolation] = []
    for raw_path in sorted(set(paths)):
        path = PurePosixPath(raw_path).as_posix()
        name = PurePosixPath(path).name
        if name in _FORBIDDEN_TRACKED_NAMES or path.endswith(_FORBIDDEN_TRACKED_SUFFIXES):
            violations.append(
                RepositoryHygieneViolation(
                    "FORBIDDEN_TRACKED_ARTIFACT",
                    path,
                    "local runtime/coverage artifact must not be versioned",
                )
            )
        if "/__pycache__/" in f"/{path}/" or path.startswith("__pycache__/"):
            violations.append(
                RepositoryHygieneViolation(
                    "FORBIDDEN_TRACKED_ARTIFACT",
                    path,
                    "Python cache artifact must not be versioned",
                )
            )
    return RepositoryHygieneAssessment(tuple(violations))


__all__ = [
    "RepositoryHygieneAssessment",
    "RepositoryHygieneViolation",
    "assess_repository_hygiene",
    "assess_tracked_filenames",
]
