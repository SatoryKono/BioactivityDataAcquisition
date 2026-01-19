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
class TestMergeServiceJoinKeyNormalization:
    """Tests for join key normalization (case-insensitive DOI/PMID matching)."""

    def test_normalize_doi_to_lowercase(self, merge_service):
        """Test DOI column is normalized to lowercase."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["10.1038/NATURE12373", "10.1000/ABC.DEF"],
            "title": ["Title 1", "Title 2"],
        })

        result = merge_service._normalize_join_key_columns(df, ["doi"])

        assert result["doi"].to_list() == ["10.1038/nature12373", "10.1000/abc.def"]
        # Non-normalized columns should be unchanged
        assert result["title"].to_list() == ["Title 1", "Title 2"]

    def test_normalize_pmid_to_lowercase(self, merge_service):
        """Test PMID column is normalized to lowercase."""
        import polars as pl

        df = pl.DataFrame({
            "pmid": ["12345678", "PMC1234567"],
            "title": ["Title 1", "Title 2"],
        })

        result = merge_service._normalize_join_key_columns(df, ["pmid"])

        assert result["pmid"].to_list() == ["12345678", "pmc1234567"]

    def test_normalize_pmc_id_to_lowercase(self, merge_service):
        """Test PMC_ID column is normalized to lowercase."""
        import polars as pl

        df = pl.DataFrame({
            "pmc_id": ["PMC1234567", "PMC7654321"],
        })

        result = merge_service._normalize_join_key_columns(df, ["pmc_id"])

        assert result["pmc_id"].to_list() == ["pmc1234567", "pmc7654321"]

    def test_normalize_skips_non_identifier_columns(self, merge_service):
        """Test non-identifier columns are not normalized."""
        import polars as pl

        df = pl.DataFrame({
            "title": ["UPPERCASE TITLE", "Another TITLE"],
            "doi": ["10.1038/NATURE", "10.1000/ABC"],
        })

        result = merge_service._normalize_join_key_columns(df, ["title", "doi"])

        # title is not in _NORMALIZE_JOIN_KEYS, so it should be unchanged
        assert result["title"].to_list() == ["UPPERCASE TITLE", "Another TITLE"]
        # doi should be normalized
        assert result["doi"].to_list() == ["10.1038/nature", "10.1000/abc"]

    def test_normalize_handles_null_values(self, merge_service):
        """Test normalization handles null DOI values."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["10.1038/NATURE", None, "10.1000/ABC"],
        })

        result = merge_service._normalize_join_key_columns(df, ["doi"])

        assert result["doi"].to_list() == ["10.1038/nature", None, "10.1000/abc"]

    def test_normalize_returns_unchanged_if_no_normalize_keys(self, merge_service):
        """Test DataFrame is unchanged if no normalizable keys."""
        import polars as pl

        df = pl.DataFrame({
            "id": ["ID1", "ID2"],
            "name": ["Name1", "Name2"],
        })

        result = merge_service._normalize_join_key_columns(df, ["id", "name"])

        # Neither id nor name are in _NORMALIZE_JOIN_KEYS
        assert result["id"].to_list() == ["ID1", "ID2"]
        assert result["name"].to_list() == ["Name1", "Name2"]

    def test_normalize_handles_missing_columns(self, merge_service):
        """Test normalization handles missing columns gracefully."""
        import polars as pl

        df = pl.DataFrame({
            "title": ["Title 1"],
        })

        # Request normalization of doi which doesn't exist
        result = merge_service._normalize_join_key_columns(df, ["doi", "title"])

        # Should return unchanged since doi doesn't exist
        assert result["title"].to_list() == ["Title 1"]

    @pytest.mark.asyncio
    async def test_apply_joins_normalizes_doi_for_matching(
        self, merge_service, mock_storage
    ):
        """Test _apply_joins normalizes DOI for case-insensitive matching."""
        import polars as pl

        # Seed has uppercase DOI
        seed_df = pl.DataFrame({
            "id": ["1"],
            "doi": ["10.1038/NATURE12373"],
            "seed_value": ["from_seed"],
        })

        # Enricher has lowercase DOI
        enricher_df = pl.DataFrame({
            "doi": ["10.1038/nature12373"],
            "enricher_value": ["from_enricher"],
        })

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
            silver_table="silver/crossref/publication",
        )

        result = await merge_service._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
        )

        # Should successfully join despite case difference
        assert len(result) == 1
        assert "enricher_value" in result.columns
        assert result["enricher_value"].to_list() == ["from_enricher"]
        # DOI should be normalized to lowercase
        assert result["doi"].to_list() == ["10.1038/nature12373"]


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
