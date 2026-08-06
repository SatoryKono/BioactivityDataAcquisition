"""Unit tests for domain export identity helpers (ARCH-REF-R2 / #7732)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.value_objects.export_identity import (
    dataset_bundle_id,
    format_utc,
)

pytestmark = pytest.mark.unit


def test_dataset_bundle_id_is_deterministic() -> None:
    first = dataset_bundle_id(
        table_name="activity",
        layer="gold",
        export_format="parquet",
        row_count=10,
        columns=("a", "b"),
        providers=("chembl",),
        data_sha256="abc",
    )
    second = dataset_bundle_id(
        table_name="activity",
        layer="gold",
        export_format="parquet",
        row_count=10,
        columns=("a", "b"),
        providers=("chembl",),
        data_sha256="abc",
    )
    assert first == second
    assert first.startswith("bioetl-export-")


def test_dataset_bundle_id_changes_with_payload() -> None:
    base = dataset_bundle_id(
        table_name="activity",
        layer="gold",
        export_format="parquet",
        row_count=10,
        columns=("a", "b"),
        providers=("chembl",),
        data_sha256="abc",
    )
    other = dataset_bundle_id(
        table_name="activity",
        layer="gold",
        export_format="parquet",
        row_count=11,
        columns=("a", "b"),
        providers=("chembl",),
        data_sha256="abc",
    )
    assert base != other


def test_format_utc_second_granularity() -> None:
    value = datetime(2026, 8, 5, 12, 0, 0, 123456, tzinfo=UTC)
    assert format_utc(value) == "2026-08-05T12:00:00Z"
