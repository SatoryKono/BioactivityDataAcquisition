"""Unit tests for MergeService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.merger import MergeService, _path_to_table_name
from bioetl.domain.composite.config import EnricherConfig, MergeConfig
from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


@pytest.fixture
def mock_storage():
    """Create a mock StoragePort."""
    storage = AsyncMock()
    storage.read_silver = AsyncMock(return_value=[])
    storage.write_silver_merged = AsyncMock()
    storage.write_gold_merged = AsyncMock()
    return storage


@pytest.fixture
def mock_logger():
    """Create a mock LoggerPort."""
    return MagicMock()


@pytest.fixture
def merge_config():
    """Create a sample MergeConfig."""
    return MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/composite/test",
        output_gold_path="gold/test_merged",
    )


@pytest.fixture
def merge_service(merge_config, mock_storage, mock_logger):
    """Create a MergeService instance."""
    return MergeService(
        merge_config=merge_config,
        storage=mock_storage,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestPathToTableName:
    """Tests for _path_to_table_name helper."""

    def test_strips_silver_prefix(self):
        """Test silver prefix is stripped."""
        assert _path_to_table_name("silver/chembl/activity") == "chembl/activity"

    def test_strips_gold_prefix(self):
        """Test gold prefix is stripped."""
        assert (
            _path_to_table_name("gold/publication_enriched") == "publication_enriched"
        )

    def test_strips_bronze_prefix(self):
        """Test bronze prefix is stripped."""
        assert _path_to_table_name("bronze/provider/entity") == "provider/entity"

    def test_returns_unchanged_if_no_prefix(self):
        """Test path without prefix is unchanged."""
        assert _path_to_table_name("some/path") == "some/path"


@pytest.mark.unit
class TestMergeServiceReadsSilverViaStorage:
    """Tests for MergeService reading Silver via StoragePort."""

    @pytest.mark.asyncio
    async def test_read_silver_uses_storage_port(self, merge_service, mock_storage):
        """Test _read_silver_table uses StoragePort.read_silver."""
        mock_storage.read_silver.return_value = [
            {"id": "1", "val": "A"},
            {"id": "2", "val": "B"},
        ]

        df = await merge_service._read_silver_table("silver/test/table")

        mock_storage.read_silver.assert_called_once_with("test/table")
        assert len(df) == 2
        assert df["id"].to_list() == ["1", "2"]

    @pytest.mark.asyncio
    async def test_read_silver_returns_empty_dataframe_for_no_records(
        self, merge_service, mock_storage
    ):
        """Test _read_silver_table returns empty DataFrame for no records."""
        mock_storage.read_silver.return_value = []

        df = await merge_service._read_silver_table("silver/test/table")

        assert len(df) == 0


@pytest.mark.unit
class TestMergeServiceWritesViaStorage:
    """Tests for MergeService writing via StoragePort."""

    @pytest.mark.asyncio
    async def test_write_merged_silver_uses_storage_port(
        self, merge_service, mock_storage
    ):
        """Test _write_merged_silver uses StoragePort.write_silver_merged."""
        import polars as pl

        df = pl.DataFrame({"id": ["1", "2"], "val": ["A", "B"]})

        await merge_service._write_merged_silver(df)

        mock_storage.write_silver_merged.assert_called_once()
        call_args = mock_storage.write_silver_merged.call_args
        assert call_args[0][0] == "composite/test"  # table_name from output_silver_path
        assert len(call_args[0][1]) == 2  # records

    @pytest.mark.asyncio
    async def test_write_merged_gold_uses_storage_port(
        self, merge_service, mock_storage
    ):
        """Test _write_merged_gold uses StoragePort.write_gold_merged."""
        import polars as pl

        df = pl.DataFrame({"id": ["1", "2"], "val": ["A", "B"]})

        await merge_service._write_merged_gold(df)

        mock_storage.write_gold_merged.assert_called_once()
        call_args = mock_storage.write_gold_merged.call_args
        assert call_args[0][0] == "test_merged"  # table_name from output_gold_path


@pytest.mark.unit
class TestMergeServiceMergeOperation:
    """Tests for MergeService.merge operation."""

    @pytest.mark.asyncio
    async def test_merge_calls_read_and_write(self, merge_service, mock_storage):
        """Test merge calls read and write via StoragePort."""
        # Setup seed data
        mock_storage.read_silver.return_value = [
            {"id": "1", "name": "Test1"},
            {"id": "2", "name": "Test2"},
        ]

        enrichers = []
        enrichment_results: dict[str, EnrichmentResult] = {}

        result = await merge_service.merge(
            seed_table="silver/seed/table",
            enrichers=enrichers,
            enrichment_results=enrichment_results,
            run_id="test-run-123",
        )

        # Verify reads and writes were called
        mock_storage.read_silver.assert_called()
        mock_storage.write_silver_merged.assert_called_once()
        mock_storage.write_gold_merged.assert_called_once()

        # Verify result
        assert result.records_merged == 2
        assert result.records_from_seed == 2
        assert "seed" in result.sources_used

    @pytest.mark.asyncio
    async def test_merge_with_enricher(self, merge_service, mock_storage):
        """Test merge with a successful enricher."""
        # Setup mock to return different data for seed vs enricher
        call_count = 0

        async def read_side_effect(table_name):
            nonlocal call_count
            call_count += 1
            if "seed" in table_name:
                return [{"id": "1", "seed_val": "A"}]
            else:
                return [{"id": "1", "enricher_val": "X"}]

        mock_storage.read_silver.side_effect = read_side_effect

        enrichers = [
            EnricherConfig(
                pipeline="test_enricher",
                join_keys=("id",),
                required=False,
                silver_table="silver/enricher/table",
            )
        ]
        enrichment_results = {
            "test_enricher": EnrichmentResult(
                enricher_name="test_enricher",
                status=EnrichmentStatus.SUCCESS,
                records_input=1,
                records_enriched=1,
            )
        }

        result = await merge_service.merge(
            seed_table="silver/seed/table",
            enrichers=enrichers,
            enrichment_results=enrichment_results,
            run_id="test-run-123",
        )

        # Should read seed and enricher tables
        assert mock_storage.read_silver.call_count == 2
        assert result.records_from_seed == 1
        assert "test_enricher" in result.sources_used
