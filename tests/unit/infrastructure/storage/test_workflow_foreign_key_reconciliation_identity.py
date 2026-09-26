"""Unit tests for deterministic FK-reconciliation quarantine identities."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import pytest

from bioetl.domain.ports import ForeignKeyReconciliationRequest
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_identity import (
    FOREIGN_KEY_ORPHAN_ERROR_CODE,
    FOREIGN_KEY_ORPHAN_GOLD_ERROR_CODE,
    build_quarantine_batch_id,
    canonical_reconciliation_value,
    coerce_optional_run_id,
    orphan_error_code,
)


pytestmark = pytest.mark.unit


def _request(layer: str = "silver") -> ForeignKeyReconciliationRequest:
    return ForeignKeyReconciliationRequest(
        source_table="source_records",
        reference_table="reference_records",
        source_key="record_id",
        reference_key="record_id",
        primary_keys=("record_id",),
        workflow_name="reconcile_records",
        source_layer=layer,  # type: ignore[arg-type]
        reference_layer=layer,  # type: ignore[arg-type]
        mutation_layer=layer,  # type: ignore[arg-type]
    )


def test_canonical_reconciliation_value_normalizes_nested_identity_inputs() -> None:
    identifier = UUID("12345678-1234-5678-1234-567812345678")
    value = {
        "z": (float("nan"), date(2026, 8, 9)),
        "a": {2: datetime(2026, 8, 9, 12, 30), "id": identifier},
    }

    normalized = canonical_reconciliation_value(value)

    assert list(normalized) == ["a", "z"]
    assert normalized == {
        "a": {
            "2": "2026-08-09 12:30:00",
            "id": "12345678-1234-5678-1234-567812345678",
        },
        "z": ["NaN", "2026-08-09"],
    }


def test_quarantine_batch_id_is_stable_for_equivalent_mapping_order() -> None:
    request = _request()

    first = build_quarantine_batch_id(
        request,
        orphan_rows=[{"record_id": 1, "payload": {"b": 2, "a": 1}}],
    )
    second = build_quarantine_batch_id(
        request,
        orphan_rows=[{"payload": {"a": 1, "b": 2}, "record_id": 1}],
    )

    assert first == second


def test_run_id_coercion_and_layer_specific_error_codes() -> None:
    run_id = "12345678-1234-5678-1234-567812345678"

    assert str(coerce_optional_run_id(run_id)) == run_id
    assert coerce_optional_run_id(None) is None
    assert coerce_optional_run_id("not-a-uuid") is None
    assert orphan_error_code(_request()) == FOREIGN_KEY_ORPHAN_ERROR_CODE
    assert orphan_error_code(_request("gold")) == FOREIGN_KEY_ORPHAN_GOLD_ERROR_CODE
