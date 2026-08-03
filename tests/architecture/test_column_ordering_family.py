# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
SRC_ALLOWLIST: frozenset[Path] = frozenset()
TEST_ALLOWLIST: frozenset[Path] = frozenset()


def _symbol_hits_from_cache(
    content_cache: dict[Path, str],
    *,
    root: Path,
    allowlist: frozenset[Path],
) -> list[str]:
    hits: list[str] = []
    for py_file, source in sorted(content_cache.items()):
        if not py_file.is_relative_to(root):
            continue
        if py_file in allowlist:
            continue
        for symbol in DEPRECATED_SYMBOLS:
            if symbol in source:
                hits.append(f"{py_file.relative_to(ROOT)} -> {symbol}")
    return hits


@pytest.mark.architecture
def test_no_runtime_imports_of_deprecated_column_ordering_symbols(
    source_content_cache: dict[Path, str],
) -> None:
    hits = _symbol_hits_from_cache(
        source_content_cache,
        root=SRC_ROOT / "bioetl",
        allowlist=SRC_ALLOWLIST,
    )
    assert hits == [], (
        "Deprecated column-ordering symbols must stay removed from runtime src:\n"
        + "\n".join(f"  - {hit}" for hit in hits)
    )


@pytest.mark.architecture
def test_application_and_integration_tests_use_canonical_column_order_service(
    test_content_cache: dict[Path, str],
) -> None:
    roots = (
        TEST_ROOT / "unit" / "application" / "composite",
        TEST_ROOT / "integration" / "composite",
    )
    hits: list[str] = []
    for root in roots:
        hits.extend(
            _symbol_hits_from_cache(
                test_content_cache,
                root=root,
                allowlist=frozenset(),
            )
        )
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


SRC_ALLOWLIST = frozenset()
