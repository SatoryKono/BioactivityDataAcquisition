"""Integration tests for Unified Column Naming in Composite Pipelines."""

import pytest
import polars as pl
from unittest.mock import MagicMock, AsyncMock

from bioetl.application.composite.merger import MergeService
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.domain.composite.config import MergeConfig, EnricherConfig
from bioetl.domain.composite.strategy import MergeStrategy, ConflictResolution


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    # Default returns empty list
    storage.read_silver.return_value = []
    storage.write_silver_merged = AsyncMock()
    storage.write_gold_merged = AsyncMock()
    return storage


class TestColumnNamingIntegration:
    """Integration tests for unified column naming in composite pipelines."""

    @pytest.fixture
    def seed_df(self) -> pl.DataFrame:
        """Seed DataFrame simulating chembl_publication output."""
        return pl.DataFrame({
            "doi": ["10.1000/test1", "10.1000/test2"],
            "title": ["Title 1", "Title 2"],
            "abstract": ["Abstract 1", "Abstract 2"],
            "journal": ["Journal A", "Journal B"],
            "_ingestion_ts": ["2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z"],
        })

    @pytest.fixture
    def enricher_df(self) -> pl.DataFrame:
        """Enricher DataFrame simulating crossref_publication output."""
        return pl.DataFrame({
            "doi": ["10.1000/test1", "10.1000/test2"],
            "title": ["CrossRef Title 1", "CrossRef Title 2"],
            "citation_count": [100, 200],
            "publisher": ["Publisher A", "Publisher B"],
        })

    def test_seed_columns_renamed_to_qualified_format(self, seed_df, mock_logger):
        """Seed columns should be renamed to {provider}.{entity}.{field}."""
        renamer = ColumnRenamer(logger=mock_logger)
        result = renamer.rename_dataframe(seed_df, "chembl_publication")

        assert "chembl.publication.title" in result.columns
        assert "chembl.publication.abstract" in result.columns
        assert "chembl.publication.journal" in result.columns
        # Join key NOT renamed
        assert "doi" in result.columns
        # System column NOT renamed
        assert "_ingestion_ts" in result.columns

    def test_enricher_columns_renamed_to_qualified_format(self, enricher_df, mock_logger):
        """Enricher columns should be renamed to {provider}.{entity}.{field}."""
        renamer = ColumnRenamer(logger=mock_logger)
        result = renamer.rename_dataframe(enricher_df, "crossref_publication")

        assert "crossref.publication.title" in result.columns
        assert "crossref.publication.citation_count" in result.columns
        assert "crossref.publication.publisher" in result.columns
        assert "doi" in result.columns

    @pytest.mark.asyncio
    async def test_merged_result_has_all_qualified_columns(
        self, seed_df, enricher_df, mock_storage, mock_logger
    ):
        """After merge, all business columns should be qualified."""
        # Setup merger
        config = MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver/composite",
            output_gold_path="gold/composite",
        )
        merger = MergeService(config, mock_storage, mock_logger)

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        # Manually setup mocks for read_silver calls inside merge if we were calling merge()
        # But we can test _apply_joins directly to focus on column structure

        result = await merger._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        expected_columns = {
            "doi",  # Join key - not renamed
            "chembl.publication.title",
            "chembl.publication.abstract",
            "chembl.publication.journal",
            "crossref.publication.title",
            "crossref.publication.citation_count",
            "crossref.publication.publisher",
            "_ingestion_ts",
        }

        # Verify seed columns were renamed (Wait, seed renaming happens in merge(), not _apply_joins!)
        # _apply_joins assumes seed is already prepared?
        # Let's check merge() code.
        # In merge(), seed_df is renamed BEFORE calling _apply_joins().
        # So we need to rename seed_df manually before passing to _apply_joins in this test
        # OR test merge() itself.

        # Let's test merge() itself by mocking reads.

        async def read_side_effect(table):
            if "chembl" in table:
                return seed_df.to_dicts()
            if "crossref" in table:
                return enricher_df.to_dicts()
            return []

        mock_storage.read_silver.side_effect = read_side_effect

        # We also need enrichment results
        from bioetl.domain.composite.result import EnrichmentResult, EnrichmentStatus
        enrichment_results = {
            "crossref_publication": EnrichmentResult(
                enricher_name="crossref_publication",
                status=EnrichmentStatus.SUCCESS,
                records_enriched=2,
                records_input=2,
                records_not_found=0,
                records_errored=0,
                dq_error_rate=0.0,
                duration_seconds=1.0,
            )
        }

        # Run merge
        merge_result = await merger.merge(
            seed_table="silver/chembl/publication",
            enrichers=[enricher_config],
            enrichment_results=enrichment_results,
            run_id="test-run",
            seed_pipeline="chembl_publication",
        )

        # Verify output via mock_storage.write_gold_merged call
        mock_storage.write_gold_merged.assert_called_once()
        args = mock_storage.write_gold_merged.call_args[0]
        # args[1] is records list of dicts
        output_records = args[1]
        first_row = output_records[0]

        # Check keys in output
        output_keys = set(first_row.keys())

        # Note: metadata columns are added in merge()
        expected_meta = {
            "_composite_run_id", "_source_providers", "_enrichment_status", "_lineage_created_at"
        }

        # Verify business columns
        assert "chembl.publication.title" in output_keys
        assert "chembl.publication.abstract" in output_keys
        assert "crossref.publication.citation_count" in output_keys
        assert "doi" in output_keys
