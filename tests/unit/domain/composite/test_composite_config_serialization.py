# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Regression snapshots for CompositeConfig serialization."""

from __future__ import annotations

import pytest

from bioetl.domain.composite.config import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    ColumnGroupConfig,
    CompositeConfig,
    CompositeDQConfig,
    CrossValidationConfig,
    DependencyConfig,
    DQOverrideConfig,
    EnricherCardinality,
    EnricherConfig,
    ExecutionConfig,
    LineageConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.config_composite_section_decoders import (
    build_cross_validation_config,
    build_dq_config,
    build_execution_config,
    build_lineage_config,
)
from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    EnricherFieldPairing,
    FieldComparisonSpec,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


pytestmark = pytest.mark.unit


def _build_composite_config() -> CompositeConfig:
    return CompositeConfig(
        name="composite_publication",
        version="1.0.0",
        seed=SeedConfig(
            pipeline="chembl_publication",
            output_keys=("doi", "pmid"),
            silver_table="silver/chembl/publication",
        ),
        dependencies=(
            DependencyConfig(
                pipeline="chembl_document",
                join_keys=("doi",),
                required=False,
                timeout_seconds=600,
                silver_table="silver/chembl/document",
                filter_fields=("doi",),
            ),
        ),
        enrichers=(
            EnricherConfig(
                pipeline="crossref_publication",
                join_keys=("doi",),
                required=True,
                timeout_seconds=900,
            ),
        ),
        merge=MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver/composite/publication",
            output_gold_path="gold/composite/publication",
            sort_by_silver=("doi",),
            sort_by_gold=("doi",),
        ),
    )


def test_composite_config_to_dict_snapshot() -> None:
    config = _build_composite_config()
    payload = config.to_dict()

    assert payload["name"] == "composite_publication"
    assert payload["version"] == "1.0.0"
    assert payload["seed"] == {
        "pipeline": "chembl_publication",
        "output_keys": ["doi", "pmid"],
        "silver_table": "silver/chembl/publication",
        "limit": None,
    }
    assert payload["dependencies"][0]["pipeline"] == "chembl_document"
    assert payload["dependencies"][0]["filter_fields"] == ["doi"]
    assert payload["enrichers"][0]["pipeline"] == "crossref_publication"
    assert payload["enrichers"][0]["timeout_seconds"] == 900
    assert payload["enrichers"][0]["cardinality"] == "one_to_one"
    assert payload["merge"]["strategy"] == "left_outer"
    assert payload["merge"]["sort_by_silver"] == ["doi"]
    assert payload["merge"]["preserve_all_sources"] is False
    # Lossless surface includes top-level runtime blocks.
    assert set(payload) >= {
        "dq",
        "execution",
        "lineage",
        "cross_validation",
        "merge",
        "seed",
        "enrichers",
        "dependencies",
    }


def test_composite_config_from_dict_roundtrip_snapshot() -> None:
    original = _build_composite_config()
    serialized = original.to_dict()

    restored = CompositeConfig.from_dict(serialized)

    assert restored.to_dict() == serialized
    assert restored.name == original.name
    assert restored.version == original.version
    assert restored.seed.output_keys == original.seed.output_keys
    assert restored.merge.strategy == original.merge.strategy
    assert restored.merge.conflict_resolution == original.merge.conflict_resolution


def test_composite_config_codec_roundtrips_all_business_sections() -> None:
    config = CompositeConfig(
        name="composite_publication",
        version="2.0.0",
        seed=SeedConfig(
            pipeline="chembl_publication",
            output_keys=("doi",),
            silver_table="silver/chembl/publication",
            limit=100,
        ),
        dependencies=(),
        enrichers=(
            EnricherConfig(
                pipeline="openalex_publication",
                join_keys=("doi",),
                required=True,
                cardinality=EnricherCardinality.MANY_TO_ONE,
                aggregation=AggregationConfig(
                    group_by="doi",
                    order_by=("publication_year",),
                    fields=(
                        AggregationFieldSpec(
                            source_field="concept_name",
                            agg_function=AggregationFunction.COLLECT_SET,
                            filter_condition="concept_name IS NOT NULL",
                            output_field="concepts",
                        ),
                    ),
                ),
            ),
        ),
        merge=MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver/composite/publication",
            output_gold_path="gold/composite/publication",
            column_groups=(
                ColumnGroupConfig(
                    name="identity",
                    fields=("doi", "pmid"),
                    provider_order=("chembl", "openalex"),
                ),
            ),
        ),
        dq=CompositeDQConfig(
            soft_fail_threshold=0.2,
            hard_fail_threshold=0.6,
            required_fields=("doi", "title"),
            enricher_overrides={
                "openalex_publication": DQOverrideConfig(
                    soft_fail_threshold=0.25,
                    hard_fail_threshold=0.65,
                )
            },
        ),
        execution=ExecutionConfig(
            max_concurrency=2,
            checkpoint_enabled=False,
            retry_max_attempts=5,
            retry_backoff_multiplier=1.5,
        ),
        lineage=LineageConfig(
            track_field_sources=True,
            track_timestamps=False,
            track_status=True,
            provider_lookup_fields={"openalex": {"doi": "doi"}},
            track_source_for_fields=("title",),
        ),
        cross_validation=CrossValidationConfig(
            warning_threshold=1,
            error_threshold=3,
            quarantine_threshold=2,
            fuzzy_threshold=0.9,
            numeric_tolerance=0.05,
            enricher_pairings=(
                EnricherFieldPairing(
                    enricher_pipeline="openalex_publication",
                    fields=(
                        FieldComparisonSpec(
                            field_name="title",
                            method=ComparisonMethod.FUZZY,
                            threshold=0.9,
                        ),
                    ),
                ),
            ),
        ),
    )

    payload = config.to_dict()
    restored = CompositeConfig.from_dict(payload)

    assert restored.to_dict() == payload
    assert payload["enrichers"][0]["aggregation"] == {
        "group_by": "doi",
        "order_by": ["publication_year"],
        "fields": [
            {
                "source_field": "concept_name",
                "agg_function": "collect_set",
                "filter_condition": "concept_name IS NOT NULL",
                "output_field": "concepts",
            }
        ],
    }
    assert payload["merge"]["column_groups"][0]["name"] == "identity"
    assert payload["dq"]["enricher_overrides"]["openalex_publication"] == {
        "soft_fail_threshold": 0.25,
        "hard_fail_threshold": 0.65,
    }
    assert payload["cross_validation"]["enricher_pairings"][0]["fields"] == [
        {"field_name": "title", "method": "fuzzy", "threshold": 0.9}
    ]


def test_composite_section_decoders_filter_invalid_nested_shapes() -> None:
    dq = build_dq_config(
        {
            "required_fields": ["doi"],
            "enricher_overrides": {
                "openalex": {
                    "soft_fail_threshold": 0.2,
                    "hard_fail_threshold": 0.7,
                },
                "ignored": "not-an-object",
            },
        }
    )
    execution = build_execution_config({})
    lineage = build_lineage_config(
        {
            "provider_lookup_fields": {
                "openalex": {"work_id": "id"},
                "ignored": "not-an-object",
            },
            "track_source_for_fields": ["title"],
        }
    )
    cross_validation = build_cross_validation_config(
        {
            "enricher_pairings": [
                "not-an-object",
                {
                    "enricher_pipeline": "openalex_publication",
                    "fields": [
                        "not-an-object",
                        {
                            "field_name": "doi",
                            "method": ComparisonMethod.EXACT,
                            "threshold": 0.0,
                        },
                    ],
                },
            ]
        }
    )

    assert set(dq.enricher_overrides) == {"openalex"}
    assert execution.max_concurrency == 4
    assert lineage.provider_lookup_fields == {"openalex": {"work_id": "id"}}
    assert cross_validation.enricher_pairings[0].fields[0].method is (
        ComparisonMethod.EXACT
    )
