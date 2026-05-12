"""Unit tests for infrastructure.schemas.composite_config branches."""

from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from bioetl.infrastructure.schemas.composite_config import (
    AggregationFieldSchema,
    AggregationSchema,
    ColumnGroupSchema,
    CompositeConfigSchema,
    CompositeDQSchema,
    CrossValidationSchema,
    DependencySchema,
    DQOverrideSchema,
    EnricherSchema,
    ExecutionSchema,
    MergeSchema,
    SeedSchema,
)


def _base_payload() -> dict[str, object]:
    return {
        "name": "composite_publication",
        "version": "1.0.0",
        "seed": {
            "pipeline": "chembl_publication",
            "output_keys": ["doi", "pmid"],
            "silver_table": "silver/chembl/publication",
        },
        "dependencies": [],
        "enrichers": [
            {
                "pipeline": "crossref_publication",
                "join_keys": ["doi"],
            }
        ],
        "merge": {
            "output": {
                "silver": "silver/composite/publication",
                "gold": "gold/composite/publication",
            },
            "sort_by": {
                "silver": ["entity_id", "publication_id"],
                "gold": ["entity_id", "publication_id"],
            },
        },
    }


def test_aggregation_schemas_to_domain() -> None:
    field = AggregationFieldSchema(source="term", agg="collect_list", filter="x > 0")
    domain_field = field.to_domain("terms")
    assert domain_field.output_field == "terms"

    aggregation = AggregationSchema(
        group_by="publication_id",
        fields={"terms": field},
    )
    domain_aggregation = aggregation.to_domain()
    assert domain_aggregation.group_by == "publication_id"
    assert len(domain_aggregation.fields) == 1


def test_seed_schema_validator_and_to_domain_paths() -> None:
    with pytest.raises(ValueError, match="output_keys cannot be empty"):
        SeedSchema.validate_output_keys_not_empty([])
    with pytest.raises(ValueError, match="output_keys cannot contain empty strings"):
        SeedSchema.validate_output_keys_not_empty(["  "])

    seed = SeedSchema(
        pipeline="chembl_publication",
        output_keys=["doi"],
        silver_table="silver/chembl/publication",
    )
    assert seed.to_domain().output_keys == ("doi",)


def test_dependency_schema_validator_and_to_domain_paths() -> None:
    with pytest.raises(ValueError, match="join_keys cannot be empty"):
        DependencySchema.validate_join_keys_not_empty([])
    with pytest.raises(ValueError, match="join_keys cannot contain empty strings"):
        DependencySchema.validate_join_keys_not_empty([" "])

    with pytest.raises(ValidationError, match="mutually exclusive"):
        DependencySchema.model_validate(
            {
                "pipeline": "chembl_document",
                "join_keys": ["doi"],
                "filter_field": "doi",
                "filter_fields": ["doi"],
            }
        )

    dependency = DependencySchema.model_validate(
        {
            "pipeline": "chembl_document",
            "join_keys": ["doi"],
            "key_source": "seed",
            "filter_fields": ["doi", "pmid"],
            "key_filter": "doi IS NOT NULL",
        }
    )
    assert dependency.to_domain().filter_fields == ("doi", "pmid")


def test_enricher_schema_validation_and_to_domain() -> None:
    with pytest.raises(ValidationError, match="requires aggregation config"):
        EnricherSchema.model_validate(
            {
                "pipeline": "chembl_publication_term",
                "join_keys": ["doi"],
                "cardinality": "many_to_one",
            }
        )

    enricher = EnricherSchema.model_validate(
        {
            "pipeline": "chembl_publication_term",
            "join_keys": ["doi"],
            "cardinality": "many_to_one",
            "aggregation": {
                "group_by": "doi",
                "fields": {
                    "terms": {
                        "source": "term",
                        "agg": "collect_list",
                    }
                },
            },
        }
    )
    assert enricher.to_domain().aggregation is not None


def test_merge_and_column_group_validation_paths() -> None:
    with pytest.raises(ValidationError, match="must have either fields or pattern"):
        ColumnGroupSchema.model_validate({"name": "empty"})

    with pytest.raises(ValidationError, match="field_priorities required"):
        MergeSchema.model_validate(
            {
                "conflict_resolution": "explicit_rules",
                "output": {"silver": "silver/path", "gold": "gold/path"},
                "sort_by": {"silver": ["entity_id"], "gold": ["entity_id"]},
            }
        )

    merge = MergeSchema.model_validate(
        {
            "strategy": "left_outer",
            "conflict_resolution": "coalesce",
            "output": {"silver": "silver/path", "gold": "gold/path"},
            "sort_by": {"silver": ["entity_id"], "gold": ["entity_id"]},
            "normalization_compatibility_overrides": {"title": "reviewed bridge"},
            "column_groups": [{"name": "ids", "fields": ["doi"]}],
        }
    )
    assert merge.to_domain().output_silver_path == "silver/path"
    assert (
        merge.to_domain().normalization_compatibility_overrides["title"]
        == "reviewed bridge"
    )


def test_dq_and_execution_schema_to_domain_paths() -> None:
    override = DQOverrideSchema(soft_fail_threshold=0.1, hard_fail_threshold=0.2)
    assert override.to_domain().hard_fail_threshold == pytest.approx(0.2)

    composite_dq = CompositeDQSchema(
        soft_fail_threshold=0.1,
        hard_fail_threshold=0.3,
        enricher_overrides={"crossref": {"soft_fail_threshold": 0.2}},
        required_fields=["title"],
    )
    assert composite_dq.to_domain().required_fields == ("title",)

    execution = ExecutionSchema()
    assert execution.to_domain().max_concurrency == 4


def test_cross_validation_schema_threshold_validation() -> None:
    with pytest.raises(
        ValidationError, match="warning_threshold must be < error_threshold"
    ):
        CrossValidationSchema.model_validate(
            {"warning_threshold": 2, "error_threshold": 2}
        )


def test_composite_config_schema_requires_enricher_or_dependency() -> None:
    payload = _base_payload()
    payload["enrichers"] = []
    payload["dependencies"] = []

    with pytest.raises(
        ValidationError,
        match="composite must have at least one enricher or dependency",
    ):
        CompositeConfigSchema.model_validate(payload)


def test_composite_config_schema_enricher_join_key_validation() -> None:
    payload = _base_payload()
    payload["enrichers"] = [{"pipeline": "crossref_publication", "join_keys": ["isbn"]}]

    with pytest.raises(ValidationError, match="join_key 'isbn'"):
        CompositeConfigSchema.model_validate(payload)


def test_composite_config_schema_enricher_validation_skips_when_no_enrichers() -> None:
    payload = _base_payload()
    payload["enrichers"] = []
    payload["dependencies"] = [
        {
            "pipeline": "chembl_document",
            "join_keys": ["doi"],
            "silver_table": "silver/chembl/document",
        }
    ]

    schema = CompositeConfigSchema.model_validate(payload)
    assert schema.enrichers == []


def test_composite_config_schema_dependency_key_validation_and_chained_skip() -> None:
    payload = _base_payload()
    payload["enrichers"] = []
    payload["dependencies"] = [
        {
            "pipeline": "chembl_chained",
            "join_keys": ["protein_classification_id"],
            "key_source": "chembl_target_component",
            "silver_table": "silver/chembl/chained",
        }
    ]
    schema = CompositeConfigSchema.model_validate(payload)
    assert schema.dependencies[0].key_source == "chembl_target_component"

    payload_bad = deepcopy(payload)
    payload_bad["dependencies"] = [
        {
            "pipeline": "chembl_document",
            "join_keys": ["document_id"],
            "silver_table": "silver/chembl/document",
        }
    ]
    with pytest.raises(
        ValidationError, match="Dependency chembl_document join_key 'document_id'"
    ):
        CompositeConfigSchema.model_validate(payload_bad)


def test_composite_config_schema_unique_name_validations() -> None:
    payload = _base_payload()
    payload["enrichers"] = [
        {"pipeline": "crossref_publication", "join_keys": ["doi"]},
        {"pipeline": "crossref_publication", "join_keys": ["doi"]},
    ]
    with pytest.raises(ValidationError, match="Duplicate enricher pipelines"):
        CompositeConfigSchema.model_validate(payload)

    payload_dep = _base_payload()
    payload_dep["enrichers"] = []
    payload_dep["dependencies"] = [
        {"pipeline": "chembl_document", "join_keys": ["doi"]},
        {"pipeline": "chembl_document", "join_keys": ["doi"]},
    ]
    with pytest.raises(ValidationError, match="Duplicate dependency pipelines"):
        CompositeConfigSchema.model_validate(payload_dep)
