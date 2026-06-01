"""Tests for ChEMBL target protein-classification data-source wrappers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from bioetl.composition.providers._chembl_target_protein_classification_data_source import (
    TargetProteinClassificationDataSource,
    TargetProteinClassificationEnrichedTargetDataSource,
)
from bioetl.domain.types import JsonDict


pytestmark = pytest.mark.unit


class _FakeChEMBLDataSource:
    provider_name = "chembl"

    def __init__(self) -> None:
        self.rows: dict[str, list[JsonDict]] = {
            "target": [
                {
                    "target_chembl_id": "CHEMBL_T1",
                    "target_components": [{"component_id": 10}],
                }
            ],
            "target_component": [
                {
                    "component_id": 10,
                    "protein_classifications": [{"protein_classification_id": 3}],
                    "targets": [{"target_chembl_id": "CHEMBL_T1"}],
                }
            ],
            "protein_class": [
                {
                    "protein_class_id": 1,
                    "parent_id": 0,
                    "class_level": 1,
                    "pref_name": "Enzyme",
                    "protein_class_desc": "Root",
                },
                {
                    "protein_class_id": 2,
                    "parent_id": 1,
                    "class_level": 2,
                    "pref_name": "Kinase",
                    "protein_class_desc": "Branch",
                },
                {
                    "protein_class_id": 3,
                    "parent_id": 2,
                    "class_level": 3,
                    "pref_name": "Serine/threonine kinase",
                    "protein_class_desc": "Leaf",
                },
            ],
        }

    async def __aenter__(self) -> _FakeChEMBLDataSource:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def aclose(self) -> None:
        return None

    async def health_check(self) -> str:
        return "healthy"

    def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        _ = query, offset
        return self._yield_rows(entity_type, filter_ids, filter_field, limit)

    def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        return self._yield_rows(entity_type, filter_ids, filter_field, limit)

    def fetch_multi_filtered(
        self,
        entity_type: str,
        filters: dict[str, list[str]],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        _ = filters
        return self._yield_rows(entity_type, None, None, limit)

    def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        _ = fallback_mapping
        return self._yield_rows(entity_type, filter_ids, filter_field, limit)

    async def _yield_rows(
        self,
        entity_type: str,
        filter_ids: list[str] | None,
        filter_field: str | None,
        limit: int | None,
    ) -> AsyncIterator[JsonDict]:
        emitted = 0
        for row in self.rows[entity_type]:
            if not _matches(row, filter_ids, filter_field):
                continue
            yield dict(row)
            emitted += 1
            if limit is not None and emitted >= limit:
                return


def _matches(
    row: dict[str, Any],
    filter_ids: list[str] | None,
    filter_field: str | None,
) -> bool:
    if not filter_ids or filter_field is None:
        return True
    values = {str(value) for value in filter_ids}
    return str(row.get(filter_field)) in values


@pytest.mark.asyncio
async def test_target_data_source_injects_prepared_relation_rows() -> None:
    data_source = TargetProteinClassificationEnrichedTargetDataSource(
        _FakeChEMBLDataSource()
    )

    rows = [row async for row in data_source.fetch("target", limit=1)]

    assert len(rows) == 1
    relation_rows = rows[0]["target_protein_classifications"]
    assert relation_rows == [
        {
            "target_id": "CHEMBL_T1",
            "component_id": 10,
            "hierarchy_index": 0,
            "leaf_id": 3,
            "l1_id": 1,
            "l1_name": "Enzyme",
            "l1_desc": "Root",
            "l2_id": 2,
            "l2_name": "Kinase",
            "l2_desc": "Branch",
            "l3_id": 3,
            "l3_name": "Serine/threonine kinase",
            "l3_desc": "Leaf",
            "l4_id": None,
            "l4_name": None,
            "l4_desc": None,
            "l5_id": None,
            "l5_name": None,
            "l5_desc": None,
            "classification_status": "resolved",
        }
    ]


@pytest.mark.asyncio
async def test_relation_data_source_derives_rows_from_target_components() -> None:
    data_source = TargetProteinClassificationDataSource(_FakeChEMBLDataSource())

    rows = [
        row
        async for row in data_source.fetch("target_protein_classification", limit=10)
    ]

    assert len(rows) == 1
    assert rows[0]["target_id"] == "CHEMBL_T1"
    assert rows[0]["component_id"] == 10
    assert rows[0]["leaf_id"] == 3
    assert rows[0]["l1_name"] == "Enzyme"
    assert rows[0]["l2_name"] == "Kinase"
    assert rows[0]["l3_name"] == "Serine/threonine kinase"
