from __future__ import annotations

import ast
from pathlib import Path


_FORBIDDEN_MODULES = {
    "searchleads.persistence.identity",
    "searchleads.persistence.ledger",
    "searchleads.persistence.semantic",
    "searchleads.persistence.sqlite",
    "searchleads.persistence.v3",
}
_FORBIDDEN_PUBLIC_NAMES = {"identity", "ledger", "semantic", "sqlite", "v3"}


def _runtime_python_files() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    files: list[Path] = []

    package_root = root / "src" / "searchleads"
    persistence_root = package_root / "persistence"
    for path in package_root.rglob("*.py"):
        if persistence_root not in path.parents:
            files.append(path)

    files.extend((root / "scripts").rglob("*.py"))
    return sorted(files)


def _forbidden_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(
                    alias.name == forbidden or alias.name.startswith(f"{forbidden}.")
                    for forbidden in _FORBIDDEN_MODULES
                ):
                    violations.append(f"line {node.lineno}: import {alias.name}")
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        module = node.module or ""
        if any(module == forbidden or module.startswith(f"{forbidden}.") for forbidden in _FORBIDDEN_MODULES):
            violations.append(f"line {node.lineno}: from {module} import ...")
            continue

        if module == "searchleads.persistence":
            for alias in node.names:
                if alias.name in _FORBIDDEN_PUBLIC_NAMES:
                    violations.append(f"line {node.lineno}: from {module} import {alias.name}")

    return violations


def test_runtime_code_uses_public_persistence_facade() -> None:
    violations: list[str] = []
    root = Path(__file__).resolve().parents[1]

    for path in _runtime_python_files():
        for violation in _forbidden_imports(path):
            violations.append(f"{path.relative_to(root)}: {violation}")

    assert not violations, (
        "Runtime code must import persistence services from searchleads.persistence; "
        "internal persistence modules are implementation details:\n"
        + "\n".join(violations)
    )
