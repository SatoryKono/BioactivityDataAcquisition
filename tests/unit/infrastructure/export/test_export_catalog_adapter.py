# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for ExportCatalogAdapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.export import ExportCatalogAdapter


pytestmark = pytest.mark.unit


@pytest.fixture
def adapter() -> ExportCatalogAdapter:
    return ExportCatalogAdapter()


def test_list_tables_returns_discovered_delta_tables(
    adapter: ExportCatalogAdapter,
    tmp_path: Path,
) -> None:
    base_path = tmp_path / "silver"
    (base_path / "chembl" / "default" / "chembl.activity" / "_delta_log").mkdir(
        parents=True
    )

    tables = adapter.list_tables(base_path=base_path, layer="silver")

    assert tables == [
        (
            "chembl.activity",
            str(base_path / "chembl" / "default" / "chembl.activity"),
        )
    ]


def test_list_tables_returns_empty_for_missing_base(
    adapter: ExportCatalogAdapter,
    tmp_path: Path,
) -> None:
    assert adapter.list_tables(base_path=tmp_path / "missing", layer="gold") == []


def test_resolve_table_path_returns_matching_table(
    adapter: ExportCatalogAdapter,
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "gold" / "chembl" / "default" / "chembl.activity"
    (table_path / "_delta_log").mkdir(parents=True)

    resolved = adapter.resolve_table_path(
        base_path=tmp_path / "gold",
        table_name="chembl.activity",
        layer="gold",
    )

    assert resolved == str(table_path.resolve())


def test_resolve_table_path_raises_for_missing_base(
    adapter: ExportCatalogAdapter,
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="Layer path not found"):
        adapter.resolve_table_path(
            base_path=tmp_path / "missing",
            table_name="chembl.activity",
            layer="silver",
        )
