#!/usr/bin/env python3
"""Pre-merge gate for naming/package consistency rules.

Rules:
1) strict suffix-policy: delegated to ``scripts/engineering/qa/naming_audit.py --check``.
2) factory-only-in-composition: no ``Factory`` classes or ``*factory*.py`` modules
   outside ``src/bioetl/composition``.
3) canonical role subpackage names: ``contracts/mappers/services/facades`` only
   (singular forms are forbidden).
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SRC_ROOT = Path("src/bioetl")
CANONICAL_NAMING_AUDIT_PATH = Path("scripts/engineering/qa/naming_audit.py")
FORBIDDEN_FACTORY_LAYERS = (
    SRC_ROOT / "application",
    SRC_ROOT / "infrastructure",
    SRC_ROOT / "domain",
    SRC_ROOT / "interfaces",
)
SINGULAR_ROLE_TO_CANONICAL = {
    "contract": "contracts",
    "mapper": "mappers",
    "service": "services",
    "facade": "facades",
}
ALLOWED_FACTORY_FACADES = {
    "src/bioetl/application/core/wiring/factory.py",
}


@dataclass(frozen=True)
class Violation:
    """Single policy violation."""

    rule: str
    location: str
    details: str


def _run_suffix_policy_check(repo_root: Path) -> list[Violation]:
    script = repo_root / CANONICAL_NAMING_AUDIT_PATH
    docs_skip_path = repo_root / "docs" / "__naming_gate_skip__"
    if not script.exists():
        return [
            Violation(
                rule="suffix-policy",
                location=CANONICAL_NAMING_AUDIT_PATH.as_posix(),
                details=f"{CANONICAL_NAMING_AUDIT_PATH.as_posix()} not found",
            )
        ]
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--check",
            "--src",
            str(repo_root / SRC_ROOT),
            "--docs",
            str(docs_skip_path),
            "--configs",
            str(repo_root / "configs"),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if result.returncode == 0:
        return []
    output = (result.stdout + "\n" + result.stderr).strip()
    preview = "\n".join(output.splitlines()[:30])
    return [
        Violation(
            rule="suffix-policy",
            location="scripts/engineering/qa/naming_audit.py --check",
            details=preview or "naming_audit returned non-zero exit code",
        )
    ]


def _factory_module_violation(py_file: Path, *, repo_root: Path) -> Violation | None:
    if py_file.name not in {"factory.py"} and not py_file.name.endswith("_factory.py"):
        return None

    rel = py_file.relative_to(repo_root).as_posix()
    if rel in ALLOWED_FACTORY_FACADES:
        return None
    return Violation(
        rule="factory-only-in-composition",
        location=rel,
        details="Factory module is outside src/bioetl/composition",
    )


def _load_python_ast(py_file: Path) -> ast.AST | None:
    try:
        return ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _factory_class_violations(py_file: Path, *, repo_root: Path) -> list[Violation]:
    tree = _load_python_ast(py_file)
    if tree is None:
        return []

    rel = py_file.relative_to(repo_root).as_posix()
    return [
        Violation(
            rule="factory-only-in-composition",
            location=f"{rel}:{node.lineno}",
            details=f"class {node.name} must live in composition layer",
        )
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.ClassDef)
            and node.name.endswith("Factory")
            and not node.name.startswith("_")
        )
    ]


def _violations_for_forbidden_factory_file(
    py_file: Path, *, repo_root: Path
) -> list[Violation]:
    violations: list[Violation] = []
    module_violation = _factory_module_violation(py_file, repo_root=repo_root)
    if module_violation is not None:
        violations.append(module_violation)
    violations.extend(_factory_class_violations(py_file, repo_root=repo_root))
    return violations


def _factory_violations(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []

    for layer in FORBIDDEN_FACTORY_LAYERS:
        layer_path = repo_root / layer
        if not layer_path.exists():
            continue
        for py_file in layer_path.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            violations.extend(
                _violations_for_forbidden_factory_file(py_file, repo_root=repo_root)
            )
    return violations


def _package_template_violations(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for directory in (repo_root / SRC_ROOT).rglob("*"):
        if not directory.is_dir() or "__pycache__" in directory.parts:
            continue
        singular_name = SINGULAR_ROLE_TO_CANONICAL.get(directory.name)
        if singular_name is None:
            continue
        rel = directory.relative_to(repo_root).as_posix()
        violations.append(
            Violation(
                rule="subpackage-template",
                location=rel,
                details=(
                    f"Use canonical subpackage name '{singular_name}' "
                    f"instead of '{directory.name}'"
                ),
            )
        )
    return violations


def run_checks(repo_root: Path) -> list[Violation]:
    """Run all consistency checks and return merged violations."""
    violations: list[Violation] = []
    violations.extend(_run_suffix_policy_check(repo_root))
    violations.extend(_factory_violations(repo_root))
    violations.extend(_package_template_violations(repo_root))
    return violations


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check naming/package consistency pre-merge rules."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when violations are found (CI mode).",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    _ = _parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    violations = run_checks(repo_root)

    if not violations:
        print(
            "Naming/package consistency: OK "
            "(suffix-policy, factory-only-in-composition, subpackage-template)"
        )
        return 0

    print(f"Naming/package consistency: {len(violations)} violation(s) found")
    for item in violations:
        print(f"  - [{item.rule}] {item.location}: {item.details}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
