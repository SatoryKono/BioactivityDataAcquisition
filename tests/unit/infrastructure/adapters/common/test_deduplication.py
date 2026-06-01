# mypy: disable-error-code=untyped-decorator

"""Tests for shared adapter deduplication helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest

from tests.async_utils import collect_async_iterator

from bioetl.infrastructure.adapters.common.deduplication import (
    async_iter_deduplicated_records,
    build_record_dedup_key,
    compute_composite_dedup_key,
    deduplicate_preserving_order,
    is_duplicate_record,
    is_new_record,
    iter_deduplicated_records,
    register_record_dedup_key,
)


pytestmark = pytest.mark.unit

def test_deduplicate_preserving_order_keeps_first_occurrence() -> None:
    values = ["P1", "P2", "P1", "P3", "P2"]

    assert deduplicate_preserving_order(values) == ["P1", "P2", "P3"]


def test_build_record_dedup_key_supports_simple_and_composite_keys() -> None:
    record = {"id": "A1", "left": "L", "right": "R"}

    assert build_record_dedup_key(record, "id") == "A1"
    assert (
        build_record_dedup_key(record, "id", composite_fields=("left", "right"))
        == "L|R"
    )
    assert (
        build_record_dedup_key(
            {"left": None, "right": ""},
            "id",
            composite_fields=("left", "right"),
        )
        is None
    )


def test_compute_composite_dedup_key_preserves_field_order_and_missing_values() -> None:
    key = compute_composite_dedup_key({"left": "A", "right": None}, ("left", "right"))

    assert key == "A|"


def test_register_record_dedup_key_logs_and_records_metrics_for_duplicates() -> None:
    seen_keys = {"CHEMBL1"}
    logger = MagicMock()
    metrics = MagicMock()

    status = register_record_dedup_key(
        record={"assay_chembl_id": "CHEMBL1"},
        seen_keys=seen_keys,
        primary_field="assay_chembl_id",
        entity_type="assay",
        logger=logger,
        metrics=metrics,
        log_context={"filter_field": "assay_id"},
    )

    assert status == "duplicate"
    logger.debug.assert_called_once_with(
        "skipping_duplicate_record",
        entity_type="assay",
        pk_field="assay_chembl_id",
        record_id="CHEMBL1",
        filter_field="assay_id",
    )
    metrics.record_dropped_duplicates.assert_called_once_with("assay")


def test_register_record_dedup_key_supports_custom_composite_builder() -> None:
    seen_keys: set[str] = set()

    def build_key(record: dict[str, object], fields: tuple[str, ...]) -> str:
        return "::".join(str(record.get(field, "")) for field in fields)

    status = register_record_dedup_key(
        record={"left": "A", "right": "B"},
        seen_keys=seen_keys,
        primary_field="left",
        composite_fields=("left", "right"),
        composite_key_builder=build_key,
    )

    assert status == "new"
    assert seen_keys == {"A::B"}


def test_duplicate_and_new_record_predicates_reflect_registration_status() -> None:
    seen_keys: set[str] = set()

    assert (
        is_new_record(
            record={"record_id": "R1"},
            seen_keys=seen_keys,
            primary_field="record_id",
        )
        is True
    )
    assert (
        is_duplicate_record(
            record={"record_id": "R1"},
            seen_keys=seen_keys,
            primary_field="record_id",
        )
        is True
    )


def test_register_record_dedup_key_marks_missing_keys_explicitly() -> None:
    assert (
        register_record_dedup_key(
            record={"left": None, "right": ""},
            seen_keys=set(),
            primary_field="left",
            composite_fields=("left", "right"),
        )
        == "missing_key"
    )


def test_iter_deduplicated_records_skips_duplicates_but_keeps_missing_keys() -> None:
    logger = MagicMock()
    metrics = MagicMock()

    records = list(
        iter_deduplicated_records(
            [
                {"record_id": "R1"},
                {"record_id": "R1"},
                {"other_field": "no-key"},
            ],
            seen_keys=set(),
            primary_field="record_id",
            entity_type="assay",
            logger=logger,
            metrics=metrics,
        )
    )

    assert records == [{"record_id": "R1"}, {"other_field": "no-key"}]
    logger.debug.assert_called_once()
    metrics.record_dropped_duplicates.assert_called_once_with("assay")


@pytest.mark.asyncio
async def test_async_iter_deduplicated_records_skips_duplicates_but_keeps_missing_keys() -> (
    None
):
    logger = MagicMock()
    metrics = MagicMock()

    async def _records() -> AsyncIterator[dict[str, str]]:
        yield {"record_id": "R1"}
        yield {"record_id": "R1"}
        yield {"other_field": "no-key"}

    records = await collect_async_iterator(
        async_iter_deduplicated_records(
            _records(),
            seen_keys=set(),
            primary_field="record_id",
            entity_type="assay",
            logger=logger,
            metrics=metrics,
        )
    )

    assert records == [{"record_id": "R1"}, {"other_field": "no-key"}]
    logger.debug.assert_called_once()
    metrics.record_dropped_duplicates.assert_called_once_with("assay")
