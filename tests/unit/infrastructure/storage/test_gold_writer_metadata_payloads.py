"""Unit tests for pure Gold metadata payload builders."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from bioetl.domain.medallion import GoldWriteMode
from bioetl.infrastructure.storage.gold.metadata_payloads import (
    build_gold_merged_metadata_input,
    build_gold_metadata_input,
    build_gold_metadata_payload,
)


@pytest.mark.unit
class TestBuildGoldMetadataInput:
    """Tests for Gold coordinator input payload construction."""

    def test_converts_silver_refs_and_preserves_transform_metadata(self) -> None:
        """Coordinator input should expose canonical SilverRef lineage objects."""
        silver_ref = MagicMock()
        silver_ref.table_name = "chembl.activity"
        silver_ref.table_path = "silver/chembl/activity"
        silver_ref.delta_version = 7

        result = build_gold_metadata_input(
            table_path="gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            completed_at=None,
            silver_refs=[silver_ref],
            gold_schema=None,
            transform_version="2.0.0",
            transform_steps=("normalize", "enrich"),
        )

        assert result.transform_version == "2.0.0"
        assert result.transform_steps == ("normalize", "enrich")
        assert result.silver_refs is not None
        assert len(result.silver_refs) == 1
        assert result.silver_refs[0].table_name == "chembl.activity"
        assert result.silver_refs[0].delta_version == 7


@pytest.mark.unit
class TestBuildGoldMergedMetadataInput:
    """Tests for merged Gold metadata input construction."""

    def test_builds_overwrite_input_with_transform_metadata(self) -> None:
        result = build_gold_merged_metadata_input(
            table_path="gold/publication",
            table_name="composite.publication",
            records=[{"_lineage_created_at": "2025-01-15T10:00:00", "id": 1}],
            completed_at=None,
            composite_run_id="cmp-1",
            schema=None,
            transform_version="2.0.0",
            transform_steps=("normalize", "enrich"),
        )

        assert result.mode == GoldWriteMode.OVERWRITE
        assert result.transform_version == "2.0.0"
        assert result.transform_steps == ("normalize", "enrich")
        assert result.composite_run_id == "cmp-1"
        assert result.schema_validation_enabled is False

    def test_enables_schema_validation_when_schema_present(self) -> None:
        mock_schema = MagicMock()

        result = build_gold_merged_metadata_input(
            table_path="gold/publication",
            table_name="composite.publication",
            records=[{"id": 1}],
            completed_at=None,
            composite_run_id=None,
            schema=mock_schema,
            transform_version="1.0.0",
            transform_steps=(),
        )

        assert result.schema_validation_enabled is True
        assert result.schema_validation_strict is True

    def test_prefers_ingestion_ts_over_lineage_created_at(self) -> None:
        result = build_gold_merged_metadata_input(
            table_path="gold/publication",
            table_name="composite.publication",
            records=[
                {"_ingestion_ts": "2025-06-01T08:00:00", "id": 1},
                {"_lineage_created_at": "2025-05-01T08:00:00+00:00", "id": 2},
            ],
            completed_at=None,
            composite_run_id=None,
            schema=None,
            transform_version=None,
            transform_steps=(),
        )

        assert result.completed_at is not None
        assert result.completed_at.month == 6

    def test_ignores_lineage_created_at_without_explicit_or_ingestion_anchor(
        self,
    ) -> None:
        result = build_gold_merged_metadata_input(
            table_path="gold/publication",
            table_name="composite.publication",
            records=[{"_lineage_created_at": "2025-05-01T08:00:00+00:00", "id": 2}],
            completed_at=None,
            composite_run_id=None,
            schema=None,
            transform_version=None,
            transform_steps=(),
        )

        assert result.completed_at is None

    def test_prefers_explicit_completed_at_over_record_timestamp(self) -> None:
        result = build_gold_merged_metadata_input(
            table_path="gold/publication",
            table_name="composite.publication",
            records=[{"_lineage_created_at": "2025-05-01T08:00:00+00:00", "id": 2}],
            completed_at=datetime(2025, 4, 1, 0, 0, 0),
            composite_run_id="cmp-explicit",
            schema=None,
            transform_version=None,
            transform_steps=(),
        )

        assert result.completed_at is not None
        assert result.completed_at.month == 4
        assert result.lineage_created_at == datetime(2025, 4, 1, 0, 0, 0)


@pytest.mark.unit
class TestBuildGoldMetadataPayload:
    """Tests for the standard Gold metadata payload routing helper."""

    def test_uses_bundle_coordinator_when_present(self) -> None:
        coordinator = MagicMock()
        metadata = MagicMock()
        bundle = MagicMock(metadata=metadata, lineage_fragment=MagicMock())
        coordinator.create_gold_metadata_bundle = MagicMock(return_value=bundle)

        result = build_gold_metadata_payload(
            coordinator=coordinator,
            table_path="gold/t",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
            silver_refs=None,
            gold_schema=None,
            transform_version="1.0.0",
            transform_steps=("normalize",),
        )

        assert result is metadata
        coordinator.create_gold_metadata_bundle.assert_called_once()

    def test_raises_when_no_coordinator(self) -> None:
        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinator is required for build_gold_metadata_payload",
        ):
            build_gold_metadata_payload(
                coordinator=None,
                table_path="gold/t",
                table_name="chembl.activity",
                records=[{"id": 1}],
                mode=GoldWriteMode.OVERWRITE,
                scd_config=None,
                ingestion_ts=None,
                run_id=None,
                silver_refs=None,
                gold_schema=None,
                transform_version="1.0.0",
                transform_steps=("normalize",),
            )

    def test_raises_when_bundle_factory_missing(self) -> None:
        coordinator = MagicMock(spec=["create_gold_metadata"])
        coordinator.create_gold_metadata = MagicMock(return_value=MagicMock())

        with pytest.raises(
            RuntimeError,
            match="create_gold_metadata_bundle is required for build_gold_metadata_payload",
        ):
            build_gold_metadata_payload(
                coordinator=coordinator,
                table_path="gold/t",
                table_name="chembl.activity",
                records=[{"id": 1}],
                mode=GoldWriteMode.OVERWRITE,
                scd_config=None,
                ingestion_ts=None,
                run_id=None,
                silver_refs=None,
                gold_schema=None,
                transform_version="1.0.0",
                transform_steps=("normalize",),
            )
