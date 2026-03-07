"""Architecture guards for domain unit-test purity (P2-9)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


DISALLOWED_IMPORT_PREFIXES = (
    "bioetl.application",
    "bioetl.infrastructure",
    "bioetl.composition",
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
