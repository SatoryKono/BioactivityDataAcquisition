# pyright: reportArgumentType=false
"""Current-run scoping for limited-extract delete_orphans."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    filter_source_rows_to_current_run,
)

pytestmark = pytest.mark.unit


def test_all_current_scope_keeps_every_row() -> None:
    rows = [
        {"assay_id": "A1", "_run_id": "run-a"},
        {"assay_id": "A2", "_run_id": "run-b"},
    ]
    scoped, disposition = filter_source_rows_to_current_run(
        rows, source_scope="all_current", source_run_ids=("run-a",)
    )
    assert disposition == "all_current"
    assert scoped == rows


def test_current_run_scope_keeps_matching_run_ids() -> None:
    rows = [
        {"assay_id": "A1", "_run_id": "run-a"},
        {"assay_id": "A2", "_run_id": "run-b"},
        {"assay_id": "A3", "_run_id": "run-a"},
    ]
    scoped, disposition = filter_source_rows_to_current_run(
        rows, source_scope="current_run", source_run_ids=("run-a",)
    )
    assert disposition == "current_run"
    assert [row["assay_id"] for row in scoped] == ["A1", "A3"]


def test_current_run_scope_blocks_when_identity_is_missing() -> None:
    rows = [{"assay_id": "A1"}]
    scoped, disposition = filter_source_rows_to_current_run(
        rows, source_scope="current_run", source_run_ids=("run-a",)
    )
    assert disposition == "blocked"
    assert scoped == []
