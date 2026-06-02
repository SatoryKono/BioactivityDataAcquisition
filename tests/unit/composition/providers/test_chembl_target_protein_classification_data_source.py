"""Tests for snapshot-backed target protein classification data source."""

from __future__ import annotations

from unittest.mock import MagicMock

import pyarrow as pa
import pytest

from bioetl.composition.providers._chembl_target_protein_classification_data_source import (
    TargetProteinClassificationSnapshotDataSource,
)
from bioetl.domain.types import HealthStatus


pytestmark = pytest.mark.unit


class _FakeDeltaReader:
    def __init__(self) -> None:
        self.tables = {
            "chembl.target": pa.table(
                {
                    "target_id": ["CHEMBL_T1", "CHEMBL_T2"],
                    "component_ids": ["[10]", "[]"],
                    "primary_component_id": [10, None],
                    "target_components": ['[{"component_id":10}]', "[]"],
                }
            ),
            "chembl.target_component": pa.table(
                {
                    "component_id": [10],
                    "protein_classification_ids": ["[3]"],
                    "protein_classifications": ['[{"protein_classification_id":3}]'],
                }
            ),
            "chembl.protein_class": pa.table(
                {
                    "protein_class_id": [1, 2, 3],
                    "parent_id": [None, 1, 2],
                    "class_level": [1, 2, 3],
                    "pref_name": ["Enzyme", "Kinase", "Serine/threonine kinase"],
                    "protein_class_desc": ["Root", "Branch", "Leaf"],
                    "replaced_by": [None, None, None],
                }
            ),
        }

    async def read_table(
        self,
        table_path: str,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> pa.Table:
        table = self.tables[table_path]
        if columns is not None:
            table = table.select(columns)
        if limit is not None:
            table = table.slice(0, limit)
        return table

    async def table_exists(self, table_path: str) -> bool:
        return table_path in self.tables

    async def get_schema(self, table_path: str) -> object:
        return self.tables[table_path].schema

    async def get_row_count(self, table_path: str) -> int:
        return self.tables[table_path].num_rows

    async def aclose(self) -> None:
        return None


@pytest.fixture
def data_source() -> TargetProteinClassificationSnapshotDataSource:
    logger = MagicMock()
    return TargetProteinClassificationSnapshotDataSource(
        delta_reader=_FakeDeltaReader(),
        logger=logger,
    )


@pytest.mark.asyncio
async def test_relation_data_source_derives_rows_from_local_snapshot_tables(
    data_source: TargetProteinClassificationSnapshotDataSource,
) -> None:
    rows = [
        row
        async for row in data_source.fetch("target_protein_classification", limit=10)
    ]

    assert rows == [
        {
            "target_id": "CHEMBL_T1",
            "classification_status": "resolved",
            "component_id": 10,
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
        },
        {
            "target_id": "CHEMBL_T2",
            "classification_status": "missing_classification",
            "component_id": None,
            "leaf_id": None,
            "l1_id": None,
            "l1_name": None,
            "l1_desc": None,
            "l2_id": None,
            "l2_name": None,
            "l2_desc": None,
            "l3_id": None,
            "l3_name": None,
            "l3_desc": None,
            "l4_id": None,
            "l4_name": None,
            "l4_desc": None,
            "l5_id": None,
            "l5_name": None,
            "l5_desc": None,
        },
    ]


@pytest.mark.asyncio
async def test_relation_data_source_supports_target_filtering(
    data_source: TargetProteinClassificationSnapshotDataSource,
) -> None:
    rows = [
        row
        async for row in data_source.fetch_filtered(
            "target_protein_classification",
            filter_ids=["CHEMBL_T1"],
            filter_field="target_id",
            limit=10,
        )
    ]

    assert len(rows) == 1
    assert rows[0]["target_id"] == "CHEMBL_T1"
    assert rows[0]["classification_status"] == "resolved"


@pytest.mark.asyncio
async def test_relation_data_source_supports_component_filtering(
    data_source: TargetProteinClassificationSnapshotDataSource,
) -> None:
    rows = [
        row
        async for row in data_source.fetch_filtered(
            "target_protein_classification",
            filter_ids=["10"],
            filter_field="component_id",
            limit=10,
        )
    ]

    assert len(rows) == 1
    assert rows[0]["target_id"] == "CHEMBL_T1"
    assert rows[0]["component_id"] == 10


@pytest.mark.asyncio
async def test_relation_data_source_health_check_requires_snapshot_tables(
    data_source: TargetProteinClassificationSnapshotDataSource,
) -> None:
    assert await data_source.health_check() == HealthStatus.HEALTHY
