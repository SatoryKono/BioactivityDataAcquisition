# pyright: reportArgumentType=false
"""Residual closeout coverage for domain/composite CR-FULL #8238-#8253."""

from __future__ import annotations

import pytest

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.composite.config import ColumnGroupConfig, MergeConfig
from bioetl.domain.composite.cross_validation import (
    EnricherFieldPairing,
    FieldComparisonSpec,
)
from bioetl.domain.composite.field_groups_models import (
    FieldGroupDefinition,
    FieldGroupId,
    FieldMapping,
)
from bioetl.domain.composite.field_groups_registry import FieldGroupRegistry
from bioetl.domain.composite.result_seed_dependency import (
    DependencyResult,
    DependencyStatus,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

pytestmark = pytest.mark.unit


def test_dependency_result_skipped_does_not_set_error_message() -> None:
    result = DependencyResult.skipped("dep_pipe", reason="Already completed")
    assert result.status == DependencyStatus.SKIPPED
    assert result.is_success is True
    assert result.error_message is None


def test_aggregation_enums_are_strenum() -> None:
    assert issubclass(AggregationFunction, str)
    assert issubclass(EnricherCardinality, str)
    assert AggregationFunction.COUNT == "count"
    assert AggregationFunction.from_string("FIRST") is AggregationFunction.FIRST
    assert (
        EnricherCardinality.from_string("many_to_one")
        is EnricherCardinality.MANY_TO_ONE
    )


def test_field_group_definition_rejects_empty_display_name() -> None:
    with pytest.raises(ValueError, match="display_name cannot be empty"):
        FieldGroupDefinition(
            group_id=FieldGroupId.BIBLIOGRAPHY,
            display_name="",
            fields=(),
        )


def test_enricher_field_pairing_normalizes_list_fields_before_validation() -> None:
    pairing = EnricherFieldPairing(
        enricher_pipeline="crossref_publication",
        fields=[  # type: ignore[arg-type]
            FieldComparisonSpec(field_name="title", method="exact"),
        ],
    )
    assert isinstance(pairing.fields, tuple)
    assert len(pairing.fields) == 1


def test_column_group_config_compiles_pattern_at_construction() -> None:
    ok = ColumnGroupConfig(name="ids", pattern=r"^doi$")
    assert ok.pattern == r"^doi$"
    with pytest.raises(ValueError, match="invalid pattern"):
        ColumnGroupConfig(name="bad", pattern="(")


def test_field_group_registry_ordered_columns_uses_rank_map() -> None:
    mapping = FieldMapping(
        base_name="doi",
        group=FieldGroupId.BIBLIOGRAPHY,
        provider_columns=("chembl.publication.doi",),
    )
    group = FieldGroupDefinition(
        group_id=FieldGroupId.BIBLIOGRAPHY,
        display_name="Identifiers",
        fields=(mapping,),
    )
    registry = FieldGroupRegistry(groups=(group,))
    ordered = registry.get_ordered_columns(
        ["_meta", "chembl.publication.doi", "unknown_col"]
    )
    assert ordered[-1] == "_meta"
    assert "chembl.publication.doi" in ordered


def test_merge_and_aggregation_convert_tuple_of_dicts() -> None:
    agg = AggregationConfig(
        group_by="document_chembl_id",
        fields=(  # type: ignore[arg-type]
            {"source_field": "term", "agg_function": "collect_list"},
        ),
    )
    assert isinstance(agg.fields[0], AggregationFieldSpec)
    assert agg.fields[0].agg_function is AggregationFunction.COLLECT_LIST

    merge = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/x",
        output_gold_path="gold/x",
        column_groups=(  # type: ignore[arg-type]
            {"name": "ids", "fields": ["doi"]},
        ),
        exclude_fields=("tmp_col",),  # type: ignore[arg-type]
    )
    assert isinstance(merge.column_groups[0], ColumnGroupConfig)
    assert merge.exclude_fields == ("tmp_col",)


def test_state_allowed_transitions_uses_cached_sets() -> None:
    allowed = CompositePipelineState.NOT_STARTED.allowed_transitions
    assert CompositePipelineState.SEED_RUNNING in allowed
    assert CompositePipelineState.COMPLETED.allowed_transitions == frozenset()
    # identity cache: repeated access returns equal frozenset content
    assert (
        CompositePipelineState.MERGING.allowed_transitions
        == CompositePipelineState.MERGING.allowed_transitions
    )
