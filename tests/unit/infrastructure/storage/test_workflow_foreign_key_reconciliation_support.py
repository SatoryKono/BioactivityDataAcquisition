# pyright: reportArgumentType=false
"""Unit tests for FK reconciliation support helpers (#7996)."""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, Mock

import pytest

from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    normalize_value,
    partition_source_rows,
    reference_value_set,
)


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_mutation_completion_retains_quarantine_receipt_and_debug_rows(
    monkeypatch,
):
    from bioetl.infrastructure.storage import (
        workflow_foreign_key_reconciliation_support as support,
    )
    from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine import (
        ReconciliationMutationSummary,
    )

    summary = ReconciliationMutationSummary(
        mutation_mode="silver_rewrite",
        quarantine_batch_id="batch",
        quarantine_rows_written=1,
        quarantine_error_code="orphan_foreign_key",
    )
    mutate = AsyncMock(return_value=summary)
    monkeypatch.setattr(support, "apply_reconciliation_mutation", mutate)
    host = Mock()
    request = _request()
    retained = [{"activity_id": "kept", "assay_id": "known"}]
    orphans = [{"activity_id": "orphan", "assay_id": "missing"}]
    result = await support.complete_with_mutation(
        host,
        request,
        scanned_rows=2,
        retained_rows_count=1,
        orphan_rows_deleted=1,
        retained_rows=retained,
        orphan_rows=orphans,
    )
    mutate.assert_awaited_once_with(host, request, orphan_rows=orphans)
    assert result.mutated and not result.would_mutate
    assert (result.scanned_rows, result.retained_rows, result.orphan_rows_deleted) == (
        2,
        1,
        1,
    )
    assert result.quarantine_batch_id == "batch" and result.quarantine_rows_written == 1
    assert result.quarantine_error_code == "orphan_foreign_key"
    host._write_debug_artifacts.assert_called_once_with(
        request, result, retained_rows=retained, orphan_rows=orphans
    )


def _request(**overrides: object) -> ForeignKeyReconciliationRequest:
    payload: dict[str, object] = {
        "source_table": "silver.activity",
        "reference_table": "silver.assay",
        "source_key": "assay_id",
        "reference_key": "assay_id",
        "primary_keys": ("activity_id",),
        "nulls_equal": False,
    }
    payload.update(overrides)
    return ForeignKeyReconciliationRequest(**payload)  # type: ignore[arg-type]


def test_normalize_value_keeps_string_and_number_distinct() -> None:
    assert normalize_value(5) == normalize_value(5.0)
    assert normalize_value("5") != normalize_value(5)
    assert normalize_value(True) != normalize_value(1)
    assert normalize_value(None) is None
    assert normalize_value(float("nan")) is None
    assert normalize_value("  ") is None
    assert normalize_value(math.nan) is None


def test_partition_retains_null_foreign_keys_even_when_nulls_equal() -> None:
    request = _request(nulls_equal=True)
    source_rows = [
        {"activity_id": "a1", "assay_id": None},
        {"activity_id": "a2", "assay_id": ""},
        {"activity_id": "a3", "assay_id": "missing"},
        {"activity_id": "a4", "assay_id": "ok"},
    ]
    reference_values = reference_value_set(
        request,
        [{"assay_id": "ok"}],
    )
    retained, orphans = partition_source_rows(
        request,
        source_rows=source_rows,
        reference_values=reference_values,
    )
    retained_ids = {row["activity_id"] for row in retained}
    orphan_ids = {row["activity_id"] for row in orphans}
    assert retained_ids == {"a1", "a2", "a4"}
    assert orphan_ids == {"a3"}


def test_partition_matches_integral_float_keys() -> None:
    request = _request(source_key="target_id", reference_key="target_id")
    source_rows = [
        {"activity_id": "a1", "target_id": 5},
        {"activity_id": "a2", "target_id": 5.0},
        {"activity_id": "a3", "target_id": "5"},
    ]
    reference_values = reference_value_set(
        request,
        [{"target_id": 5.0}],
    )
    retained, orphans = partition_source_rows(
        request,
        source_rows=source_rows,
        reference_values=reference_values,
    )
    assert {row["activity_id"] for row in retained} == {"a1", "a2"}
    assert {row["activity_id"] for row in orphans} == {"a3"}
