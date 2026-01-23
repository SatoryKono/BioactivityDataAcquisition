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

        df = pl.DataFrame(
            {
                "doi": ["10.1038/NATURE12373", "10.1000/ABC.DEF"],
                "title": ["Title 1", "Title 2"],
            }
        )

        result = merge_service._normalize_join_key_columns(df, ["doi"])

        assert result["doi"].to_list() == ["10.1038/nature12373", "10.1000/abc.def"]
        # Non-normalized columns should be unchanged
        assert result["title"].to_list() == ["Title 1", "Title 2"]

    def test_normalize_pmid_to_lowercase(self, merge_service):
        """Test PMID column is normalized to lowercase."""
        import polars as pl

        df = pl.DataFrame(
            {
                "pmid": ["12345678", "PMC1234567"],
                "title": ["Title 1", "Title 2"],
            }
        )

        result = merge_service._normalize_join_key_columns(df, ["pmid"])

        assert result["pmid"].to_list() == ["12345678", "pmc1234567"]

    def test_normalize_pmc_id_to_lowercase(self, merge_service):
        """Test PMC_ID column is normalized to lowercase."""
        import polars as pl

        df = pl.DataFrame(
            {
                "pmc_id": ["PMC1234567", "PMC7654321"],
            }
        )

        result = merge_service._normalize_join_key_columns(df, ["pmc_id"])

        assert result["pmc_id"].to_list() == ["pmc1234567", "pmc7654321"]

    def test_normalize_skips_non_identifier_columns(self, merge_service):
        """Test non-identifier columns are not normalized."""
        import polars as pl

        df = pl.DataFrame(
            {
                "title": ["UPPERCASE TITLE", "Another TITLE"],
                "doi": ["10.1038/NATURE", "10.1000/ABC"],
            }
        )

        result = merge_service._normalize_join_key_columns(df, ["title", "doi"])

        # title is not in _NORMALIZE_JOIN_KEYS, so it should be unchanged
        assert result["title"].to_list() == ["UPPERCASE TITLE", "Another TITLE"]
        # doi should be normalized
        assert result["doi"].to_list() == ["10.1038/nature", "10.1000/abc"]

    def test_normalize_handles_null_values(self, merge_service):
        """Test normalization handles null DOI values."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["10.1038/NATURE", None, "10.1000/ABC"],
            }
        )

        result = merge_service._normalize_join_key_columns(df, ["doi"])

        assert result["doi"].to_list() == ["10.1038/nature", None, "10.1000/abc"]

    def test_normalize_returns_unchanged_if_no_normalize_keys(self, merge_service):
        """Test DataFrame is unchanged if no normalizable keys."""
        import polars as pl

        df = pl.DataFrame(
            {
                "id": ["ID1", "ID2"],
                "name": ["Name1", "Name2"],
            }
        )

        result = merge_service._normalize_join_key_columns(df, ["id", "name"])

        # Neither id nor name are in _NORMALIZE_JOIN_KEYS
        assert result["id"].to_list() == ["ID1", "ID2"]
        assert result["name"].to_list() == ["Name1", "Name2"]

    def test_normalize_handles_missing_columns(self, merge_service):
        """Test normalization handles missing columns gracefully."""
        import polars as pl

        df = pl.DataFrame(
            {
                "title": ["Title 1"],
            }
        )

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
        seed_df = pl.DataFrame(
            {
                "id": ["1"],
                "doi": ["10.1038/NATURE12373"],
                "seed_value": ["from_seed"],
            }
        )

        # Enricher has lowercase DOI
        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1038/nature12373"],
                "enricher_value": ["from_enricher"],
            }
        )

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
            silver_table="silver/crossref/publication",
        )

        # When seed_pipeline is provided, uses smart prefix (crossref.)
        result = await merge_service._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Should successfully join despite case difference
        assert len(result) == 1
        # With smart prefix, enricher_value becomes crossref.enricher_value
        assert "crossref.enricher_value" in result.columns
        assert result["crossref.enricher_value"].to_list() == ["from_enricher"]
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


@pytest.mark.unit
class TestParsePipelineName:
    """Tests for _parse_pipeline_name helper."""

    def test_parses_standard_pipeline_name(self, merge_service):
        """Test parsing standard pipeline name."""
        provider, entity = merge_service._parse_pipeline_name("chembl_publication")
        assert provider == "chembl"
        assert entity == "publication"

    def test_parses_pipeline_with_underscore_in_entity(self, merge_service):
        """Test parsing pipeline name with underscore in entity."""
        provider, entity = merge_service._parse_pipeline_name("chembl_target_component")
        assert provider == "chembl"
        assert entity == "target_component"

    def test_raises_on_invalid_format(self, merge_service):
        """Test error on invalid pipeline name format."""
        with pytest.raises(ValueError, match="must be in format"):
            merge_service._parse_pipeline_name("invalidpipelinename")


@pytest.mark.unit
class TestDeterminePrefixStrategy:
    """Tests for _determine_prefix_strategy helper."""

    def test_cross_provider_same_entity(self, merge_service):
        """Test cross-provider merge (same entity, different providers)."""
        strategy = merge_service._determine_prefix_strategy(
            "chembl", "publication", "crossref", "publication"
        )
        assert strategy == "provider"

    def test_cross_entity_same_provider(self, merge_service):
        """Test cross-entity merge (same provider, different entities)."""
        strategy = merge_service._determine_prefix_strategy(
            "chembl", "publication", "chembl", "activity"
        )
        assert strategy == "entity"

    def test_cross_provider_and_entity(self, merge_service):
        """Test cross-provider-entity merge (different both)."""
        strategy = merge_service._determine_prefix_strategy(
            "chembl", "publication", "pubchem", "compound"
        )
        assert strategy == "both"

    def test_same_provider_and_entity(self, merge_service):
        """Test same provider and entity uses pipeline prefix."""
        strategy = merge_service._determine_prefix_strategy(
            "chembl", "publication", "chembl", "publication"
        )
        assert strategy == "pipeline"

    def test_case_insensitive_comparison(self, merge_service):
        """Test provider/entity comparison is case-insensitive."""
        strategy = merge_service._determine_prefix_strategy(
            "ChEMBL", "Publication", "chembl", "publication"
        )
        assert strategy == "pipeline"


@pytest.mark.unit
class TestColumnContainsIdentifier:
    """Tests for _column_contains_identifier helper."""

    def test_contains_identifier_lowercase(self, merge_service):
        """Test identifier match in lowercase."""
        assert merge_service._column_contains_identifier("crossref_doi", "crossref")

    def test_contains_identifier_uppercase(self, merge_service):
        """Test identifier match in uppercase."""
        assert merge_service._column_contains_identifier("CROSSREF.DOI", "crossref")

    def test_does_not_contain_identifier(self, merge_service):
        """Test no match when identifier not present."""
        assert not merge_service._column_contains_identifier("doi", "crossref")

    def test_partial_match(self, merge_service):
        """Test partial match is detected."""
        assert merge_service._column_contains_identifier("chembl_id", "chembl")


@pytest.mark.unit
class TestBuildPrefix:
    """Tests for _build_prefix helper."""

    def test_provider_strategy(self, merge_service):
        """Test prefix for provider strategy."""
        prefix = merge_service._build_prefix(
            "provider", "crossref", "publication", "crossref_publication"
        )
        assert prefix == "crossref"

    def test_entity_strategy(self, merge_service):
        """Test prefix for entity strategy."""
        prefix = merge_service._build_prefix(
            "entity", "chembl", "activity", "chembl_activity"
        )
        assert prefix == "activity"

    def test_both_strategy(self, merge_service):
        """Test prefix for both strategy."""
        prefix = merge_service._build_prefix(
            "both", "pubchem", "compound", "pubchem_compound"
        )
        assert prefix == "pubchem.compound"

    def test_pipeline_strategy(self, merge_service):
        """Test prefix for pipeline strategy (fallback)."""
        prefix = merge_service._build_prefix(
            "pipeline", "chembl", "publication", "chembl_publication"
        )
        assert prefix == "chembl_publication"


@pytest.mark.unit
class TestApplyColumnPrefix:
    """Tests for _apply_column_prefix helper."""

    def test_applies_prefix_to_columns(self, merge_service):
        """Test prefix is applied to specified columns."""
        import polars as pl

        df = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"], "year": [2024]})

        result = merge_service._apply_column_prefix(
            df, {"title", "year"}, "crossref", {"doi"}
        )

        assert "doi" in result.columns
        assert "crossref.title" in result.columns
        assert "crossref.year" in result.columns
        assert "title" not in result.columns
        assert "year" not in result.columns

    def test_excludes_join_keys(self, merge_service):
        """Test join keys are not renamed."""
        import polars as pl

        df = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"]})

        result = merge_service._apply_column_prefix(
            df, {"doi", "title"}, "crossref", {"doi"}
        )

        assert "doi" in result.columns
        assert "crossref.title" in result.columns
        # doi should NOT be renamed
        assert "crossref.doi" not in result.columns


@pytest.mark.unit
class TestDetectAndResolveConflicts:
    """Tests for _detect_and_resolve_conflicts helper."""

    def test_no_conflicts(self, merge_service):
        """Test no changes when no conflicts."""
        import polars as pl

        seed = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"]})
        enricher = pl.DataFrame({"doi": ["10.1/a"], "crossref.author": ["A1"]})

        seed_out, enricher_out = merge_service._detect_and_resolve_conflicts(
            seed, enricher, {"doi"}
        )

        assert seed_out.columns == ["doi", "title"]
        assert enricher_out.columns == ["doi", "crossref.author"]

    def test_resolves_conflicts_with_suffixes(self, merge_service):
        """Test conflicts are resolved with .A/.B suffixes."""
        import polars as pl

        seed = pl.DataFrame({"doi": ["10.1/a"], "crossref.title": ["T1"]})
        enricher = pl.DataFrame({"doi": ["10.1/a"], "crossref.title": ["T2"]})

        seed_out, enricher_out = merge_service._detect_and_resolve_conflicts(
            seed, enricher, {"doi"}
        )

        assert "crossref.title.A" in seed_out.columns
        assert "crossref.title.B" in enricher_out.columns
        assert "crossref.title" not in seed_out.columns
        assert "crossref.title" not in enricher_out.columns

    def test_join_keys_not_affected(self, merge_service):
        """Test join keys are not affected by conflict resolution."""
        import polars as pl

        seed = pl.DataFrame({"doi": ["10.1/a"], "value": ["V1"]})
        enricher = pl.DataFrame({"doi": ["10.1/a"], "value": ["V2"]})

        # doi is join key, value is a conflict
        seed_out, enricher_out = merge_service._detect_and_resolve_conflicts(
            seed, enricher, {"doi"}
        )

        # doi should remain unchanged in both
        assert "doi" in seed_out.columns
        assert "doi" in enricher_out.columns
        # value should be renamed
        assert "value.A" in seed_out.columns
        assert "value.B" in enricher_out.columns


@pytest.mark.unit
class TestApplyJoinsSmartColumnRenaming:
    """Tests for _apply_joins with smart column renaming."""

    @pytest.mark.asyncio
    async def test_cross_provider_merge_uses_provider_prefix(self, merge_service):
        """Test cross-provider merge uses provider name as prefix."""
        import polars as pl

        seed_df = pl.DataFrame({"doi": ["10.1/a"], "title": ["Seed Title"]})
        enricher_df = pl.DataFrame({"doi": ["10.1/a"], "title": ["Crossref Title"]})

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Should have: doi, title, crossref.title
        assert "doi" in result.columns
        assert "title" in result.columns
        assert "crossref.title" in result.columns

    @pytest.mark.asyncio
    async def test_cross_entity_merge_uses_entity_prefix(self, merge_service):
        """Test cross-entity merge uses entity name as prefix."""
        import polars as pl

        seed_df = pl.DataFrame({"chembl_id": ["C1"], "name": ["Drug A"]})
        enricher_df = pl.DataFrame({"chembl_id": ["C1"], "name": ["Activity Name"]})

        enricher_config = EnricherConfig(
            pipeline="chembl_activity",
            join_keys=("chembl_id",),
            required=False,
        )

        result = await merge_service._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"chembl_activity": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Should have: chembl_id, name, activity.name
        assert "chembl_id" in result.columns
        assert "name" in result.columns
        assert "activity.name" in result.columns

    @pytest.mark.asyncio
    async def test_cross_provider_entity_merge_uses_both_prefix(self, merge_service):
        """Test cross-provider-entity merge uses provider.entity prefix."""
        import polars as pl

        seed_df = pl.DataFrame({"id": ["1"], "name": ["Seed Name"]})
        enricher_df = pl.DataFrame({"id": ["1"], "name": ["Compound Name"]})

        enricher_config = EnricherConfig(
            pipeline="pubchem_compound",
            join_keys=("id",),
            required=False,
        )

        result = await merge_service._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"pubchem_compound": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Should have: id, name, pubchem.compound.name
        assert "id" in result.columns
        assert "name" in result.columns
        assert "pubchem.compound.name" in result.columns

    @pytest.mark.asyncio
    async def test_skips_already_prefixed_columns(self, merge_service):
        """Test columns already containing identifier are not re-prefixed."""
        import polars as pl

        seed_df = pl.DataFrame({"doi": ["10.1/a"], "title": ["Seed"]})
        # crossref_doi already contains "crossref"
        enricher_df = pl.DataFrame(
            {"doi": ["10.1/a"], "crossref_doi": ["10.1/a"], "author": ["A1"]}
        )

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # crossref_doi should NOT become crossref.crossref_doi
        assert "crossref_doi" in result.columns
        assert "crossref.crossref_doi" not in result.columns
        # author should become crossref.author
        assert "crossref.author" in result.columns

    @pytest.mark.asyncio
    async def test_conflict_after_prefixing_gets_suffixes(self, merge_service):
        """Test conflict after prefixing gets .A/.B suffixes."""
        import polars as pl

        # Seed already has crossref.title
        seed_df = pl.DataFrame({"doi": ["10.1/a"], "crossref.title": ["Seed CT"]})
        # Enricher title becomes crossref.title → conflict!
        enricher_df = pl.DataFrame({"doi": ["10.1/a"], "title": ["Enricher Title"]})

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Conflict resolved with .A/.B suffixes
        assert "crossref.title.A" in result.columns
        assert "crossref.title.B" in result.columns

    @pytest.mark.asyncio
    async def test_legacy_prefix_when_no_seed_pipeline(self, merge_service):
        """Test legacy prefix when seed_pipeline not provided."""
        import polars as pl

        seed_df = pl.DataFrame({"doi": ["10.1/a"], "title": ["Seed Title"]})
        enricher_df = pl.DataFrame({"doi": ["10.1/a"], "title": ["Enricher Title"]})

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline=None,  # No seed pipeline
        )

        # Should use legacy prefix: crossref_publication_title
        assert "crossref_publication_title" in result.columns


@pytest.mark.unit
class TestGetEnricherPrefix:
    """Tests for _get_enricher_prefix helper."""

    def test_cross_provider_prefix(self, merge_service):
        """Test cross-provider prefix ends with dot."""
        prefix = merge_service._get_enricher_prefix(
            "crossref_publication", "chembl_publication"
        )
        assert prefix == "crossref."

    def test_cross_entity_prefix(self, merge_service):
        """Test cross-entity prefix ends with dot."""
        prefix = merge_service._get_enricher_prefix(
            "chembl_activity", "chembl_publication"
        )
        assert prefix == "activity."

    def test_cross_both_prefix(self, merge_service):
        """Test cross-both prefix ends with dot."""
        prefix = merge_service._get_enricher_prefix(
            "pubchem_compound", "chembl_publication"
        )
        assert prefix == "pubchem.compound."

    def test_legacy_prefix_when_no_seed(self, merge_service):
        """Test legacy prefix when seed is None."""
        prefix = merge_service._get_enricher_prefix("crossref_publication", None)
        assert prefix == "crossref_publication_"


@pytest.mark.unit
class TestExtractBaseColumn:
    """Tests for _extract_base_column helper."""

    def test_extracts_base_from_dot_prefix(self, merge_service):
        """Test extraction from dot-based prefix."""
        base = merge_service._extract_base_column("crossref.title", "crossref.")
        assert base == "title"

    def test_extracts_base_from_legacy_prefix(self, merge_service):
        """Test extraction from legacy underscore prefix."""
        base = merge_service._extract_base_column(
            "crossref_publication_title", "crossref_publication_"
        )
        assert base == "title"

    def test_returns_none_for_no_match(self, merge_service):
        """Test returns None when prefix doesn't match."""
        base = merge_service._extract_base_column("title", "crossref.")
        assert base is None


@pytest.mark.unit
class TestInferPipelineFromTable:
    """Tests for _infer_pipeline_from_table helper."""

    def test_infers_from_silver_path(self, merge_service):
        """Test inferring pipeline from silver table path."""
        pipeline = merge_service._infer_pipeline_from_table("silver/chembl/publication")
        assert pipeline == "chembl_publication"

    def test_infers_from_absolute_path(self, merge_service):
        """Test inferring pipeline from absolute path."""
        pipeline = merge_service._infer_pipeline_from_table(
            "/data/output/silver/crossref/publication"
        )
        assert pipeline == "crossref_publication"

    def test_returns_none_for_invalid_path(self, merge_service):
        """Test returns None for path without layer prefix."""
        pipeline = merge_service._infer_pipeline_from_table("invalid/path")
        assert pipeline is None


@pytest.mark.unit
class TestCheckDuplicates:
    """Tests for _check_duplicates helper."""

    def test_no_duplicates(self, merge_service):
        """Test returns False when no duplicates."""
        import polars as pl

        df = pl.DataFrame({"doi": ["a", "b", "c"], "val": [1, 2, 3]})
        assert merge_service._check_duplicates(df, ["doi"]) is False

    def test_has_duplicates(self, merge_service):
        """Test returns True when duplicates exist."""
        import polars as pl

        df = pl.DataFrame({"doi": ["a", "a", "b"], "val": [1, 2, 3]})
        assert merge_service._check_duplicates(df, ["doi"]) is True

    def test_empty_dataframe(self, merge_service):
        """Test returns False for empty DataFrame."""
        import polars as pl

        df = pl.DataFrame({"doi": [], "val": []}).cast({"doi": pl.String, "val": pl.Int64})
        assert merge_service._check_duplicates(df, ["doi"]) is False

    def test_missing_key_column(self, merge_service):
        """Test returns False when key column doesn't exist."""
        import polars as pl

        df = pl.DataFrame({"val": [1, 2, 3]})
        assert merge_service._check_duplicates(df, ["doi"]) is False

    def test_composite_key(self, merge_service):
        """Test composite key detection."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a", "a"],
            "pmid": ["1", "1", "2"],
            "val": [1, 2, 3],
        })
        # (a, 1) and (a, 2) are unique composite keys, but (a, 1) has duplicate
        # Wait, actually: (a, 1), (a, 1), (a, 2) → (a, 1) is duplicated
        assert merge_service._check_duplicates(df, ["doi", "pmid"]) is True

        # No duplicates
        df2 = pl.DataFrame({
            "doi": ["a", "a", "b"],
            "pmid": ["1", "2", "1"],
            "val": [1, 2, 3],
        })
        assert merge_service._check_duplicates(df2, ["doi", "pmid"]) is False


@pytest.mark.unit
class TestDeduplicateEnricher:
    """Tests for _deduplicate_enricher and related helpers."""

    def test_no_duplicates_returns_unchanged(self, merge_service):
        """Test no duplicates returns DataFrame unchanged."""
        import polars as pl

        df = pl.DataFrame({"doi": ["a", "b"], "title": ["T1", "T2"]})
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert result.equals(df)

    def test_identical_values_preserves_type(self, merge_service):
        """Test identical values preserve original type."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a", "b"],
            "title": ["Same", "Same", "Other"],
            "count": [10, 10, 20],
        })
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert len(result) == 2
        row_a = result.filter(pl.col("doi") == "a")
        assert row_a["title"][0] == "Same"
        assert row_a["count"][0] == 10
        # Type should be preserved
        assert row_a["count"].dtype == pl.Int64

    def test_different_values_concatenated(self, merge_service):
        """Test different values are concatenated with |."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a", "b"],
            "title": ["T1", "T2", "T3"],
            "count": [10, 20, 30],
        })
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert len(result) == 2
        row_a = result.filter(pl.col("doi") == "a")
        assert row_a["title"][0] == "T1|T2"
        assert row_a["count"][0] == "10|20"

    def test_all_null_remains_null(self, merge_service):
        """Test all null values remain null."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a"],
            "title": [None, None],
        })
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert len(result) == 1
        assert result["title"][0] is None

    def test_mixed_null_values(self, merge_service):
        """Test mixed null and values include null as string."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a", "a"],
            "title": ["T1", None, "T2"],
        })
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert len(result) == 1
        # Values sorted: T1, T2, null → should be T1|T2|null
        assert result["title"][0] == "T1|T2|null"

    def test_single_value_plus_null(self, merge_service):
        """Test single value plus null are concatenated."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a"],
            "title": ["Same", None],
        })
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert len(result) == 1
        assert result["title"][0] == "Same|null"

    def test_numeric_with_null(self, merge_service):
        """Test numeric values with null."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a", "a"],
            "count": [10, None, 20],
        })
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert len(result) == 1
        assert result["count"][0] == "10|20|null"

    def test_boolean_values(self, merge_service):
        """Test boolean values are converted to lowercase strings."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a"],
            "is_oa": [True, False],
        })
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert len(result) == 1
        # Sorted: false, true
        assert result["is_oa"][0] == "false|true"

    def test_date_values(self, merge_service):
        """Test date values are converted to ISO format."""
        import polars as pl
        from datetime import date

        df = pl.DataFrame({
            "doi": ["a", "a"],
            "pub_date": [date(2024, 1, 1), date(2024, 6, 15)],
        })
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert len(result) == 1
        assert result["pub_date"][0] == "2024-01-01|2024-06-15"

    def test_composite_key(self, merge_service):
        """Test deduplication with composite key."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a", "a"],
            "pmid": ["1", "1", "2"],
            "val": ["X", "Y", "Z"],
        })
        result = merge_service._deduplicate_enricher(df, ["doi", "pmid"], "test")
        assert len(result) == 2
        row_a1 = result.filter((pl.col("doi") == "a") & (pl.col("pmid") == "1"))
        assert row_a1["val"][0] == "X|Y"

    def test_empty_dataframe(self, merge_service):
        """Test empty DataFrame returns unchanged."""
        import polars as pl

        df = pl.DataFrame({"doi": [], "title": []}).cast(
            {"doi": pl.String, "title": pl.String}
        )
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert len(result) == 0

    def test_duplicate_values_in_group_deduplicated(self, merge_service):
        """Test duplicate values within a group are removed."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a", "a"],
            "title": ["Same", "Same", "Different"],
        })
        result = merge_service._deduplicate_enricher(df, ["doi"], "test")
        assert len(result) == 1
        # unique values sorted: Different, Same
        assert result["title"][0] == "Different|Same"

    def test_logs_warning_on_duplicates(self, merge_service, mock_logger):
        """Test warning is logged when duplicates are found."""
        import polars as pl

        df = pl.DataFrame({
            "doi": ["a", "a"],
            "title": ["T1", "T2"],
        })
        merge_service._deduplicate_enricher(df, ["doi"], "test_enricher")

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["enricher"] == "test_enricher"
        assert call_kwargs["join_keys"] == ["doi"]
        assert call_kwargs["duplicate_count"] == 1
        assert "title" in call_kwargs["columns_with_conflicts"]


@pytest.mark.unit
class TestApplyJoinsWithDeduplication:
    """Tests for _apply_joins with enricher deduplication."""

    @pytest.mark.asyncio
    async def test_deduplicates_enricher_before_join(self, merge_service):
        """Test enricher is deduplicated before join to prevent fan-out."""
        import polars as pl

        # Seed has 2 unique DOIs
        seed_df = pl.DataFrame({
            "doi": ["10.1/aaa", "10.1/bbb"],
            "title": ["Study A", "Study B"],
        })

        # Enricher has duplicates for 10.1/aaa
        enricher_df = pl.DataFrame({
            "doi": ["10.1/aaa", "10.1/aaa", "10.1/bbb"],
            "citation_count": [150, 200, 50],
        })

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Result should have exactly 2 rows (no fan-out)
        assert len(result) == 2

        # Citation count for aaa should be aggregated
        row_aaa = result.filter(pl.col("doi") == "10.1/aaa")
        assert "150|200" in str(row_aaa["crossref.citation_count"][0])

        # Citation count for bbb - no duplicates, but column type is String
        # because other groups have conflicts (Polars requires uniform column type)
        row_bbb = result.filter(pl.col("doi") == "10.1/bbb")
        assert row_bbb["crossref.citation_count"][0] == "50"

    @pytest.mark.asyncio
    async def test_no_deduplication_when_no_duplicates(self, merge_service, mock_logger):
        """Test no deduplication overhead when enricher has no duplicates."""
        import polars as pl

        seed_df = pl.DataFrame({
            "doi": ["10.1/aaa", "10.1/bbb"],
            "title": ["Study A", "Study B"],
        })

        enricher_df = pl.DataFrame({
            "doi": ["10.1/aaa", "10.1/bbb"],
            "citation_count": [150, 50],
        })

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        await merge_service._apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Warning should NOT be called (no duplicates)
        for call in mock_logger.warning.call_args_list:
            # Check that we didn't log about duplicate aggregation
            if call[0] and "Duplicates aggregated" in str(call[0][0]):
                pytest.fail("Should not log duplicate warning when no duplicates")


@pytest.mark.unit
class TestConvertToStringForConcat:
    """Tests for _convert_to_string_for_concat helper."""

    def test_string_type(self, merge_service):
        """Test string type is passed through."""
        import polars as pl

        df = pl.DataFrame({"col": ["a", "b"]})
        expr = merge_service._convert_to_string_for_concat("col", pl.String)
        result = df.select(expr.alias("result"))
        assert result["result"].to_list() == ["a", "b"]

    def test_int_type(self, merge_service):
        """Test int type is cast to string."""
        import polars as pl

        df = pl.DataFrame({"col": [10, 20]})
        expr = merge_service._convert_to_string_for_concat("col", pl.Int64)
        result = df.select(expr.alias("result"))
        assert result["result"].to_list() == ["10", "20"]

    def test_float_type(self, merge_service):
        """Test float type is cast to string."""
        import polars as pl

        df = pl.DataFrame({"col": [1.5, 2.5]})
        expr = merge_service._convert_to_string_for_concat("col", pl.Float64)
        result = df.select(expr.alias("result"))
        assert result["result"].to_list() == ["1.5", "2.5"]

    def test_boolean_type(self, merge_service):
        """Test boolean type is converted to lowercase."""
        import polars as pl

        df = pl.DataFrame({"col": [True, False]})
        expr = merge_service._convert_to_string_for_concat("col", pl.Boolean)
        result = df.select(expr.alias("result"))
        assert result["result"].to_list() == ["true", "false"]

    def test_date_type(self, merge_service):
        """Test date type is converted to ISO format."""
        import polars as pl
        from datetime import date

        df = pl.DataFrame({"col": [date(2024, 1, 15), date(2024, 6, 30)]})
        expr = merge_service._convert_to_string_for_concat("col", pl.Date)
        result = df.select(expr.alias("result"))
        assert result["result"].to_list() == ["2024-01-15", "2024-06-30"]
