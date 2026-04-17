"""Integration tests for unified column naming in composite pipelines."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.column_service import (
    ColumnOrderService as ColumnOrderer,
)
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.domain.value_objects.column_order import SemanticGroup

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def renamer(mock_logger: MagicMock) -> ColumnRenamer:
    """Create ColumnRenamer instance."""
    return ColumnRenamer(mock_logger)


@pytest.fixture
def orderer(mock_logger: MagicMock) -> ColumnOrderer:
    """Create ColumnOrderer instance."""
    return ColumnOrderer(mock_logger)


@pytest.fixture
def seed_df() -> pl.DataFrame:
    """Seed DataFrame simulating chembl_publication output."""
    return pl.DataFrame(
        {
            "doi": ["10.1000/test1", "10.1000/test2", "10.1000/test3"],
            "pmid": ["111", "222", None],
            "title": ["ChEMBL Title 1", "ChEMBL Title 2", "ChEMBL Title 3"],
            "abstract": ["Abstract 1", None, "Abstract 3"],
            "journal": ["Journal A", "Journal B", "Journal C"],
            "authors": [["A1"], ["A2"], ["A3"]],
            "publication_date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "_run_id": ["run1", "run1", "run1"],
            "_ingestion_ts": ["2025-01-01T00:00:00Z"] * 3,
            "entity_id": ["e1", "e2", "e3"],
            "content_hash": ["h1", "h2", "h3"],
        }
    )


@pytest.fixture
def enricher_crossref_df() -> pl.DataFrame:
    """Enricher DataFrame simulating crossref_publication output."""
    return pl.DataFrame(
        {
            "doi": ["10.1000/test1", "10.1000/test2"],
            "title": ["CrossRef Title 1", "CrossRef Title 2"],
            "citation_count": [100, 200],
            "publisher": ["Publisher A", "Publisher B"],
        }
    )


class TestFullPipelineColumnOrder:
    """Tests for full pipeline with renaming and ordering."""

    def test_full_pipeline_column_order(
        self,
        renamer: ColumnRenamer,
        orderer: ColumnOrderer,
        seed_df: pl.DataFrame,
        enricher_crossref_df: pl.DataFrame,
    ) -> None:
        """Full pipeline produces correctly ordered columns."""
        # Step 1: Rename seed
        seed_renamed = renamer.rename_dataframe(seed_df, "chembl_publication")

        # Step 2: Rename enricher
        enricher_renamed = renamer.rename_dataframe(
            enricher_crossref_df, "crossref_publication"
        )

        # Step 3: Join
        merged = seed_renamed.join(enricher_renamed, on="doi", how="left")

        # Step 4: Order columns
        ordered = orderer.order_columns(merged)

        # Verify semantic order
        columns = ordered.columns

        # System fields first
        system_cols = [
            c for c in columns if orderer._config.get_group(c) == SemanticGroup.SYSTEM
        ]
        identifier_cols = [
            c
            for c in columns
            if orderer._config.get_group(c) == SemanticGroup.IDENTIFIERS
        ]
        title_cols = [
            c for c in columns if orderer._config.get_group(c) == SemanticGroup.TITLE
        ]

        # Get indices
        system_indices = [columns.index(c) for c in system_cols]
        identifier_indices = [columns.index(c) for c in identifier_cols]
        title_indices = [columns.index(c) for c in title_cols]

        # All system before all identifiers
        if system_indices and identifier_indices:
            assert max(system_indices) < min(identifier_indices)

        # All identifiers before all titles
        if identifier_indices and title_indices:
            assert max(identifier_indices) < min(title_indices)

    def test_provider_order_within_group(
        self,
        renamer: ColumnRenamer,
        orderer: ColumnOrderer,
    ) -> None:
        """Within same semantic group, chembl comes before crossref."""
        # Create DataFrame with multiple providers for same field
        df = pl.DataFrame(
            {
                "crossref.publication.title": ["T1"],
                "chembl.publication.title": ["T2"],
                "pubmed.publication.title": ["T3"],
                "doi": ["10.1/a"],
            }
        )

        ordered = orderer.order_columns(df)

        # Find title column indices
        chembl_idx = ordered.columns.index("chembl.publication.title")
        crossref_idx = ordered.columns.index("crossref.publication.title")
        pubmed_idx = ordered.columns.index("pubmed.publication.title")

        assert chembl_idx < crossref_idx < pubmed_idx

    def test_expected_column_order_publication(
        self,
        renamer: ColumnRenamer,
        orderer: ColumnOrderer,
    ) -> None:
        """Verify expected column order for publication composite."""
        df = pl.DataFrame(
            {
                "citation_count": [100],
                "authors": [["Author"]],
                "journal": ["Nature"],
                "publication_date": ["2025-01-01"],
                "abstract": ["Abstract"],
                "title": ["Title"],
                "mesh_terms": [["term"]],
                "doi": ["10.1/a"],
                "pmid": ["123"],
                "_run_id": ["r1"],
                "entity_id": ["e1"],
                "content_hash": ["hash"],
                "pdf_url": ["http://example.com"],
            }
        )

        ordered = orderer.order_columns(df)

        # Expected order based on semantic groups and alphabetical field names:
        # - SYSTEM: _run_id, content_hash, entity_id (sorted alphabetically)
        # - IDENTIFIERS: doi, pmid
        # - TITLE: title
        # - ABSTRACT: abstract
        # - AUTHORS: authors
        # - JOURNAL: journal
        # - DATES: publication_date
        # - METRICS: citation_count
        # - CLASSIFICATION: mesh_terms
        # - URLS: pdf_url
        expected_order = [
            "_run_id",  # SYSTEM
            "content_hash",  # SYSTEM
            "entity_id",  # SYSTEM
            "doi",  # IDENTIFIERS
            "pmid",  # IDENTIFIERS
            "title",  # TITLE
            "abstract",  # ABSTRACT
            "authors",  # AUTHORS
            "journal",  # JOURNAL
            "publication_date",  # DATES
            "citation_count",  # METRICS
            "mesh_terms",  # CLASSIFICATION
            "pdf_url",  # URLS
        ]

        assert ordered.columns == expected_order


class TestSeedColumnRenaming:
    """Tests for seed column renaming."""

    def test_seed_columns_renamed_to_qualified_format(
        self, renamer: ColumnRenamer, seed_df: pl.DataFrame
    ) -> None:
        """Seed business columns become {provider}.{entity}.{field}."""
        result = renamer.rename_dataframe(seed_df, "chembl_publication")

        # Business columns renamed
        assert "chembl.publication.title" in result.columns
        assert "chembl.publication.abstract" in result.columns
        assert "chembl.publication.journal" in result.columns

        # Original names removed
        assert "title" not in result.columns
        assert "abstract" not in result.columns
        assert "journal" not in result.columns

    def test_seed_join_keys_not_renamed(
        self, renamer: ColumnRenamer, seed_df: pl.DataFrame
    ) -> None:
        """Join keys (doi, pmid) remain unchanged."""
        result = renamer.rename_dataframe(seed_df, "chembl_publication")

        assert "doi" in result.columns
        assert "pmid" in result.columns

    def test_seed_system_columns_not_renamed(
        self, renamer: ColumnRenamer, seed_df: pl.DataFrame
    ) -> None:
        """System columns (prefixed with _) remain unchanged."""
        result = renamer.rename_dataframe(seed_df, "chembl_publication")

        # Columns starting with _ are system columns, not renamed
        assert "_run_id" in result.columns
        assert "_ingestion_ts" in result.columns

        # entity_id and content_hash are identity columns, not renamed
        assert "entity_id" in result.columns
        assert "content_hash" in result.columns


class TestEnricherColumnRenaming:
    """Tests for enricher column renaming."""

    def test_enricher_columns_renamed_to_qualified_format(
        self, renamer: ColumnRenamer, enricher_crossref_df: pl.DataFrame
    ) -> None:
        """Enricher business columns become {provider}.{entity}.{field}."""
        result = renamer.rename_dataframe(enricher_crossref_df, "crossref_publication")

        assert "crossref.publication.title" in result.columns
        assert "crossref.publication.citation_count" in result.columns
        assert "crossref.publication.publisher" in result.columns


class TestNoColumnConflicts:
    """Tests verifying no naming conflicts after renaming."""

    def test_same_field_different_providers_no_conflict(
        self,
        renamer: ColumnRenamer,
        seed_df: pl.DataFrame,
        enricher_crossref_df: pl.DataFrame,
    ) -> None:
        """Same field from different providers gets unique qualified names."""
        seed_renamed = renamer.rename_dataframe(seed_df, "chembl_publication")
        enricher_renamed = renamer.rename_dataframe(
            enricher_crossref_df, "crossref_publication"
        )

        # Verify they can coexist after join
        merged = seed_renamed.join(enricher_renamed, on="doi", how="left")

        assert "chembl.publication.title" in merged.columns
        assert "crossref.publication.title" in merged.columns


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_dataframe(
        self, renamer: ColumnRenamer, orderer: ColumnOrderer
    ) -> None:
        """Empty DataFrame handled correctly."""
        df = pl.DataFrame()
        renamed = renamer.rename_dataframe(df, "chembl_publication")
        ordered = orderer.order_columns(renamed)

        assert len(ordered.columns) == 0

    def test_only_system_columns(
        self, renamer: ColumnRenamer, orderer: ColumnOrderer
    ) -> None:
        """DataFrame with only system columns."""
        df = pl.DataFrame(
            {
                "_run_id": ["r1"],
                "_ingestion_ts": ["2025-01-01"],
            }
        )
        renamed = renamer.rename_dataframe(df, "chembl_publication")
        ordered = orderer.order_columns(renamed)

        # Alphabetical order: _ingestion_ts < _run_id
        assert ordered.columns == ["_ingestion_ts", "_run_id"]


class TestDataPreservation:
    """Tests verifying data integrity through the pipeline."""

    def test_data_values_preserved_through_rename(self, renamer: ColumnRenamer) -> None:
        """Data values are preserved after renaming."""
        df = pl.DataFrame(
            {
                "title": ["Test Title"],
                "abstract": ["Test Abstract"],
                "doi": ["10.1/test"],
            }
        )

        result = renamer.rename_dataframe(df, "chembl_publication")

        # Data preserved in renamed columns
        assert result["chembl.publication.title"].to_list() == ["Test Title"]
        assert result["chembl.publication.abstract"].to_list() == ["Test Abstract"]
        assert result["doi"].to_list() == ["10.1/test"]

    def test_data_values_preserved_through_ordering(
        self, orderer: ColumnOrderer
    ) -> None:
        """Data values are preserved after ordering."""
        df = pl.DataFrame(
            {
                "citation_count": [100],
                "title": ["Test"],
                "_run_id": ["r1"],
            }
        )

        result = orderer.order_columns(df)

        # Data preserved regardless of column order
        assert result["citation_count"].to_list() == [100]
        assert result["title"].to_list() == ["Test"]
        assert result["_run_id"].to_list() == ["r1"]

    def test_row_count_preserved(
        self,
        renamer: ColumnRenamer,
        orderer: ColumnOrderer,
        seed_df: pl.DataFrame,
    ) -> None:
        """Row count is preserved through full pipeline."""
        original_rows = len(seed_df)

        renamed = renamer.rename_dataframe(seed_df, "chembl_publication")
        ordered = orderer.order_columns(renamed)

        assert len(ordered) == original_rows


class TestMultipleEnrichers:
    """Tests for scenarios with multiple enrichers."""

    def test_three_providers_merge_correctly(
        self, renamer: ColumnRenamer, orderer: ColumnOrderer
    ) -> None:
        """Columns from three providers merge and order correctly."""
        # Seed from ChEMBL
        seed = pl.DataFrame(
            {
                "doi": ["10.1/a", "10.1/b"],
                "title": ["ChEMBL 1", "ChEMBL 2"],
                "entity_id": ["e1", "e2"],
            }
        )

        # Enricher from CrossRef
        crossref = pl.DataFrame(
            {
                "doi": ["10.1/a", "10.1/b"],
                "citation_count": [100, 200],
            }
        )

        # Enricher from PubMed
        pubmed = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "mesh_terms": [["term1"]],
            }
        )

        # Rename
        seed_renamed = renamer.rename_dataframe(seed, "chembl_publication")
        crossref_renamed = renamer.rename_dataframe(crossref, "crossref_publication")
        pubmed_renamed = renamer.rename_dataframe(pubmed, "pubmed_publication")

        # Join
        merged = seed_renamed.join(crossref_renamed, on="doi", how="left")
        merged = merged.join(pubmed_renamed, on="doi", how="left")

        # Order
        ordered = orderer.order_columns(merged)

        # Verify all columns present
        assert "chembl.publication.title" in ordered.columns
        assert "crossref.publication.citation_count" in ordered.columns
        assert "pubmed.publication.mesh_terms" in ordered.columns

        # Verify semantic ordering
        title_idx = ordered.columns.index("chembl.publication.title")
        metrics_idx = ordered.columns.index("crossref.publication.citation_count")
        classification_idx = ordered.columns.index("pubmed.publication.mesh_terms")

        # Title before metrics, metrics before classification
        assert title_idx < metrics_idx < classification_idx


class TestNormalizedJoinKeys:
    """Tests for merge-facing normalized join keys."""

    def test_normalization_enables_provider_join_on_equivalent_doi_variants(
        self,
        renamer: ColumnRenamer,
    ) -> None:
        """Equivalent DOI variants should join only after normalization."""
        raw_seed = pl.DataFrame(
            {
                "doi": [" HTTPS://doi.org/10.1038/NATURE12373 "],
                "title": ["Seed Title"],
            }
        )
        raw_enricher = pl.DataFrame(
            {
                "doi": ["10.1038/nature12373"],
                "citation_count": [100],
            }
        )

        raw_seed_renamed = renamer.rename_dataframe(raw_seed, "chembl_publication")
        raw_enricher_renamed = renamer.rename_dataframe(
            raw_enricher, "crossref_publication"
        )
        raw_joined = raw_seed_renamed.join(raw_enricher_renamed, on="doi", how="left")
        assert raw_joined["crossref.publication.citation_count"].to_list() == [None]

        seed_processor = RecordNormalizationProcessor(provider="chembl")
        enricher_processor = RecordNormalizationProcessor(provider="crossref")
        normalized_seed = pl.DataFrame(
            [
                seed_processor.normalize_record(
                    {
                        "doi": " HTTPS://doi.org/10.1038/NATURE12373 ",
                        "title": "Seed Title",
                    }
                )
            ]
        )
        normalized_enricher = pl.DataFrame(
            [
                enricher_processor.normalize_record(
                    {
                        "doi": "10.1038/nature12373",
                        "citation_count": 100,
                    }
                )
            ]
        )

        normalized_seed_renamed = renamer.rename_dataframe(
            normalized_seed, "chembl_publication"
        )
        normalized_enricher_renamed = renamer.rename_dataframe(
            normalized_enricher, "crossref_publication"
        )
        normalized_joined = normalized_seed_renamed.join(
            normalized_enricher_renamed,
            on="doi",
            how="left",
        )

        assert normalized_joined["doi"].to_list() == ["10.1038/nature12373"]
        assert normalized_joined["crossref.publication.citation_count"].to_list() == [
            100
        ]


class TestQualifiedColumnHandling:
    """Tests for already-qualified column handling."""

    def test_already_qualified_columns_not_double_renamed(
        self, renamer: ColumnRenamer
    ) -> None:
        """Already qualified columns are not renamed again."""
        df = pl.DataFrame(
            {
                "chembl.publication.title": ["Title"],
                "new_field": ["Value"],
            }
        )

        result = renamer.rename_dataframe(df, "crossref_publication")

        # Already qualified should stay the same
        assert "chembl.publication.title" in result.columns
        # New field should be renamed with crossref prefix
        assert "crossref.publication.new_field" in result.columns
        # Should not create double-qualified name
        assert "crossref.publication.chembl.publication.title" not in result.columns

    def test_qualified_columns_grouped_by_field(self, orderer: ColumnOrderer) -> None:
        """Qualified columns are grouped by their field semantic group."""
        df = pl.DataFrame(
            {
                "chembl.publication.title": ["T1"],
                "crossref.publication.abstract": ["A1"],
                "entity_id": ["e1"],
            }
        )

        ordered = orderer.order_columns(df)

        entity_idx = ordered.columns.index("entity_id")
        title_idx = ordered.columns.index("chembl.publication.title")
        abstract_idx = ordered.columns.index("crossref.publication.abstract")

        # entity_id (SYSTEM) < title (TITLE) < abstract (ABSTRACT)
        assert entity_idx < title_idx < abstract_idx
