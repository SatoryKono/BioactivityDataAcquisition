"""Tests for snapshot-backed target protein classification data source."""

from __future__ import annotations

from unittest.mock import MagicMock

import pyarrow as pa
import pytest

from bioetl.composition.providers._chembl_target_protein_classification_data_source import (
    TargetProteinClassificationSnapshotDataSource,
)
from bioetl.composition.providers._chembl_target_protein_classification_manifest import (
    source_manifest,
    with_source_manifest,
)
from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
    ProteinClassTopLevelMappingEntry,
)
from bioetl.domain.types import HealthStatus


pytestmark = pytest.mark.unit


class _FakeDeltaReader:
    def __init__(self) -> None:
        self.closed = False
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
        self.closed = True


@pytest.fixture
def data_source() -> TargetProteinClassificationSnapshotDataSource:
    logger = MagicMock()
    return TargetProteinClassificationSnapshotDataSource(
        delta_reader=_FakeDeltaReader(),
        logger=logger,
        target_type_mapping_data=ProteinClassTargetTypeMappingData(
            mapping_version="protein_class_l1_map_v1",
            entries=(
                ProteinClassTopLevelMappingEntry("Enzyme", "enzyme", True),
                ProteinClassTopLevelMappingEntry(
                    "Unclassified protein",
                    "unclassified_protein",
                    False,
                ),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_relation_data_source_derives_rows_from_local_snapshot_tables(
    data_source: TargetProteinClassificationSnapshotDataSource,
) -> None:
    rows = [
        row
        async for row in data_source.fetch("target_protein_classification", limit=10)
    ]

    assert len(rows) == 2
    assert {
        key: rows[0][key]
        for key in (
            "target_id",
            "classification_status",
            "component_id",
            "leaf_id",
            "path_ids",
            "path_names",
            "path_labels",
            "depth",
            "root_id",
            "is_leaf",
            "l1_id",
            "l2_id",
            "l3_id",
            "canonical_l1",
            "l1_counts_for_target_type",
            "l1_mapping_version",
            "target_type_rule_version",
            "l1_normalization_status",
        )
    } == {
        "target_id": "CHEMBL_T1",
        "classification_status": "resolved",
        "component_id": 10,
        "leaf_id": 3,
        "path_ids": "[1,2,3]",
        "path_names": '["Enzyme","Kinase","Serine/threonine kinase"]',
        "path_labels": '["1:Enzyme","2:Kinase","3:Serine/threonine kinase"]',
        "depth": 2,
        "root_id": 1,
        "is_leaf": True,
        "l1_id": 1,
        "l2_id": 2,
        "l3_id": 3,
        "canonical_l1": "enzyme",
        "l1_counts_for_target_type": True,
        "l1_mapping_version": "protein_class_l1_map_v1",
        "target_type_rule_version": "target_type_rule_v1",
        "l1_normalization_status": "ok",
    }
    assert {
        key: rows[1][key]
        for key in (
            "target_id",
            "classification_status",
            "component_id",
            "leaf_id",
            "path_ids",
            "depth",
            "root_id",
            "is_leaf",
        )
    } == {
        "target_id": "CHEMBL_T2",
        "classification_status": "missing_classification",
        "component_id": None,
        "leaf_id": None,
        "path_ids": None,
        "depth": None,
        "root_id": None,
        "is_leaf": None,
    }
    for row in rows:
        assert row["dataset_version"] == "target-protein-classification-path-v2.1.0"
        assert row["source_url"].endswith("/protein_classification")
        assert row["chembl_release"] == "unknown"
        assert row["chembl_api_version"] == "unknown"
        assert row["source_manifest_status"] == "release_metadata_unavailable"
        assert len(row["source_snapshot_fingerprint"]) == 64
        assert row["target_snapshot_row_count"] == 2
        assert row["target_component_snapshot_row_count"] == 1
        assert row["protein_class_snapshot_row_count"] == 3


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


@pytest.mark.asyncio
async def test_relation_data_source_context_offset_and_close(
    data_source: TargetProteinClassificationSnapshotDataSource,
) -> None:
    async with data_source as loaded:
        assert loaded is data_source

    assert data_source._delta_reader.closed is True

    rows = [
        row
        async for row in data_source.fetch(
            "target_protein_classification",
            limit=1,
            offset=1,
        )
    ]

    assert len(rows) == 1
    assert rows[0]["target_id"] == "CHEMBL_T2"


@pytest.mark.asyncio
async def test_relation_data_source_health_check_reports_missing_tables(
    data_source: TargetProteinClassificationSnapshotDataSource,
) -> None:
    data_source._delta_reader.tables.pop("chembl.protein_class")

    assert await data_source.health_check() == HealthStatus.DEGRADED
    data_source._logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_relation_data_source_rejects_invalid_entity_and_filter(
    data_source: TargetProteinClassificationSnapshotDataSource,
) -> None:
    with pytest.raises(ValueError, match="only serves target_protein_classification"):
        data_source.fetch("target", limit=1)

    with pytest.raises(ValueError, match="Unsupported target protein classification"):
        [
            row
            async for row in data_source.fetch(
                "target_protein_classification",
                filter_ids=["CHEMBL_T1"],
                filter_field="unsupported_field",
                limit=1,
            )
        ]

    with pytest.raises(ValueError, match="only serves target_protein_classification"):
        [
            row
            async for row in data_source.fetch_multi_filtered(
                "target",
                {"target_id": ["CHEMBL_T1"]},
                limit=1,
            )
        ]


@pytest.mark.asyncio
async def test_relation_data_source_multi_filter_intersection_and_empty_filters(
    data_source: TargetProteinClassificationSnapshotDataSource,
) -> None:
    rows = [
        row
        async for row in data_source.fetch_multi_filtered(
            "target_protein_classification",
            {
                "target_id": ["CHEMBL_T1", "CHEMBL_T2"],
                "component_id": ["10", "bad"],
            },
            limit=1,
        )
    ]

    assert len(rows) == 1
    assert rows[0]["target_id"] == "CHEMBL_T1"

    assert [
        row
        async for row in data_source.fetch_multi_filtered(
            "target_protein_classification",
            {},
            limit=10,
        )
    ] == []


def test_relation_rows_for_target_requires_loaded_snapshot(
    data_source: TargetProteinClassificationSnapshotDataSource,
) -> None:
    with pytest.raises(RuntimeError, match="was not initialized"):
        data_source._relation_rows_for_target("CHEMBL_T1")


def test_source_manifest_prefers_release_metadata_and_stable_fingerprint() -> None:
    first = source_manifest(
        target_rows=({"target_id": "T2"}, {"target_id": "T1"}),
        target_component_rows=({"component_id": 10},),
        protein_class_rows=(
            {
                "protein_class_id": 3,
                "chembl_release": "35",
                "chembl_api_version": "v1",
            },
        ),
    )
    second = source_manifest(
        target_rows=({"target_id": "T1"}, {"target_id": "T2"}),
        target_component_rows=({"component_id": 10},),
        protein_class_rows=(
            {
                "protein_class_id": 3,
                "chembl_release": "35",
                "chembl_api_version": "v1",
            },
        ),
    )

    assert first["chembl_release"] == "35"
    assert first["chembl_api_version"] == "v1"
    assert first["source_manifest_status"] == "release_metadata_available"
    assert first["source_snapshot_fingerprint"] == second["source_snapshot_fingerprint"]


def test_with_source_manifest_overlays_relation_row_metadata() -> None:
    assert with_source_manifest(
        {"target_id": "CHEMBL_T1", "dataset_version": "row"},
        {"dataset_version": "manifest", "source_url": "https://example.test"},
    ) == {
        "target_id": "CHEMBL_T1",
        "dataset_version": "manifest",
        "source_url": "https://example.test",
    }
