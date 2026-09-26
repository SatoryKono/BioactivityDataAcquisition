# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for enricher join execution helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.enricher_join_execution import (
    PreparedEnricherJoinContext,
    build_prepared_enricher_join_context,
    execute_prepared_enricher_join,
)
from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.composite.config import EnricherConfig


@pytest.mark.unit
def test_build_prepared_enricher_join_context_many_to_one_aggregates_and_prepares_frames() -> (
    None
):
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
    logger = MagicMock()
    join_key_resolver = MagicMock()
    join_key_resolver.normalize_join_key_columns.side_effect = (
        lambda df, join_keys, pipeline=None: df
    )
    resolve_join_key_names = MagicMock(
        return_value=(
            "chembl.publication.doi",
            "crossref.publication.doi",
            None,
        )
    )
    seed_df = pl.DataFrame({"chembl.publication.doi": ["10.1/a"], "seed_only": [1]})
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
    enricher = EnricherConfig(
        pipeline="crossref_publication",
        join_keys=("doi",),
        cardinality=EnricherCardinality.MANY_TO_ONE,
        aggregation=aggregation,
    )

    prepared = build_prepared_enricher_join_context(
        merged_df=seed_df,
        enricher_df=enricher_df,
        enricher=enricher,
        seed_pipeline="chembl_publication",
        deduplicator=deduplicator,
        aggregator=aggregator,
        renamer=renamer,
        logger=logger,
        field_alias_resolver=lambda _pipeline: None,
        join_key_resolver=join_key_resolver,
        resolve_join_key_names=resolve_join_key_names,
        drop_system_columns=lambda df: df,
    )

    assert prepared.enricher_pipeline == "crossref_publication"
    assert prepared.metadata.seed_join_key == "chembl.publication.doi"
    assert prepared.metadata.enricher_join_key == "crossref.publication.doi"
    aggregator.aggregate.assert_called_once()
    deduplicator.deduplicate.assert_called_once()


@pytest.mark.unit
def test_execute_prepared_enricher_join_resolves_conflicts_and_executes_join() -> None:
    conflict_resolver = MagicMock()
    merged_df = pl.DataFrame({"chembl.publication.doi": ["10.1/a"]})
    enricher_df = pl.DataFrame({"crossref.publication.doi": ["10.1/a"]})
    conflict_resolver.detect_and_resolve_conflicts.return_value = (
        merged_df,
        enricher_df,
    )
    join_executor = MagicMock(return_value=pl.DataFrame({"joined": [1]}))
    prepared = PreparedEnricherJoinContext(
        enricher_pipeline="crossref_publication",
        metadata=MagicMock(
            seed_join_key="chembl.publication.doi",
            enricher_join_key="crossref.publication.doi",
            join_key_set={"chembl.publication.doi", "crossref.publication.doi"},
        ),
        merged_df=merged_df,
        enricher_df=enricher_df,
    )

    result = execute_prepared_enricher_join(
        prepared_context=prepared,
        conflict_resolver=conflict_resolver,
        join_executor=join_executor,
    )

    assert result.equals(pl.DataFrame({"joined": [1]}))
    conflict_resolver.detect_and_resolve_conflicts.assert_called_once_with(
        merged_df,
        enricher_df,
        {"chembl.publication.doi", "crossref.publication.doi"},
    )
    join_executor.assert_called_once_with(
        merged_df,
        enricher_df,
        "chembl.publication.doi",
        "crossref.publication.doi",
        "crossref_publication",
    )
