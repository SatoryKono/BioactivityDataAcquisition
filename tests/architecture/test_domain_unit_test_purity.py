"""Architecture guards for domain purity and domain-unit test purity."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


DISALLOWED_IMPORT_PREFIXES = (
    "bioetl.application",
    "bioetl.infrastructure",
    "bioetl.composition",
)

DISALLOWED_RUNTIME_SEAMS: tuple[tuple[str, str], ...] = (
    ("open", "filesystem I/O via open()"),
    ("read_text", "filesystem I/O via Path.read_text()"),
    ("write_text", "filesystem I/O via Path.write_text()"),
    ("yaml", "YAML parsing/serialization"),
    ("datetime.now", "wall-clock time via datetime.now()"),
    ("datetime.utcnow", "wall-clock time via datetime.utcnow()"),
    ("time.time", "wall-clock time via time.time()"),
)


def _collect_disallowed_imports(file_path: Path) -> list[str]:
    violations: list[str] = []
    content = file_path.read_text(encoding="utf-8")

    for prefix in DISALLOWED_IMPORT_PREFIXES:
        pattern = re.compile(
            rf"^\s*(?:from|import)\s+{re.escape(prefix)}\b", re.MULTILINE
        )
        if pattern.search(content):
            violations.append(f"{file_path}: imports {prefix}")

    return violations


def _attribute_path(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _attribute_path(node.value)
        return None if parent is None else f"{parent}.{node.attr}"
    return None


def _collect_disallowed_runtime_seams(file_path: Path) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "yaml":
                    violations.append(f"{file_path}:{node.lineno}: uses YAML parsing/serialization")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "yaml":
                violations.append(f"{file_path}:{node.lineno}: uses YAML parsing/serialization")
        elif isinstance(node, ast.Call):
            target = _attribute_path(node.func)
            if target == "open":
                violations.append(f"{file_path}:{node.lineno}: uses filesystem I/O via open()")
            elif target == "yaml.safe_load" or target == "yaml.safe_dump" or target == "yaml.dump":
                violations.append(f"{file_path}:{node.lineno}: uses YAML parsing/serialization")
            elif target == "datetime.now":
                violations.append(f"{file_path}:{node.lineno}: uses wall-clock time via datetime.now()")
            elif target == "datetime.utcnow":
                violations.append(f"{file_path}:{node.lineno}: uses wall-clock time via datetime.utcnow()")
            elif target == "time.time":
                violations.append(f"{file_path}:{node.lineno}: uses wall-clock time via time.time()")
            elif target is not None and target.endswith(".read_text"):
                violations.append(
                    f"{file_path}:{node.lineno}: uses filesystem I/O via Path.read_text()"
                )
            elif target is not None and target.endswith(".write_text"):
                violations.append(
                    f"{file_path}:{node.lineno}: uses filesystem I/O via Path.write_text()"
                )

    return violations


def test_domain_unit_tests_do_not_import_orchestration_layers(
    project_root: Path,
) -> None:
    """Domain unit tests must stay focused on domain invariants only."""
    domain_tests_path = project_root / "tests" / "unit" / "domain"
    if not domain_tests_path.exists():
        pytest.skip("tests/unit/domain not found")

    violations: list[str] = []
    for py_file in sorted(domain_tests_path.rglob("test_*.py")):
        violations.extend(_collect_disallowed_imports(py_file))

    assert not violations, (
        "Domain unit tests import non-domain layers (application/"
        "infrastructure/composition):\n" + "\n".join(violations)
    )


@pytest.mark.parametrize(
    ("root_path", "file_glob", "surface_label"),
    (
        ("src/bioetl/domain", "*.py", "Domain runtime modules"),
        ("tests/unit/domain", "test_*.py", "Domain unit tests"),
    ),
)
def test_domain_surfaces_do_not_use_filesystem_or_wall_clock_seams(
    project_root: Path,
    root_path: str,
    file_glob: str,
    surface_label: str,
) -> None:
    """Domain surfaces must stay pure and deterministic."""
    root = project_root / root_path
    if not root.exists():
        pytest.skip(f"{root_path} not found")

    violations: list[str] = []
    for py_file in sorted(root.rglob(file_glob)):
        violations.extend(_collect_disallowed_runtime_seams(py_file))

    assert not violations, (
        f"{surface_label} use forbidden filesystem/time seams:\n"
        + "\n".join(violations)
        + "\n\nForbidden seams: "
        + ", ".join(label for label, _reason in DISALLOWED_RUNTIME_SEAMS)
    )
