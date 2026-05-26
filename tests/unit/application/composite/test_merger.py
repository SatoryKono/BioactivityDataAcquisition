"""Unit tests for MergeService."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import cache
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.composite.config import DependencyConfig, EnricherConfig, MergeConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.domain.exceptions import BioETLError
from tests.helpers.clock import FixedClock
from tests.unit.application.composite.merge_test_support import build_merge_service

if TYPE_CHECKING:
    from bioetl.application.composite.merger import (
        MergeCollaboratorGroup,
        MergeService,
    )


@cache
def _merge_runtime_symbols() -> dict[str, object]:
    """Load composite runtime helpers lazily to reduce module-scope import cost."""
    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.application.composite.merger import (
        MergeCollaboratorGroup,
        MergeService,
        _path_to_table_name,
    )

    return {
        "EnricherAggregator": EnricherAggregator,
        "EnricherDeduplicatorService": EnricherDeduplicatorService,
        "MergeCollaboratorGroup": MergeCollaboratorGroup,
        "MergeService": MergeService,
        "_path_to_table_name": _path_to_table_name,
    }


def _merge_service_cls() -> type[MergeService]:
    return _merge_runtime_symbols()["MergeService"]  # type: ignore[return-value]


def _merge_collaborator_group_cls() -> type[MergeCollaboratorGroup]:
    return _merge_runtime_symbols()["MergeCollaboratorGroup"]  # type: ignore[return-value]


def _path_to_table_name_helper(path: str) -> str:
    helper = _merge_runtime_symbols()["_path_to_table_name"]
    return helper(path)  # type: ignore[misc, operator]


@pytest.fixture
def mock_storage():
    """Create a mock merged storage port."""
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
def deduplicator(mock_logger):
    """Create an EnricherDeduplicatorService instance."""
    deduplicator_cls = _merge_runtime_symbols()["EnricherDeduplicatorService"]
    return deduplicator_cls(mock_logger)  # type: ignore[misc, operator]


@pytest.fixture
def aggregator(mock_logger):
    """Create an EnricherAggregator instance."""
    aggregator_cls = _merge_runtime_symbols()["EnricherAggregator"]
    return aggregator_cls(mock_logger)  # type: ignore[misc, operator]


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
    return build_merge_service(
        merge_config=merge_config,
        logger=mock_logger,
        storage=mock_storage,
        gold_schema=MagicMock(),
    )


@pytest.mark.unit
def test_merge_service_accepts_injected_internal_components(
    merge_config,
    mock_storage,
    mock_logger,
):
    """MergeService should allow overriding internally constructed collaborators."""
    deduplicator = MagicMock()
    aggregator = MagicMock()
    renamer = MagicMock()
    order_service = MagicMock()
    priority_orderer = MagicMock()
    order_service._priority_orderer = priority_orderer
    coalesce_policy = MagicMock()
    conflict_resolver = MagicMock()
    join_planner = MagicMock()

    service = _merge_service_cls()(
        merge_config=merge_config,
        storage=mock_storage,
        logger=mock_logger,
        clock=FixedClock(datetime(2026, 4, 28, 12, 0, tzinfo=UTC)),
        collaborators=_merge_collaborator_group_cls()(
            deduplicator=deduplicator,
            aggregator=aggregator,
            renamer=renamer,
            order_service=order_service,
            coalesce_policy=coalesce_policy,
            conflict_resolver=conflict_resolver,
            join_planner=join_planner,
        ),
    )

    assert service._deduplicator is deduplicator
    assert service._aggregator is aggregator
    assert service._renamer is renamer
    assert service._order_service is order_service
    assert service._priority_orderer is priority_orderer
    assert service._coalesce_policy is coalesce_policy
    assert service._conflict_resolver is conflict_resolver
    assert service._join_planner is join_planner


@pytest.mark.unit
class TestPathToTableName:
    """Tests for _path_to_table_name helper."""

    def test_strips_silver_prefix(self):
        """Test silver prefix is stripped."""
        assert _path_to_table_name_helper("silver/chembl/activity") == "chembl/activity"

    def test_strips_gold_prefix(self):
        """Test gold prefix is stripped."""
        assert (
            _path_to_table_name_helper("gold/publication_enriched")
            == "publication_enriched"
        )

    def test_strips_bronze_prefix(self):
        """Test bronze prefix is stripped."""
        assert _path_to_table_name_helper("bronze/provider/entity") == "provider/entity"

    def test_returns_unchanged_if_no_prefix(self):
        """Test path without prefix is unchanged."""
        assert _path_to_table_name_helper("some/path") == "some/path"


@pytest.mark.unit
class TestMergeServiceReadsSilverViaStorage:
    """Tests for MergeService reading Silver via SilverStoragePort."""

    @pytest.mark.asyncio
    async def test_prepare_seed_dataframe_returns_named_context(
        self, merge_service, mock_storage
    ) -> None:
        """Seed preparation should return an explicit prepared context."""
        mock_storage.read_silver.return_value = [
            {"id": "1", "val": "A"},
            {"id": "2", "val": "B"},
        ]

        prepared = await merge_service._prepare_seed_dataframe(
            "silver/test/table",
            "test_publication",
        )

        assert prepared.records_from_seed == 2
        assert prepared.effective_seed_pipeline == "test_publication"
        assert prepared.seed_df.height == 2

    @pytest.mark.asyncio
    async def test_read_silver_uses_storage_port(self, merge_service, mock_storage):
        """Test _read_silver_table uses SilverStoragePort.read_silver."""
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

    @pytest.mark.asyncio
    async def test_read_silver_requires_reader_when_all_readers_missing(
        self, merge_service
    ) -> None:
        """Missing delta_reader and silver_reader should raise explicit runtime error."""
        merge_service._delta_reader = None
        merge_service._silver_reader = None

        with pytest.raises(
            RuntimeError, match="requires delta_reader or silver_reader"
        ):
            await merge_service._read_silver_table("silver/test/table")


@pytest.mark.unit
class TestMergeServiceWritesViaStorage:
    """Tests for MergeService writing via MergedStoragePort."""

    @pytest.mark.asyncio
    async def test_write_merged_silver_uses_storage_port(
        self, merge_service, mock_storage
    ):
        """Test _write_merged_silver uses MergedStoragePort.write_silver_merged."""
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
        """Test _write_merged_gold uses MergedStoragePort.write_gold_merged."""
        import polars as pl

        df = pl.DataFrame({"id": ["1", "2"], "val": ["A", "B"]})

        await merge_service._write_merged_gold(df)

        mock_storage.write_gold_merged.assert_called_once()
        call_args = mock_storage.write_gold_merged.call_args
        assert call_args[0][0] == "test_merged"  # table_name from output_gold_path


@pytest.mark.unit
class TestMergeServiceJoinKeyNormalization:
    """Tests for join key normalization (case-insensitive DOI/PMID matching)."""

    def test_normalize_doi_with_trim_and_lowercase(self, merge_service):
        """Test DOI column is normalized with trim and lowercase."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": [" 10.1038/NATURE12373 ", "10.1000/ABC.DEF"],
                "title": ["Title 1", "Title 2"],
            }
        )

        result = merge_service._join_planner.normalize_join_key_columns(
            df, ["doi"], None
        )

        assert result["doi"].to_list() == ["10.1038/nature12373", "10.1000/abc.def"]
        # Non-normalized columns should be unchanged
        assert result["title"].to_list() == ["Title 1", "Title 2"]

    def test_normalize_pmid_validates_family_before_join_canonicalization(
        self, merge_service
    ):
        """Test PMID column keeps digits-only IDs and nulls wrong-family identifiers."""
        import polars as pl

        df = pl.DataFrame(
            {
                "pmid": ["12345678", "PMC1234567"],
                "title": ["Title 1", "Title 2"],
            }
        )

        result = merge_service._join_planner.normalize_join_key_columns(
            df, ["pmid"], None
        )

        assert result["pmid"].to_list() == ["12345678", None]

    def test_normalize_pmc_id_to_lowercase(self, merge_service):
        """Test PMC_ID column is normalized to lowercase."""
        import polars as pl

        df = pl.DataFrame(
            {
                "pmc_id": ["PMC1234567", "PMC7654321"],
            }
        )

        result = merge_service._join_planner.normalize_join_key_columns(
            df, ["pmc_id"], None
        )

        assert result["pmc_id"].to_list() == ["pmc1234567", "pmc7654321"]

    def test_normalize_title_cleans_without_lowercasing(self, merge_service):
        """Test title join keys use canonical title cleanup but keep casing."""
        import polars as pl

        df = pl.DataFrame(
            {
                "title": ["  <b>UPPERCASE</b>&nbsp;TITLE  ", " Another\nTITLE"],
                "doi": ["10.1038/NATURE", "10.1000/ABC"],
            }
        )

        result = merge_service._join_planner.normalize_join_key_columns(
            df, ["title", "doi"], None
        )

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

        result = merge_service._join_planner.normalize_join_key_columns(
            df, ["doi"], None
        )

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

        result = merge_service._join_planner.normalize_join_key_columns(
            df, ["id", "name"], None
        )

        # Neither id nor name has an explicit normalization policy
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
        result = merge_service._join_planner.normalize_join_key_columns(
            df, ["doi", "title"], None
        )

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
        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Should successfully join despite case difference
        assert len(result) == 1
        # With qualified naming, enricher_value becomes crossref.publication.enricher_value
        assert "crossref.publication.enricher_value" in result.columns
        assert result["crossref.publication.enricher_value"].to_list() == [
            "from_enricher"
        ]
        # DOI should be normalized to lowercase
        assert result["doi"].to_list() == ["10.1038/nature12373"]


@pytest.mark.unit
class TestMergeServiceMergeOperation:
    """Tests for MergeService.merge operation."""

    @pytest.mark.asyncio
    async def test_merge_calls_read_and_write(self, merge_service, mock_storage):
        """Test merge calls read and write via narrow storage ports."""
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

        def read_side_effect(table_name):
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
class TestMergeServiceOptionalReadPolicy:
    """Tests for optional merge input read degradation."""

    @pytest.mark.asyncio
    async def test_load_enricher_dataframes_skips_failed_read(
        self, merge_service, mock_storage, mock_logger
    ) -> None:
        """Successful enricher result should be dropped when table read fails."""
        mock_storage.read_silver.side_effect = OSError("disk issue")

        enrichers = [
            EnricherConfig(
                pipeline="crossref_publication",
                join_keys=("doi",),
                required=False,
                silver_table="silver/crossref/publication",
            )
        ]
        enrichment_results = {
            "crossref_publication": EnrichmentResult(
                enricher_name="crossref_publication",
                status=EnrichmentStatus.SUCCESS,
                records_input=1,
                records_enriched=1,
            )
        }

        enricher_dfs, sources = await merge_service._load_enricher_dataframes(
            enrichers,
            enrichment_results,
        )

        assert enricher_dfs == {}
        assert sources == []
        mock_logger.warning.assert_called_once()
        assert (
            mock_logger.warning.call_args.kwargs["enricher"] == "crossref_publication"
        )

    @pytest.mark.asyncio
    async def test_load_dependency_dataframes_skips_failed_read_with_reason_code(
        self, merge_service, mock_storage, mock_logger
    ) -> None:
        """BioETLError read failure should be logged and degraded for dependencies."""
        mock_storage.read_silver.side_effect = BioETLError("delta read failed")

        dependencies = [
            DependencyConfig(
                pipeline="chembl_target_component",
                silver_table="silver/chembl/target_component",
                join_keys=("target_chembl_id",),
                required=False,
            )
        ]
        dependency_results = {
            "chembl_target_component": DependencyResult(
                pipeline_name="chembl_target_component",
                status=DependencyStatus.SUCCESS,
                records_extracted=1,
                records_silver=1,
            )
        }

        dependency_dfs, sources = await merge_service._load_dependency_dataframes(
            dependencies,
            dependency_results,
        )

        assert dependency_dfs == {}
        assert sources == []
        mock_logger.warning.assert_called_once()
        warning_kwargs = mock_logger.warning.call_args.kwargs
        assert warning_kwargs["dependency"] == "chembl_target_component"
        assert warning_kwargs.get("reason_code") == "unexpected_bioetl_error"


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
class TestDetectAndResolveConflicts:
    """Tests for _detect_and_resolve_conflicts helper."""

    def test_no_conflicts(self, merge_service):
        """Test no changes when no conflicts."""
        import polars as pl

        seed = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"]})
        enricher = pl.DataFrame({"doi": ["10.1/a"], "crossref.author": ["A1"]})

        seed_out, enricher_out = (
            merge_service._conflict_resolver.detect_and_resolve_conflicts(
                seed, enricher, {"doi"}
            )
        )

        assert seed_out.columns == ["doi", "title"]
        assert enricher_out.columns == ["doi", "crossref.author"]

    def test_resolves_conflicts_with_suffixes(self, merge_service):
        """Test conflicts are resolved: seed unchanged, enricher gets suffix."""
        import polars as pl

        seed = pl.DataFrame({"doi": ["10.1/a"], "crossref.title": ["T1"]})
        enricher = pl.DataFrame({"doi": ["10.1/a"], "crossref.title": ["T2"]})

        seed_out, enricher_out = (
            merge_service._conflict_resolver.detect_and_resolve_conflicts(
                seed, enricher, {"doi"}
            )
        )

        # Seed columns remain unchanged
        assert "crossref.title" in seed_out.columns
        # Enricher gets incremental suffix
        assert "crossref.title.A" in enricher_out.columns
        assert "crossref.title" not in enricher_out.columns

    def test_join_keys_not_affected(self, merge_service):
        """Test join keys are not affected by conflict resolution."""
        import polars as pl

        seed = pl.DataFrame({"doi": ["10.1/a"], "value": ["V1"]})
        enricher = pl.DataFrame({"doi": ["10.1/a"], "value": ["V2"]})

        # doi is join key, value is a conflict
        seed_out, enricher_out = (
            merge_service._conflict_resolver.detect_and_resolve_conflicts(
                seed, enricher, {"doi"}
            )
        )

        # doi should remain unchanged in both
        assert "doi" in seed_out.columns
        assert "doi" in enricher_out.columns
        # seed value unchanged, enricher value gets suffix
        assert "value" in seed_out.columns
        assert "value.A" in enricher_out.columns

    def test_find_next_suffix_basic(self, merge_service):
        """Test _find_next_suffix returns first available suffix."""
        # No existing suffixes → returns A
        assert (
            merge_service._conflict_resolver.find_next_suffix("title", {"title"}) == "A"
        )
        # A exists → returns B
        assert (
            merge_service._conflict_resolver.find_next_suffix(
                "title", {"title", "title.A"}
            )
            == "B"
        )
        # A, B exist → returns C
        assert (
            merge_service._conflict_resolver.find_next_suffix(
                "title", {"title", "title.A", "title.B"}
            )
            == "C"
        )

    def test_incremental_suffixes_multiple_enrichers(self, merge_service):
        """Test incremental suffixes when multiple enrichers conflict."""
        import polars as pl

        # Seed with a column that will conflict
        seed = pl.DataFrame({"doi": ["10.1/a"], "pub_date": ["2024-01-01"]})

        # First enricher conflict
        enricher1 = pl.DataFrame({"doi": ["10.1/a"], "pub_date": ["2024-02-01"]})
        seed_out1, enricher_out1 = (
            merge_service._conflict_resolver.detect_and_resolve_conflicts(
                seed, enricher1, {"doi"}
            )
        )
        assert "pub_date" in seed_out1.columns  # Seed unchanged
        assert "pub_date.A" in enricher_out1.columns  # First enricher gets A

        # Simulate merged state after first join
        merged = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "pub_date": ["2024-01-01"],
                "pub_date.A": ["2024-02-01"],
            }
        )

        # Second enricher conflict - should get B suffix
        enricher2 = pl.DataFrame({"doi": ["10.1/a"], "pub_date": ["2024-03-01"]})
        merged_out, enricher_out2 = (
            merge_service._conflict_resolver.detect_and_resolve_conflicts(
                merged, enricher2, {"doi"}
            )
        )
        assert "pub_date" in merged_out.columns  # Original seed column unchanged
        assert "pub_date.A" in merged_out.columns  # First enricher column unchanged
        assert "pub_date.B" in enricher_out2.columns  # Second enricher gets B


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

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Should have: doi, title, crossref.publication.title (qualified name)
        assert "doi" in result.columns
        assert "title" in result.columns
        assert "crossref.publication.title" in result.columns

    @pytest.mark.asyncio
    async def test_cross_entity_merge_uses_entity_prefix(self, merge_service):
        """Test cross-entity merge uses qualified name as prefix."""
        import polars as pl

        # Use doi as join key since it's in JOIN_KEY_COLUMNS and won't be renamed
        seed_df = pl.DataFrame({"doi": ["10.1/a"], "name": ["Drug A"]})
        enricher_df = pl.DataFrame({"doi": ["10.1/a"], "name": ["Activity Name"]})

        enricher_config = EnricherConfig(
            pipeline="chembl_activity",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"chembl_activity": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Should have: doi, name, chembl.activity.name (qualified name)
        assert "doi" in result.columns
        assert "name" in result.columns
        assert "chembl.activity.name" in result.columns

    @pytest.mark.asyncio
    async def test_cross_provider_entity_merge_uses_both_prefix(self, merge_service):
        """Test cross-provider-entity merge uses provider.entity prefix."""
        import polars as pl

        # Use doi as join key since it's in JOIN_KEY_COLUMNS and won't be renamed
        seed_df = pl.DataFrame({"doi": ["10.1/a"], "name": ["Seed Name"]})
        enricher_df = pl.DataFrame({"doi": ["10.1/a"], "name": ["Compound Name"]})

        enricher_config = EnricherConfig(
            pipeline="pubchem_compound",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"pubchem_compound": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Should have: doi, name, pubchem.compound.name
        assert "doi" in result.columns
        assert "name" in result.columns
        assert "pubchem.compound.name" in result.columns

    @pytest.mark.asyncio
    async def test_skips_already_prefixed_columns(self, merge_service):
        """Test columns already in qualified format are not re-prefixed."""
        import polars as pl

        seed_df = pl.DataFrame({"doi": ["10.1/a"], "title": ["Seed"]})
        # crossref.publication.extra is already qualified
        enricher_df = pl.DataFrame(
            {"doi": ["10.1/a"], "crossref.publication.extra": ["E1"], "author": ["A1"]}
        )

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Already qualified column stays unchanged
        assert "crossref.publication.extra" in result.columns
        # author should become crossref.publication.author (qualified)
        assert "crossref.publication.author" in result.columns

    @pytest.mark.asyncio
    async def test_conflict_after_prefixing_gets_suffixes(self, merge_service):
        """Test conflict after prefixing: seed unchanged, enricher gets suffix."""
        import polars as pl

        # Seed already has crossref.publication.title
        seed_df = pl.DataFrame(
            {"doi": ["10.1/a"], "crossref.publication.title": ["Seed CT"]}
        )
        # Enricher title becomes crossref.publication.title → conflict!
        enricher_df = pl.DataFrame({"doi": ["10.1/a"], "title": ["Enricher Title"]})

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Seed column unchanged, enricher gets incremental suffix
        assert "crossref.publication.title" in result.columns
        assert "crossref.publication.title.A" in result.columns

    @pytest.mark.asyncio
    async def test_secondary_join_keys_are_prefixed(self, merge_service):
        """Test secondary join keys (not used in actual join) are prefixed.

        When join_keys has multiple values, only the first (primary) key is used
        for the actual join. Secondary keys should be prefixed to avoid Polars
        adding its own suffix.
        """
        import polars as pl

        # Seed has both doi and title
        seed_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "title": ["Seed Title"],
                "abstract": ["Seed Abstract"],
            }
        )
        # Enricher also has doi and title - title is secondary join key
        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "title": ["CrossRef Title"],
                "citation_count": [42],
            }
        )

        # title is listed as secondary join key but NOT used in actual join
        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi", "title"),  # doi is primary, title is secondary
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Primary key (doi) is used for join - single column in result
        assert "doi" in result.columns
        assert result.columns.count("doi") == 1

        # Secondary key (title) should be prefixed, NOT get Polars suffix
        assert "title" in result.columns  # Seed title
        assert (
            "crossref.publication.title" in result.columns
        )  # Enricher title with qualified name
        assert "title_crossref_publication" not in result.columns  # NO Polars suffix

        # Regular columns should also be prefixed with qualified name
        assert "crossref.publication.citation_count" in result.columns
        # Enricher DOI preserved as qualified data column
        assert "crossref.publication.doi" in result.columns

    @pytest.mark.asyncio
    async def test_multiple_enrichers_secondary_keys_prefixed(self, merge_service):
        """Test multiple enrichers with secondary join keys all get prefixed."""
        import polars as pl

        seed_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "title": ["Seed Title"],
            }
        )

        crossref_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "title": ["CrossRef Title"],
            }
        )

        openalex_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "title": ["OpenAlex Title"],
            }
        )

        enrichers = [
            EnricherConfig(
                pipeline="crossref_publication",
                join_keys=("doi", "title"),
                required=False,
            ),
            EnricherConfig(
                pipeline="openalex_publication",
                join_keys=("doi", "title"),
                required=False,
            ),
        ]

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={
                "crossref_publication": crossref_df,
                "openalex_publication": openalex_df,
            },
            enrichers=enrichers,
            seed_pipeline="chembl_publication",
        )

        # Seed title unchanged
        assert "title" in result.columns
        # Each enricher's title is prefixed with qualified name
        assert "crossref.publication.title" in result.columns
        assert "openalex.publication.title" in result.columns
        # NO Polars suffixes
        assert "title_crossref_publication" not in result.columns
        assert "title_openalex_publication" not in result.columns

    @pytest.mark.asyncio
    async def test_qualified_prefix_when_no_seed_pipeline(self, merge_service):
        """Test qualified prefix even when seed_pipeline not provided."""
        import polars as pl

        seed_df = pl.DataFrame({"doi": ["10.1/a"], "title": ["Seed Title"]})
        enricher_df = pl.DataFrame({"doi": ["10.1/a"], "title": ["Enricher Title"]})

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline=None,  # No seed pipeline
        )

        # ColumnRenamer always uses qualified format from enricher pipeline
        assert "crossref.publication.title" in result.columns


@pytest.mark.unit
class TestGetEnricherPrefix:
    """Tests for _get_enricher_prefix helper."""

    def test_returns_qualified_prefix(self, merge_service):
        """Test prefix uses qualified format {provider}.{entity}."""
        prefix = merge_service._priority_orderer.get_enricher_prefix(
            "crossref_publication"
        )
        assert prefix == "crossref.publication."

    def test_qualified_prefix_same_provider(self, merge_service):
        """Test qualified prefix for same provider different entity."""
        prefix = merge_service._priority_orderer.get_enricher_prefix("chembl_activity")
        assert prefix == "chembl.activity."

    def test_qualified_prefix_different_both(self, merge_service):
        """Test qualified prefix for different provider and entity."""
        prefix = merge_service._priority_orderer.get_enricher_prefix("pubchem_compound")
        assert prefix == "pubchem.compound."

    def test_fallback_prefix_when_invalid_format(self, merge_service):
        """Test fallback prefix when pipeline name has no underscore."""
        prefix = merge_service._priority_orderer.get_enricher_prefix("invalidpipeline")
        assert prefix == "invalidpipeline_"


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
    """Tests for EnricherDeduplicatorService._check_duplicates helper."""

    def test_no_duplicates(self, deduplicator):
        """Test returns False when no duplicates."""
        import polars as pl

        df = pl.DataFrame({"doi": ["a", "b", "c"], "val": [1, 2, 3]})
        assert deduplicator._check_duplicates(df, ["doi"]) is False

    def test_has_duplicates(self, deduplicator):
        """Test returns True when duplicates exist."""
        import polars as pl

        df = pl.DataFrame({"doi": ["a", "a", "b"], "val": [1, 2, 3]})
        assert deduplicator._check_duplicates(df, ["doi"]) is True

    def test_empty_dataframe(self, deduplicator):
        """Test returns False for empty DataFrame."""
        import polars as pl

        df = pl.DataFrame({"doi": [], "val": []}).cast(
            {"doi": pl.String, "val": pl.Int64}
        )
        assert deduplicator._check_duplicates(df, ["doi"]) is False

    def test_missing_key_column(self, deduplicator):
        """Test returns False when key column doesn't exist."""
        import polars as pl

        df = pl.DataFrame({"val": [1, 2, 3]})
        assert deduplicator._check_duplicates(df, ["doi"]) is False

    def test_composite_key(self, deduplicator):
        """Test composite key detection."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a", "a"],
                "pmid": ["1", "1", "2"],
                "val": [1, 2, 3],
            }
        )
        # (a, 1) and (a, 2) are unique composite keys, but (a, 1) has duplicate
        # Wait, actually: (a, 1), (a, 1), (a, 2) → (a, 1) is duplicated
        assert deduplicator._check_duplicates(df, ["doi", "pmid"]) is True

        # No duplicates
        df2 = pl.DataFrame(
            {
                "doi": ["a", "a", "b"],
                "pmid": ["1", "2", "1"],
                "val": [1, 2, 3],
            }
        )
        assert deduplicator._check_duplicates(df2, ["doi", "pmid"]) is False


@pytest.mark.unit
class TestDeduplicateEnricher:
    """Tests for EnricherDeduplicatorService.deduplicate and related helpers."""

    def test_no_duplicates_returns_unchanged(self, deduplicator):
        """Test no duplicates returns DataFrame unchanged."""
        import polars as pl

        df = pl.DataFrame({"doi": ["a", "b"], "title": ["T1", "T2"]})
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert result.equals(df)

    def test_identical_values_preserves_type(self, deduplicator):
        """Test identical values preserve original type."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a", "b"],
                "title": ["Same", "Same", "Other"],
                "count": [10, 10, 20],
            }
        )
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert len(result) == 2
        row_a = result.filter(pl.col("doi") == "a")
        assert row_a["title"][0] == "Same"
        assert row_a["count"][0] == 10
        # Type should be preserved
        assert row_a["count"].dtype == pl.Int64

    def test_different_values_concatenated(self, deduplicator):
        """Test different values are concatenated with | in original order."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a", "b"],
                "title": ["T1", "T2", "T3"],
                "count": [10, 20, 30],
            }
        )
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert len(result) == 2
        row_a = result.filter(pl.col("doi") == "a")
        assert row_a["title"][0] == "T1|T2"
        assert row_a["count"][0] == "10|20"

    def test_all_null_remains_null(self, deduplicator):
        """Test all null values remain null (no conflict when all identical)."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a"],
                "title": [None, None],
            }
        )
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert len(result) == 1
        # All nulls → remains null (no conflict, uses first() which preserves null)
        assert result["title"][0] is None

    def test_mixed_null_values(self, deduplicator):
        """Test mixed null and values include null as string in original order."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a", "a"],
                "title": ["T1", None, "T2"],
            }
        )
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert len(result) == 1
        # Order preserved: T1, null, T2
        assert result["title"][0] == "T1|null|T2"

    def test_single_value_plus_null(self, deduplicator):
        """Test single value plus null are concatenated in original order."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a"],
                "title": ["Same", None],
            }
        )
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert len(result) == 1
        assert result["title"][0] == "Same|null"

    def test_numeric_with_null(self, deduplicator):
        """Test numeric values with null in original order."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a", "a"],
                "count": [10, None, 20],
            }
        )
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert len(result) == 1
        # Order preserved: 10, null, 20
        assert result["count"][0] == "10|null|20"

    def test_boolean_values(self, deduplicator):
        """Test boolean values are converted to lowercase strings in original order."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a"],
                "is_oa": [True, False],
            }
        )
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert len(result) == 1
        # Order preserved: true, false
        assert result["is_oa"][0] == "true|false"

    def test_date_values(self, deduplicator):
        """Test date values are converted to ISO format in original order."""
        import polars as pl
        from datetime import date

        df = pl.DataFrame(
            {
                "doi": ["a", "a"],
                "pub_date": [date(2024, 1, 1), date(2024, 6, 15)],
            }
        )
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert len(result) == 1
        assert result["pub_date"][0] == "2024-01-01|2024-06-15"

    def test_composite_key__test_deduplicate_enricher_application_composite_test_merger_1308(self, deduplicator):
        """Test deduplication with composite key."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a", "a"],
                "pmid": ["1", "1", "2"],
                "val": ["X", "Y", "Z"],
            }
        )
        result = deduplicator.deduplicate(df, ["doi", "pmid"], "test")
        assert len(result) == 2
        row_a1 = result.filter((pl.col("doi") == "a") & (pl.col("pmid") == "1"))
        assert row_a1["val"][0] == "X|Y"

    def test_empty_dataframe(self, deduplicator):
        """Test empty DataFrame returns unchanged."""
        import polars as pl

        df = pl.DataFrame({"doi": [], "title": []}).cast(
            {"doi": pl.String, "title": pl.String}
        )
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert len(result) == 0

    def test_duplicate_values_in_group_preserved(self, deduplicator):
        """Test duplicate values within a group are preserved (not deduplicated)."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a", "a"],
                "title": ["Same", "Same", "Different"],
            }
        )
        result = deduplicator.deduplicate(df, ["doi"], "test")
        assert len(result) == 1
        # Order and duplicates preserved: Same, Same, Different
        assert result["title"][0] == "Same|Same|Different"

    def test_logs_warning_on_duplicates(self, deduplicator, mock_logger):
        """Test warning is logged when duplicates are found."""
        import polars as pl

        df = pl.DataFrame(
            {
                "doi": ["a", "a"],
                "title": ["T1", "T2"],
            }
        )
        deduplicator.deduplicate(df, ["doi"], "test_enricher")

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
        seed_df = pl.DataFrame(
            {
                "doi": ["10.1/aaa", "10.1/bbb"],
                "title": ["Study A", "Study B"],
            }
        )

        # Enricher has duplicates for 10.1/aaa
        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1/aaa", "10.1/aaa", "10.1/bbb"],
                "citation_count": [150, 200, 50],
            }
        )

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Result should have exactly 2 rows (no fan-out)
        assert len(result) == 2

        # Citation count for aaa should be aggregated
        row_aaa = result.filter(pl.col("doi") == "10.1/aaa")
        assert "150|200" in str(row_aaa["crossref.publication.citation_count"][0])

        # Citation count for bbb - no duplicates, but column type is String
        # because other groups have conflicts (Polars requires uniform column type)
        row_bbb = result.filter(pl.col("doi") == "10.1/bbb")
        assert row_bbb["crossref.publication.citation_count"][0] == "50"

    @pytest.mark.asyncio
    async def test_no_deduplication_when_no_duplicates(
        self, merge_service, mock_logger
    ):
        """Test no deduplication overhead when enricher has no duplicates."""
        import polars as pl

        seed_df = pl.DataFrame(
            {
                "doi": ["10.1/aaa", "10.1/bbb"],
                "title": ["Study A", "Study B"],
            }
        )

        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1/aaa", "10.1/bbb"],
                "citation_count": [150, 50],
            }
        )

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        await merge_service._join_planner.apply_joins(
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
class TestDropSystemColumns:
    """Tests for _drop_system_columns method."""

    def test_drops_system_columns_from_enricher(self, merge_service):
        """Test that system columns are dropped from enricher DataFrame."""
        import polars as pl

        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "title": ["Test"],
                "_dq_error": [False],
                "_dq_warn": [False],
                "_run_id": ["run-1"],
                "_ingestion_ts": ["2024-01-01T00:00:00Z"],
                "_source": ["crossref"],
            }
        )

        result = merge_service._join_planner.drop_system_columns(enricher_df)

        # Business columns preserved
        assert "doi" in result.columns
        assert "title" in result.columns
        # System columns dropped
        assert "_dq_error" not in result.columns
        assert "_dq_warn" not in result.columns
        assert "_run_id" not in result.columns
        assert "_ingestion_ts" not in result.columns
        assert "_source" not in result.columns

    def test_no_change_when_no_system_columns(self, merge_service):
        """Test no change when enricher has no system columns."""
        import polars as pl

        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "title": ["Test"],
                "citation_count": [42],
            }
        )

        result = merge_service._join_planner.drop_system_columns(enricher_df)

        assert result.columns == enricher_df.columns
        assert len(result) == len(enricher_df)

    @pytest.mark.asyncio
    async def test_system_columns_not_duplicated_after_join(self, merge_service):
        """Test that system columns don't get .A, .B suffixes after merge."""
        import polars as pl

        seed_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "title": ["Seed Title"],
                "_dq_error": [False],
                "_dq_warn": [False],
                "_run_id": ["run-1"],
            }
        )

        # Enricher has same system columns - they should be dropped before join
        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "citation_count": [42],
                "_dq_error": [True],  # Different value - but should be dropped
                "_dq_warn": [True],
                "_run_id": ["run-2"],
            }
        )

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Seed system columns preserved
        assert "_dq_error" in result.columns
        assert "_dq_warn" in result.columns
        assert "_run_id" in result.columns

        # NO duplicate system columns with suffixes
        assert "_dq_error.A" not in result.columns
        assert "_dq_warn.A" not in result.columns
        assert "_dq_error_crossref_publication" not in result.columns
        assert "_dq_warn_crossref_publication" not in result.columns

        # Seed values preserved (enricher values dropped)
        assert result["_dq_error"][0] is False
        assert result["_run_id"][0] == "run-1"

    @pytest.mark.asyncio
    async def test_multiple_enrichers_no_system_column_duplicates(self, merge_service):
        """Test multiple enrichers don't create _dq_error.A, .B, .C, .D."""
        import polars as pl

        seed_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "_dq_error": [False],
            }
        )

        # All enrichers have _dq_error - should all be dropped
        enrichers = []
        enricher_dfs = {}
        for provider in ["crossref", "openalex", "pubmed", "semanticscholar"]:
            pipeline = f"{provider}_publication"
            enricher_dfs[pipeline] = pl.DataFrame(
                {
                    "doi": ["10.1/a"],
                    f"{provider}_field": [f"value_{provider}"],
                    "_dq_error": [True],  # Should be dropped
                }
            )
            enrichers.append(
                EnricherConfig(
                    pipeline=pipeline,
                    join_keys=("doi",),
                    required=False,
                )
            )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline="chembl_publication",
        )

        # Only one _dq_error column (from seed)
        dq_error_cols = [c for c in result.columns if "_dq_error" in c]
        assert dq_error_cols == ["_dq_error"], (
            f"Expected only '_dq_error', got: {dq_error_cols}"
        )

        # No .A, .B, .C, .D suffixes
        assert "_dq_error.A" not in result.columns
        assert "_dq_error.B" not in result.columns
        assert "_dq_error.C" not in result.columns
        assert "_dq_error.D" not in result.columns


@pytest.mark.unit
class TestQualifiedJoinKeys:
    """Tests for qualified join key renaming feature."""

    @pytest.mark.asyncio
    async def test_join_with_pre_qualified_seed_columns(self, merge_service):
        """Test JOIN works when seed columns are pre-qualified."""
        import polars as pl

        # Seed with qualified column names (as happens after merge() renaming)
        seed_df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a", "10.1/b"],
                "chembl.publication.title": ["Title 1", "Title 2"],
            }
        )
        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "citation_count": [100],
            }
        )

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Should join on chembl.publication.doi = crossref.publication.doi
        assert "chembl.publication.doi" in result.columns
        assert "chembl.publication.title" in result.columns
        assert "crossref.publication.citation_count" in result.columns
        # Enricher DOI preserved as data column
        assert "crossref.publication.doi" in result.columns
        # Both seed records preserved (left join)
        assert len(result) == 2
        # First record has enrichment
        assert result["crossref.publication.citation_count"][0] == 100
        # Second record has null (no match)
        assert result["crossref.publication.citation_count"][1] is None

    @pytest.mark.asyncio
    async def test_normalization_with_qualified_columns(self, merge_service):
        """Test case-insensitive normalization works with qualified columns."""
        import polars as pl

        # Seed with uppercase DOI
        seed_df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1038/NATURE12373"],
                "chembl.publication.title": ["Test"],
            }
        )
        # Enricher with lowercase DOI
        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1038/nature12373"],
                "citation_count": [500],
            }
        )

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Should match despite case difference
        assert "crossref.publication.citation_count" in result.columns
        assert result["crossref.publication.citation_count"][0] == 500

    @pytest.mark.asyncio
    async def test_multiple_enrichers_with_qualified_seed(self, merge_service):
        """Test multiple enrichers work with pre-qualified seed columns."""
        import polars as pl

        seed_df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "chembl.publication.title": ["Seed Title"],
            }
        )

        enricher_dfs = {
            "crossref_publication": pl.DataFrame(
                {"doi": ["10.1/a"], "citation_count": [100]}
            ),
            "openalex_publication": pl.DataFrame(
                {"doi": ["10.1/a"], "concepts": ["AI"]}
            ),
        }

        enrichers = [
            EnricherConfig(
                pipeline="crossref_publication", join_keys=("doi",), required=False
            ),
            EnricherConfig(
                pipeline="openalex_publication", join_keys=("doi",), required=False
            ),
        ]

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs=enricher_dfs,
            enrichers=enrichers,
            seed_pipeline="chembl_publication",
        )

        # All columns should be present
        assert "chembl.publication.doi" in result.columns
        assert "chembl.publication.title" in result.columns
        assert "crossref.publication.citation_count" in result.columns
        assert "openalex.publication.concepts" in result.columns
        # Enricher DOI columns preserved
        assert "crossref.publication.doi" in result.columns
        assert "openalex.publication.doi" in result.columns

    @pytest.mark.asyncio
    async def test_enricher_join_key_becomes_qualified(self, merge_service):
        """Test enricher join keys are renamed to qualified format."""
        import polars as pl

        seed_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "title": ["Seed Title"],
            }
        )
        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "title": ["Enricher Title"],
            }
        )

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Enricher title should be qualified
        assert "crossref.publication.title" in result.columns
        # Enricher DOI preserved as qualified data column
        assert "crossref.publication.doi" in result.columns
        # Original seed columns preserved
        assert "doi" in result.columns
        assert "title" in result.columns

    @pytest.mark.asyncio
    async def test_enricher_join_key_preserved_as_data_column(self, merge_service):
        """Test that enricher DOI/PMID are preserved after join.

        Polars drops right_on column when left_on != right_on. The fix uses
        a temporary column as right_on so the qualified enricher join key
        survives as a regular data column.
        """
        import polars as pl

        seed_df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a", "10.1/b"],
                "chembl.publication.title": ["T1", "T2"],
            }
        )
        enricher_df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "citation_count": [100],
            }
        )

        enricher_config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=False,
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"crossref_publication": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Both seed and enricher DOIs preserved
        assert "chembl.publication.doi" in result.columns
        assert "crossref.publication.doi" in result.columns

        # Values match: enricher DOI has value for matched row, null for unmatched
        assert result["crossref.publication.doi"][0] == "10.1/a"
        assert result["crossref.publication.doi"][1] is None

        # Temp column NOT present in result
        assert not any(c.startswith("__temp_join_") for c in result.columns)
