"""Architecture guard for the canonical column-ordering naming family."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.application import composite as composite_package
from bioetl.application.composite import runtime_wiring_api

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TEST_ROOT = ROOT / "tests"
DEPRECATED_SYMBOLS = ("ColumnOrderer", "ColumnPriorityOrderer")
SRC_ALLOWLIST = frozenset(
    {
        SRC_ROOT / "bioetl" / "application" / "composite" / "column_orderer.py",
        SRC_ROOT
        / "bioetl"
        / "application"
        / "composite"
        / "column_priority_orderer.py",
    }
)
TEST_ALLOWLIST = frozenset(
    {
        TEST_ROOT
        / "unit"
        / "application"
        / "composite"
        / "test_column_priority_orderer.py",
    }
)


def _python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _symbol_hits(root: Path, allowlist: frozenset[Path]) -> list[str]:
    hits: list[str] = []
    for py_file in _python_files(root):
        if py_file in allowlist:
            continue
        source = py_file.read_text(encoding="utf-8")
        for symbol in DEPRECATED_SYMBOLS:
            if symbol in source:
                hits.append(f"{py_file.relative_to(ROOT)} -> {symbol}")
    return hits


@pytest.mark.architecture
def test_no_runtime_imports_of_deprecated_column_ordering_symbols() -> None:
    hits = _symbol_hits(SRC_ROOT / "bioetl", SRC_ALLOWLIST)
    assert hits == [], (
        "Deprecated column-ordering symbols must stay confined to dedicated "
        "compatibility shims:\n" + "\n".join(f"  - {hit}" for hit in hits)
    )


@pytest.mark.architecture
def test_application_and_integration_tests_use_canonical_column_order_service() -> None:
    roots = (
        TEST_ROOT / "unit" / "application" / "composite",
        TEST_ROOT / "integration" / "composite",
    )
    hits: list[str] = []
    for root in roots:
        hits.extend(_symbol_hits(root, TEST_ALLOWLIST))
    assert hits == [], (
        "First-party tests must use ColumnOrderService as the canonical default "
        "surface:\n" + "\n".join(f"  - {hit}" for hit in hits)
    )


@pytest.mark.architecture
def test_public_composite_exports_only_expose_canonical_column_order_service() -> None:
    """Deprecated orderer names must stay out of package/runtime public exports."""
    composite_exports = set(composite_package.__all__)
    runtime_exports = set(runtime_wiring_api.__all__)

    assert "ColumnOrderService" in composite_exports
    assert "ColumnOrderService" in runtime_exports
    assert "ColumnOrderer" not in composite_exports
    assert "ColumnOrderer" not in runtime_exports
    assert "ColumnPriorityOrderer" not in composite_exports
    assert "ColumnPriorityOrderer" not in runtime_exports
