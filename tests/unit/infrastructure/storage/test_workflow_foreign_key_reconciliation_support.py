# pyright: reportArgumentType=false
"""Unit tests for FK reconciliation support helpers (#7996)."""

from __future__ import annotations

import math

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


@pytest.mark.parametrize("flag", ["_is_current", "is_current"])
def test_current_rows_keep_only_explicit_true_flags(flag):
    from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
        filter_current_rows,
    )

    values = [True, False, None, 1, 0, 1.0, 2.0, " true ", "false", "yes", object()]
    rows = [{"id": index, flag: value} for index, value in enumerate(values)]
    assert [
        row["id"] for row in filter_current_rows(rows, current_only=True, layer="gold")
    ] == [0, 3, 5, 7, 9]
    assert filter_current_rows(rows, current_only=False, layer="gold") is rows
    without_flags = [{"id": 1}]
    assert (
        filter_current_rows(without_flags, current_only=True, layer="silver")
        is without_flags
    )
    assert filter_current_rows([], current_only=True, layer="gold") == []


@pytest.mark.asyncio
async def test_mutation_completion_preserves_quarantine_result_and_debug_rows(
    monkeypatch,
):
    from unittest.mock import AsyncMock, MagicMock
    from bioetl.infrastructure.storage import (
        workflow_foreign_key_reconciliation_support as support,
    )
    from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_quarantine import (
        ReconciliationMutationSummary,
    )

    host = MagicMock()
    request = _request()
    retained = [{"activity_id": "a1", "assay_id": "valid"}]
    orphans = [{"activity_id": "a2", "assay_id": "missing"}]
    mutate = AsyncMock(
        return_value=ReconciliationMutationSummary(
            mutation_mode="silver_rewrite",
            quarantine_batch_id="batch-1",
            quarantine_rows_written=1,
            quarantine_error_code="FILTERED_OUT_SILVER",
        )
    )
    monkeypatch.setattr(support, "apply_reconciliation_mutation", mutate)
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
    assert result.mutated is True
    assert result.mutation_mode == "silver_rewrite"
    assert result.quarantine_rows_written == 1
    assert result.quarantine_batch_id == "batch-1"
    assert result.quarantine_error_code == "FILTERED_OUT_SILVER"
    host._write_debug_artifacts.assert_called_once_with(
        request, result, retained_rows=retained, orphan_rows=orphans
    )
    assert host._log.call_args.kwargs["scanned_rows"] == 2
