"""Unit tests for Silver writer metadata operations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _PreparedSilverMetadataWriteOperation,
    _SilverMergedMetadataWriteRequest,
    _SilverMetadataWriteRequest,
    _coerce_silver_metadata_write_request,
    _execute_prepared_silver_metadata_write_operation,
)

TEST_ACTIVITY_TABLE_PATH = "test-output/silver/chembl/activity"
TEST_COMPOSITE_TABLE_PATH = "test-output/silver/composite/publication"


@pytest.mark.unit
class TestCoerceSilverMetadataWriteRequest:
    """Regression coverage for legacy Silver metadata argument coercion."""

    def test_accepts_kwargs_only_calls(self) -> None:
        request = _coerce_silver_metadata_write_request(
            kwargs={
                "table_path": TEST_ACTIVITY_TABLE_PATH,
                "table_name": "chembl.activity",
                "records": [{"entity_id": "1"}],
                "primary_keys": ["entity_id"],
                "mode": SilverWriteMode.MERGE,
            }
        )

        assert request.table_path == TEST_ACTIVITY_TABLE_PATH
        assert request.table_name == "chembl.activity"
        assert request.primary_keys == ["entity_id"]
        assert request.mode is SilverWriteMode.MERGE

    def test_accepts_partial_legacy_positional_args(self) -> None:
        request = _coerce_silver_metadata_write_request(
            None,
            args=(
                TEST_ACTIVITY_TABLE_PATH,
                "chembl.activity",
                [{"entity_id": "1"}],
                ["entity_id"],
                SilverWriteMode.MERGE,
            ),
        )

        assert request.table_path == TEST_ACTIVITY_TABLE_PATH
        assert request.table_name == "chembl.activity"
        assert request.records == [{"entity_id": "1"}]
        assert request.primary_keys == ["entity_id"]
        assert request.mode is SilverWriteMode.MERGE
        assert request.bronze_refs is None


@pytest.mark.unit
class TestExecutePreparedSilverMetadataWriteOperation:
    """Tests for Silver metadata persistence metrics."""

    @pytest.mark.asyncio
    async def test_emits_missing_bronze_refs_metric_for_standard_write(self) -> None:
        host = AsyncMock()
        host._lineage_store = None
        host._metrics = MagicMock()
        metadata = MagicMock()
        request = _SilverMetadataWriteRequest(
            table_path=TEST_ACTIVITY_TABLE_PATH,
            table_name="chembl.activity",
            records=[{"entity_id": "1"}],
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=None,
        )
        prepared = _PreparedSilverMetadataWriteOperation(
            request=request,
            provider_name="chembl",
            entity_name="activity",
            metadata=metadata,
        )

        await _execute_prepared_silver_metadata_write_operation(host, prepared)

        host._write_silver_metadata_file.assert_awaited_once()
        host._metrics.increment_counter.assert_called_once_with(
            "bioetl_lineage_refs_missing_total",
            1,
            {
                "pipeline": "chembl_activity",
                "layer": "silver",
                "ref_type": "bronze_batch",
            },
        )

    @pytest.mark.asyncio
    async def test_emits_composite_source_selection_metrics_for_merged_write(
        self,
    ) -> None:
        host = AsyncMock()
        host._lineage_store = None
        host._metrics = MagicMock()
        metadata = MagicMock()
        request = _SilverMergedMetadataWriteRequest(
            table_path=TEST_COMPOSITE_TABLE_PATH,
            table_name="composite.publication",
            records=[
                {
                    "entity_id": "1",
                    "_source_providers": ["chembl", "pubchem"],
                    "_field_sources": {"title": "chembl", "score": "pubchem"},
                },
                {
                    "entity_id": "2",
                    "_source_providers": ["chembl"],
                    "_field_sources": {"summary": "chembl"},
                },
            ],
            primary_keys=["entity_id"],
            run_id="run-1",
            sources_used=["openalex"],
        )
        prepared = _PreparedSilverMetadataWriteOperation(
            request=request,
            provider_name="composite",
            entity_name="publication",
            metadata=metadata,
        )

        await _execute_prepared_silver_metadata_write_operation(host, prepared)

        host._write_silver_metadata_file.assert_awaited_once()
        host._metrics.increment_counter.assert_has_calls(
            [
                call(
                    "bioetl_composite_source_selection_total",
                    1,
                    {
                        "pipeline": "composite_publication",
                        "decision_type": "silver_source_included",
                        "selected_source": "chembl",
                    },
                ),
                call(
                    "bioetl_composite_source_selection_total",
                    1,
                    {
                        "pipeline": "composite_publication",
                        "decision_type": "silver_source_included",
                        "selected_source": "openalex",
                    },
                ),
                call(
                    "bioetl_composite_source_selection_total",
                    1,
                    {
                        "pipeline": "composite_publication",
                        "decision_type": "silver_source_included",
                        "selected_source": "pubchem",
                    },
                ),
                call(
                    "bioetl_composite_source_selection_total",
                    2,
                    {
                        "pipeline": "composite_publication",
                        "decision_type": "silver_field_selected",
                        "selected_source": "chembl",
                    },
                ),
                call(
                    "bioetl_composite_source_selection_total",
                    1,
                    {
                        "pipeline": "composite_publication",
                        "decision_type": "silver_field_selected",
                        "selected_source": "pubchem",
                    },
                ),
            ],
            any_order=False,
        )
