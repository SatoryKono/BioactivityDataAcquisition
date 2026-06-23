"""Unit tests for JoinPlannerService."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.join_execution import JoinHow
from bioetl.application.composite.join_planner import JoinPlannerService
from tests.unit.application.composite.merge_test_support import (
    build_join_planner_service,
)
from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.composite.config_merge import MergeConfig
from bioetl.domain.composite.config_models import DependencyConfig, EnricherConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


@pytest.fixture
def merge_config() -> MergeConfig:
    return MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/composite/test",
        output_gold_path="gold/composite/test",
    )


@pytest.fixture
def planner_deps() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    deduplicator = MagicMock()
    deduplicator.deduplicate.side_effect = (
        lambda enricher_df, join_keys, enricher_name: enricher_df
    )

    aggregator = MagicMock()
    aggregator.aggregate.side_effect = lambda df, agg, pipeline: df

    renamer = MagicMock()
    renamer.rename_dataframe.side_effect = (
        lambda df, pipeline, exclude_join_keys, field_aliases: df
    )

    conflict_resolver = MagicMock()
    conflict_resolver.detect_and_resolve_conflicts.side_effect = (
        lambda left, right, join_keys: (left, right)
    )
    return deduplicator, aggregator, renamer, conflict_resolver


@pytest.fixture
def planner(merge_config: MergeConfig, planner_deps) -> JoinPlannerService:
    deduplicator, aggregator, renamer, conflict_resolver = planner_deps
    logger = MagicMock()
    # Use a mutable ref so test can swap planner._config and resolver follows
    planner_ref: list[JoinPlannerService] = []

    def _resolve_join_type() -> JoinHow:
        from bioetl.domain.composite.strategy import MergeStrategy

        if not planner_ref:
            return "left"
        cfg = planner_ref[0]._config
        strategy = getattr(cfg, "strategy", MergeStrategy.LEFT_OUTER)
        match strategy:
            case MergeStrategy.INNER:
                return "inner"
            case MergeStrategy.UNION:
                return "full"
            case _:
                return "left"

    svc = build_join_planner_service(
        merge_config=merge_config,
        logger=logger,
        deduplicator=deduplicator,
        aggregator=aggregator,
        renamer=renamer,
        conflict_resolver=conflict_resolver,
        field_alias_resolver=lambda _pipeline: None,
        join_type_resolver=_resolve_join_type,
    )
    planner_ref.append(svc)
    return svc


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_joins_skips_missing_enricher(planner: JoinPlannerService) -> None:
    seed_df = pl.DataFrame({"chembl.publication.doi": ["10.1/a"], "seed_only": [1]})
    enrichers = (EnricherConfig(pipeline="crossref_publication", join_keys=("doi",)),)

    result = await planner.apply_joins(
        seed_df=seed_df,
        enricher_dfs={},
        enrichers=enrichers,
        seed_pipeline="chembl_publication",
    )

    assert result.equals(seed_df)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_joins_many_to_one_aggregates_and_joins(
    planner: JoinPlannerService, planner_deps
) -> None:
    deduplicator, aggregator, _renamer, conflict_resolver = planner_deps
    seed_df = pl.DataFrame(
        {
            "chembl.publication.doi": ["10.1/a"],
            "seed_only": [1],
        }
    )
    enricher_df = pl.DataFrame(
        {
            "crossref.publication.doi": ["10.1/a"],
            "crossref.publication.title": ["Title A"],
        }
    )
    aggregation = AggregationConfig(
        group_by="doi",
        fields=(AggregationFieldSpec("title", AggregationFunction.FIRST),),
    )
    enrichers = (
        EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            cardinality=EnricherCardinality.MANY_TO_ONE,
            aggregation=aggregation,
        ),
    )

    result = await planner.apply_joins(
        seed_df=seed_df,
        enricher_dfs={"crossref_publication": enricher_df},
        enrichers=enrichers,
        seed_pipeline="chembl_publication",
    )

    assert "crossref.publication.title" in result.columns
    aggregator.aggregate.assert_called_once()
    deduplicator.deduplicate.assert_called_once()
    assert conflict_resolver.detect_and_resolve_conflicts.call_args.args[2] == {
        "chembl.publication.doi",
        "crossref.publication.doi",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_dependency_joins_with_filter_field(
    planner: JoinPlannerService, planner_deps
) -> None:
    _deduplicator, _aggregator, _renamer, conflict_resolver = planner_deps
    merged_df = pl.DataFrame({"chembl.publication.doi": ["10.1/a"]})
    dep_df = pl.DataFrame(
        {
            "pubmed.publication.pmid": ["10.1/a"],
            "pubmed.publication.title": ["From dependency"],
        }
    )
    dep = DependencyConfig(
        pipeline="pubmed_publication",
        join_keys=("doi",),
        filter_field="pmid",
    )

    result = await planner.apply_dependency_joins(
        merged_df=merged_df,
        dependency_dfs={"pubmed_publication": dep_df},
        dependencies=(dep,),
        seed_pipeline="chembl_publication",
    )

    assert "pubmed.publication.title" in result.columns
    assert conflict_resolver.detect_and_resolve_conflicts.called
    assert conflict_resolver.detect_and_resolve_conflicts.call_args.args[2] == {
        "chembl.publication.doi",
        "pubmed.publication.pmid",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_dependency_joins_prefers_key_source_for_left_key_resolution(
    planner: JoinPlannerService, planner_deps
) -> None:
    _deduplicator, _aggregator, _renamer, conflict_resolver = planner_deps
    merged_df = pl.DataFrame({"openalex.publication.doi": ["10.1/a"]})
    dep_df = pl.DataFrame(
        {
            "pubmed.publication.doi": ["10.1/a"],
            "pubmed.publication.title": ["From dependency"],
        }
    )
    dep = DependencyConfig(
        pipeline="pubmed_publication",
        join_keys=("doi",),
        key_source="openalex_publication",
    )

    result = await planner.apply_dependency_joins(
        merged_df=merged_df,
        dependency_dfs={"pubmed_publication": dep_df},
        dependencies=(dep,),
        seed_pipeline="chembl_publication",
    )

    assert "pubmed.publication.title" in result.columns
    assert conflict_resolver.detect_and_resolve_conflicts.call_args.args[2] == {
        "openalex.publication.doi",
        "pubmed.publication.doi",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_dependency_joins_delegates_composite_key(
    planner: JoinPlannerService,
) -> None:
    merged_df = pl.DataFrame({"chembl.publication.doi": ["10.1/a"]})
    dep_df = pl.DataFrame({"pubmed.publication.doi": ["10.1/a"]})
    dep = DependencyConfig(
        pipeline="pubmed_publication",
        join_keys=("doi", "pmid"),
        filter_fields=("doi", "pmid"),
    )

    expected = pl.DataFrame({"ok": [1]})
    planner._dependency_joiner.apply_composite_key_dependency_join = MagicMock(
        return_value=expected
    )

    result = await planner.apply_dependency_joins(
        merged_df=merged_df,
        dependency_dfs={"pubmed_publication": dep_df},
        dependencies=(dep,),
        seed_pipeline="chembl_publication",
    )

    assert result.equals(expected)
    planner._dependency_joiner.apply_composite_key_dependency_join.assert_called_once()


@pytest.mark.unit
def test_apply_composite_key_dependency_join_missing_columns_returns_input(
    planner: JoinPlannerService,
    planner_deps,
) -> None:
    _deduplicator, _aggregator, _renamer, conflict_resolver = planner_deps
    merged_df = pl.DataFrame({"chembl.publication.doi": ["10.1/a"]})
    dep_df = pl.DataFrame(
        {
            "pubmed.publication.doi": ["10.1/a"],
            "pubmed.publication.pmid": ["p1"],
        }
    )
    dep = DependencyConfig(
        pipeline="pubmed_publication",
        join_keys=("doi", "pmid"),
        filter_fields=("doi", "pmid"),
    )

    result = planner.apply_composite_key_dependency_join(
        merged_df=merged_df,
        dep_df=dep_df,
        dep=dep,
        seed_pipeline="chembl_publication",
    )

    assert result.equals(merged_df)
    conflict_resolver.detect_and_resolve_conflicts.assert_not_called()


@pytest.mark.unit
def test_apply_composite_key_dependency_join_success(
    planner: JoinPlannerService,
    planner_deps,
) -> None:
    _deduplicator, _aggregator, _renamer, conflict_resolver = planner_deps
    merged_df = pl.DataFrame(
        {
            "chembl.publication.doi": ["10.1/a"],
            "chembl.publication.pmid": ["p1"],
            "seed": [1],
        }
    )
    dep_df = pl.DataFrame(
        {
            "pubmed.publication.doi": ["10.1/a"],
            "pubmed.publication.pmid": ["p1"],
            "pubmed.publication.year": [2024],
        }
    )
    dep = DependencyConfig(
        pipeline="pubmed_publication",
        join_keys=("doi", "pmid"),
        filter_fields=("doi", "pmid"),
    )

    result = planner.apply_composite_key_dependency_join(
        merged_df=merged_df,
        dep_df=dep_df,
        dep=dep,
        seed_pipeline="chembl_publication",
    )

    assert "pubmed.publication.year" in result.columns
    assert conflict_resolver.detect_and_resolve_conflicts.call_args.args[2] == {
        "chembl.publication.doi",
        "chembl.publication.pmid",
        "pubmed.publication.doi",
        "pubmed.publication.pmid",
    }
    assert conflict_resolver.detect_and_resolve_conflicts.call_count == 1


@pytest.mark.unit
def test_find_join_key_column_fallbacks(planner: JoinPlannerService) -> None:
    columns = ["chembl.publication.doi", "doi", "crossref.publication.pmid"]
    assert (
        planner.find_join_key_column("doi", columns, pipeline="chembl_publication")
        == "chembl.publication.doi"
    )
    assert planner.find_join_key_column("doi", columns, pipeline="invalid") == "doi"
    assert planner.find_join_key_column("pmid", columns) == "crossref.publication.pmid"


@pytest.mark.unit
def test_normalize_and_drop_system_columns(planner: JoinPlannerService) -> None:
    df = pl.DataFrame(
        {
            "chembl.publication.doi": ["10.1/ABC"],
            "_run_id": ["r1"],
            "title": ["T"],
        }
    )
    normalized = planner.normalize_join_key_columns(
        df,
        join_keys=["doi", "title"],
        pipeline="chembl_publication",
    )
    assert normalized["chembl.publication.doi"].to_list() == ["10.1/abc"]

    dropped = planner.drop_system_columns(normalized)
    assert "_run_id" not in dropped.columns


@pytest.mark.unit
def test_execute_polars_join_missing_key_returns_left(
    planner: JoinPlannerService,
) -> None:
    left_df = pl.DataFrame({"left_id": [1], "v": ["a"]})
    right_df = pl.DataFrame({"other": [1], "x": ["b"]})

    result = planner.execute_polars_join(
        left_df=left_df,
        right_df=right_df,
        left_key="missing_left",
        right_key="other",
        pipeline_name="pubmed_publication",
    )

    assert result.equals(left_df)


@pytest.mark.unit
def test_execute_polars_join_type_mismatch_and_temp_key(
    planner: JoinPlannerService,
) -> None:
    left_df = pl.DataFrame({"left_id": [1.0], "v": ["seed"]})
    right_df = pl.DataFrame({"right_id": ["1"], "x": ["enriched"]})

    result = planner.execute_polars_join(
        left_df=left_df,
        right_df=right_df,
        left_key="left_id",
        right_key="right_id",
        pipeline_name="pubmed_publication",
    )

    assert result.height == 1
    assert "x" in result.columns


@pytest.mark.unit
def test_resolve_key_helpers_and_pipeline_parser(planner: JoinPlannerService) -> None:
    seed_key, enricher_key, seed_qualified = planner.resolve_join_key_names(
        primary_key="doi",
        seed_pipeline="invalid",
        enricher_pipeline="invalid",
        merged_columns=[],
    )
    assert seed_key == "doi"
    assert enricher_key == "doi"
    assert seed_qualified is None

    left_key, right_key, left_qualified = planner.resolve_join_key_names_asymmetric(
        left_key="doi",
        right_key="pmid",
        left_pipeline="invalid",
        right_pipeline="invalid",
        merged_columns=[],
    )
    assert (left_key, right_key, left_qualified) == ("doi", "pmid", None)

    with pytest.raises(ValueError):
        planner._parse_pipeline_name("invalid")

    assert planner._parse_pipeline_name("chembl_publication") == (
        "chembl",
        "publication",
    )


@pytest.mark.unit
def test_composite_key_resolution_and_join_type_mapping(
    planner: JoinPlannerService,
) -> None:
    left_keys, right_keys, join_keys = planner.resolve_composite_join_keys(
        join_keys_list=["doi", "pmid"],
        left_pipeline="chembl_publication",
        right_pipeline="pubmed_publication",
        merged_columns=["chembl.publication.doi", "chembl.publication.pmid"],
    )

    assert left_keys == ["chembl.publication.doi", "chembl.publication.pmid"]
    assert right_keys == ["pubmed.publication.doi", "pubmed.publication.pmid"]
    assert "chembl.publication.doi" in join_keys
    assert "pubmed.publication.pmid" in join_keys

    same_key_join = planner.execute_composite_key_join(
        left_df=pl.DataFrame({"id": ["a"], "v": [1]}),
        right_df=pl.DataFrame({"id": ["a"], "x": [2]}),
        left_keys=["id"],
        right_keys=["id"],
        pipeline_name="crossref_publication",
    )
    assert "x" in same_key_join.columns

    diff_key_join = planner.execute_composite_key_join(
        left_df=pl.DataFrame({"left_id": ["a"], "v": [1]}),
        right_df=pl.DataFrame({"right_id": ["a"], "x": [2]}),
        left_keys=["left_id"],
        right_keys=["right_id"],
        pipeline_name="crossref_publication",
    )
    assert "x" in diff_key_join.columns

    planner._config = replace(planner._config, strategy=MergeStrategy.LEFT_OUTER)
    assert planner.get_polars_join_type() == "left"
    planner._config = replace(planner._config, strategy=MergeStrategy.INNER)
    assert planner.get_polars_join_type() == "inner"
    planner._config = replace(planner._config, strategy=MergeStrategy.UNION)
    assert planner.get_polars_join_type() == "full"
    object.__setattr__(planner._config, "strategy", "unknown")
    assert planner.get_polars_join_type() == "left"
