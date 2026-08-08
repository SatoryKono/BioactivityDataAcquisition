# pyright: reportArgumentType=false
"""Residual closeout coverage for domain/composite CR-FULL #8222-#8255."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from bioetl.domain.composite.aggregation import (
    AggregationFieldSpec,
    AggregationFunction,
)
from bioetl.domain.composite.config import (
    CompositeConfig,
    DependencyConfig,
    EnricherConfig,
    MergeConfig,
    SeedConfig,
    composite_from_dict,
)
from bioetl.domain.composite.config_cross_validation import (
    CrossValidationConfig,
    _validate_cross_validation_thresholds,
    _validate_cross_validation_tolerances,
)
from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    FieldComparisonSpec,
)
from bioetl.domain.composite.field_groups_models import (
    FieldGroupDefinition,
    FieldGroupId,
    FieldMapping,
)
from bioetl.domain.composite.field_groups_registry import FieldGroupRegistry
from bioetl.domain.composite.lineage import (
    CompositeLineageMetadata,
    EnrichmentStatusRecord,
)
from bioetl.domain.composite.result_enrichment import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.result_seed_dependency import DependencyResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

pytestmark = pytest.mark.unit


def test_enrichment_timeout_rejects_non_finite_timeout() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        EnrichmentResult.timeout("e", timeout_seconds=-1)
    with pytest.raises(ValueError, match="timeout_seconds"):
        EnrichmentResult.timeout("e", timeout_seconds=math.nan)
    ok = EnrichmentResult.timeout("e", timeout_seconds=0.0, records_input=1)
    assert ok.status is EnrichmentStatus.TIMEOUT
    assert ok.duration_seconds == 0.0


def test_enrichment_result_rejects_invalid_record_counts() -> None:
    with pytest.raises(ValueError, match="records_input"):
        EnrichmentResult(
            enricher_name="e",
            status=EnrichmentStatus.SUCCESS,
            records_input=-1,
        )
    with pytest.raises(ValueError, match="records_enriched cannot exceed"):
        EnrichmentResult(
            enricher_name="e",
            status=EnrichmentStatus.SUCCESS,
            records_input=1,
            records_enriched=2,
        )


def test_cross_validation_rejects_non_finite_thresholds() -> None:
    with pytest.raises(ValueError, match="finite"):
        _validate_cross_validation_tolerances(math.nan, 0.1)
    with pytest.raises(ValueError, match="finite"):
        _validate_cross_validation_thresholds(1, 2, math.inf)  # type: ignore[arg-type]
    CrossValidationConfig()  # defaults ok


def _deserialize_config(payload: dict[str, object]) -> CompositeConfig:
    return composite_from_dict(
        payload,
        composite_cls=CompositeConfig,
        seed_cls=SeedConfig,
        dependency_cls=DependencyConfig,
        enricher_cls=EnricherConfig,
        merge_cls=MergeConfig,
    )


@pytest.mark.parametrize("section", ["dependencies", "enrichers"])
def test_serialization_preserves_zero_timeout_for_validation(section: str) -> None:
    payload: dict[str, object] = {
        "name": "c",
        "version": "1",
        "seed": {"pipeline": "seed", "output_keys": ["id"], "silver_table": "s"},
        "dependencies": [],
        "enrichers": [],
        "merge": {
            "strategy": "left_outer",
            "conflict_resolution": "seed_priority",
            "output_silver_path": "silver/c",
            "output_gold_path": "gold/c",
        },
    }
    payload[section] = [
        {"pipeline": "related", "join_keys": ["id"], "timeout_seconds": 0}
    ]
    with pytest.raises(ValueError, match="timeout_seconds"):
        _deserialize_config(payload)


def test_state_metric_doc_range_includes_terminals() -> None:
    assert CompositePipelineState.COMPLETED.to_metric_value() == 10
    assert CompositePipelineState.FAILED.to_metric_value() == 11


def test_lineage_nested_enrichment_status_roundtrip() -> None:
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    meta = CompositeLineageMetadata(
        composite_run_id="run-1",
        composite_name="pub",
        enrichment_status={
            "chembl": EnrichmentStatusRecord(
                provider="chembl",
                status="success",
                timestamp=ts,
                error_message=None,
            )
        },
    )
    payload = meta.to_dict()
    assert payload["_enrichment_status"]["chembl"]["status"] == "success"
    assert payload["_enrichment_status"]["chembl"]["timestamp"] == ts.isoformat()
    restored = CompositeLineageMetadata.from_dict(payload)
    assert restored.enrichment_status["chembl"].status == "success"
    assert restored.enrichment_status["chembl"].timestamp == ts
    # legacy plain string
    legacy = CompositeLineageMetadata.from_dict(
        {
            "_composite_run_id": "r",
            "_composite_name": "n",
            "_enrichment_status": {"crossref": "not_found"},
        }
    )
    assert legacy.enrichment_status["crossref"].status == "not_found"


def test_lineage_parsers_skip_invalid_iso_timestamps() -> None:
    meta = CompositeLineageMetadata.from_dict(
        {
            "_composite_run_id": "r",
            "_composite_name": "n",
            "_enrichment_timestamps": {"chembl": "not-a-date"},
            "_lineage_created_at": "also-bad",
        }
    )
    assert meta.enrichment_timestamps == {}
    assert meta.created_at is None


def test_field_mapping_providers_case_insensitive_dedupe() -> None:
    mapping = FieldMapping(
        base_name="doi",
        provider_columns=("ChEMBL.publication.doi", "chembl.publication.doi2"),
        group=FieldGroupId.BIBLIOGRAPHY,
    )
    assert mapping.providers == ("chembl",)
    assert mapping.has_provider("CHEMBL") is True


def test_merge_sort_policies_strip_whitespace() -> None:
    merge = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/x",
        output_gold_path="gold/x",
        sort_by_silver=(" id ", "name"),  # type: ignore[arg-type]
    )
    assert merge.sort_by_silver == ("id", "name")


def test_field_comparison_spec_defaults_thresholds() -> None:
    fuzzy = FieldComparisonSpec(field_name="title", method=ComparisonMethod.FUZZY)
    assert fuzzy.threshold == 0.8
    numeric = FieldComparisonSpec(
        field_name="year", method=ComparisonMethod.NUMERIC_TOLERANCE
    )
    assert numeric.threshold == 0.10


def test_is_gold_field_respects_definition_override() -> None:
    group = FieldGroupDefinition(
        group_id=FieldGroupId.BIBLIOGRAPHY,
        display_name="Bib",
        include_in_gold=False,
        fields=(
            FieldMapping(
                base_name="title",
                provider_columns=("chembl.publication.title",),
                group=FieldGroupId.BIBLIOGRAPHY,
            ),
        ),
    )
    registry = FieldGroupRegistry(groups=(group,))
    assert registry.is_gold_field("chembl.publication.title") is False


def test_aggregation_filter_condition_validated() -> None:
    ok = AggregationFieldSpec(
        source_field="term",
        agg_function=AggregationFunction.COLLECT_LIST,
        filter_condition="term_type == 'MESH_HEADING'",
    )
    assert ok.filter_condition is not None
    with pytest.raises(ValueError, match="unsupported syntax"):
        AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COUNT,
            filter_condition="term LIKE '%x%'",
        )


def test_dependency_timeout_doc_behavior() -> None:
    result = DependencyResult.timeout(
        "dep", timeout_seconds=30.0, duration_seconds=12.0
    )
    assert result.duration_seconds == 12.0
    defaulted = DependencyResult.timeout("dep", timeout_seconds=30.0)
    assert defaulted.duration_seconds == 30.0
