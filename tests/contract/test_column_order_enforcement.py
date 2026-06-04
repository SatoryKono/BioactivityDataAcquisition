"""Contract tests for canonical column ordering used before Gold writes."""

from __future__ import annotations

import pytest

from bioetl.domain.schemas.column_order import (
    DQ_FIELDS_SUFFIX,
    SYSTEM_FIELDS_PREFIX,
    canonical_column_order,
)
from bioetl.infrastructure.storage.gold.io_preparation import _prepare_gold_merged_table

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def test_canonical_column_order_matches_gold_preparation_contract() -> None:
    """Gold IO preparation must reorder columns via canonical_column_order."""
    records = [
        {
            "entity_id": "entity:1",
            "content_hash": "b" * 64,
            "_run_id": "00000000-0000-4000-8000-000000000001",
            "_run_type": "incremental",
            "_ingestion_ts": "2026-01-01T00:00:00+00:00",
            "_index": 0,
            "_dq_warn": False,
            "activity_id": "A1",
        }
    ]
    prepared = _prepare_gold_merged_table(
        records=records,
        primary_keys=None,
        preserve_column_order=False,
    )
    assert prepared.column_names == canonical_column_order(list(prepared.column_names))
    assert prepared.column_names[:2] == list(SYSTEM_FIELDS_PREFIX[:2])
    assert prepared.column_names[-1] in DQ_FIELDS_SUFFIX


def test_canonical_column_order_rejects_dq_prefix_in_business_block() -> None:
    """DQ suffix fields must not appear before business columns when reordered."""
    columns = ["entity_id", "content_hash", "z_field", "_dq_error"]
    ordered = canonical_column_order(columns)
    assert ordered.index("_dq_error") > ordered.index("z_field")


def test_canonical_column_order_places_lookup_fields_before_business_columns() -> None:
    columns = (
        "_lookup_method",
        "z_field",
        "entity_id",
        "_original_id",
        "content_hash",
        "a_field",
        "_dq_warn",
    )

    ordered = canonical_column_order(columns)

    assert ordered == [
        "entity_id",
        "content_hash",
        "_lookup_method",
        "_original_id",
        "a_field",
        "z_field",
        "_dq_warn",
    ]


def test_canonical_column_order_deduplicates_duplicate_inputs() -> None:
    ordered = canonical_column_order(
        ["entity_id", "entity_id", "_dq_error", "name", "name", "content_hash"]
    )
    assert ordered == ["entity_id", "content_hash", "name", "_dq_error"]
