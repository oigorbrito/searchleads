from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Iterable, Mapping


_DIRECT_SEND_MODULES = {"smtplib", "sendgrid", "mailgun"}
_EXPERIMENTAL_DEPENDENCY_MODULES = {
    "followthemoney",
    "nomenklatura",
    "rigour",
    "crawlee",
    "yente",
}
_STRONG_SECRET_PATTERNS = (
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("AWS_ACCESS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GITHUB_CLASSIC_PAT", re.compile(r"\bghp_[A-Za-z0-9]{30,}\b")),
    ("GITHUB_FINE_GRAINED_PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
)
_FORBIDDEN_TRACKED_NAMES = (".env", ".coverage")
_FORBIDDEN_TRACKED_SUFFIXES = (".sqlite", ".sqlite3", ".db", ".pyc")


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


def _top_level_module(name: str | None) -> str:
    return (name or "").split(".", 1)[0].lower()


def _python_source_violations(path: str, content: str) -> tuple[RepositoryHygieneViolation, ...]:
    try:
        tree = ast.parse(content, filename=path)
    except SyntaxError as exc:
        return (
            RepositoryHygieneViolation(
                "PYTHON_SYNTAX_ERROR",
                path,
                f"tracked production source cannot be parsed: line {exc.lineno or 0}",
            ),
        )

    violations: list[RepositoryHygieneViolation] = []
    for node in ast.walk(tree):
        imported: tuple[str, ...] = ()
        if isinstance(node, ast.Import):
            imported = tuple(_top_level_module(alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported = (_top_level_module(node.module),)

        for module in imported:
            if module in _DIRECT_SEND_MODULES:
                violations.append(
                    RepositoryHygieneViolation(
                        "DIRECT_SEND_PATH",
                        path,
                        f"production source imports direct-send module: {module}",
                    )
                )
            if module in _EXPERIMENTAL_DEPENDENCY_MODULES:
                violations.append(
                    RepositoryHygieneViolation(
                        "EXPERIMENTAL_DEPENDENCY_IN_PRODUCTION",
                        path,
                        f"production source imports experimental dependency: {module}",
                    )
                )

        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Attribute) and function.attr in {"sendmail", "send_message"}:
            violations.append(
                RepositoryHygieneViolation(
                    "DIRECT_SEND_PATH",
                    path,
                    f"production source calls direct-send method: {function.attr}",
                )
            )
        if (
            isinstance(function, ast.Attribute)
            and function.attr == "client"
            and isinstance(function.value, ast.Name)
            and function.value.id == "boto3"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and str(node.args[0].value).lower() == "ses"
        ):
            violations.append(
                RepositoryHygieneViolation(
                    "DIRECT_SEND_PATH",
                    path,
                    "production source constructs an AWS SES client",
                )
            )

    return tuple(violations)


def assess_repository_hygiene(
    tracked_files: Mapping[str, str],
) -> RepositoryHygieneAssessment:
    """Fail closed on high-confidence release-candidate hygiene violations."""

    violations: list[RepositoryHygieneViolation] = []
    for raw_path, content in sorted(tracked_files.items()):
        path = PurePosixPath(raw_path).as_posix()
        if path.startswith("src/") and path.endswith(".py"):
            violations.extend(_python_source_violations(path, content))
        for pattern_name, pattern in _STRONG_SECRET_PATTERNS:
            if pattern.search(content):
                violations.append(
                    RepositoryHygieneViolation(
                        "STRONG_SECRET_PATTERN",
                        path,
                        f"tracked text matches secret pattern: {pattern_name}",
                    )
                )
    ordered = tuple(sorted(set(violations), key=lambda item: (item.path, item.code, item.detail)))
    return RepositoryHygieneAssessment(ordered)


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
