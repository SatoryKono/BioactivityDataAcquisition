# pyright: reportArgumentType=false
"""Unit tests for pure FK quarantine key/column helpers (tech-debt paydown)."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine_keys import (
    CURRENT_FLAG_COLUMNS,
    build_orphan_key_rows,
    require_sql_identifier,
    resolve_present_column,
)

pytestmark = pytest.mark.unit


def test_require_sql_identifier_accepts_safe_names() -> None:
    assert require_sql_identifier("assay_id", "primary_keys") == "assay_id"
    assert require_sql_identifier("_is_current", "current_flag_column") == "_is_current"


def test_require_sql_identifier_rejects_injection_shapes() -> None:
    with pytest.raises(ValueError, match="not a safe SQL identifier"):
        require_sql_identifier("id; drop", "primary_keys")
    with pytest.raises(ValueError, match="not a safe SQL identifier"):
        require_sql_identifier("1bad", "primary_keys")


def test_resolve_present_column_prefers_table_schema() -> None:
    rows = [{"is_current": True}]
    chosen = resolve_present_column(
        rows,
        CURRENT_FLAG_COLUMNS,
        table_columns=frozenset({"_is_current", "assay_id"}),
    )
    assert chosen == "_is_current"


def test_resolve_present_column_falls_back_to_row_keys() -> None:
    rows = [{"is_current": True, "assay_id": "a1"}]
    chosen = resolve_present_column(rows, CURRENT_FLAG_COLUMNS)
    assert chosen == "is_current"


def test_build_orphan_key_rows_dedupes_and_requires_non_null_pk() -> None:
    rows = [
        {"activity_id": "a1", "assay_id": "x"},
        {"activity_id": "a1", "assay_id": "y"},
        {"activity_id": "a2", "assay_id": "z"},
    ]
    keys = build_orphan_key_rows(
        rows,
        ("activity_id",),
        operation="test",
    )
    assert keys == [{"activity_id": "a1"}, {"activity_id": "a2"}]
    with pytest.raises(ValueError, match="non-null primary key"):
        build_orphan_key_rows(
            [{"activity_id": None}],
            ("activity_id",),
            operation="test",
        )
