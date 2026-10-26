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
"""Unit tests for infrastructure.schemas.composite_config branches."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from bioetl.infrastructure.config.composite_config_api import load_composite_config

from bioetl.infrastructure.schemas._composite_config_merge_schema import (
    ColumnGroupSchema,
    MergeOutputSchema,
    TargetProteinClassificationProjectionSchema,
)
from bioetl.infrastructure.schemas.composite_config import (
    AggregationFieldSchema,
    AggregationSchema,
    CompositeConfigFileSchema,
    CompositeConfigSchema,
    CompositeDQSchema,
    CrossValidationSchema,
    DependencySchema,
    DQOverrideSchema,
    EnricherFieldPairingSchema,
    EnricherSchema,
    ExecutionSchema,
    FieldComparisonSpecSchema,
    LineageSchema,
    MergeSchema,
    MergeSortBySchema,
    NormalizedAnchorPolicySchema,
    NormalizedJoinKeyPolicySchema,
    PublicationIdentityJoinPolicySchema,
    PubchemCompoundAnchorSchema,
    PubchemCompoundJoinBoundarySchema,
    RetrySchema,
    SeedSchema,
    UniprotIdMappingAnchorSchema,
    UniprotIdMappingJoinBoundarySchema,
    validate_composite_config_payload,
)


pytestmark = pytest.mark.unit


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
    field = AggregationFieldSchema(source="term", agg="collect_list", filter="x != 0")
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


def test_merge_schema_conflict_resolution_alias_mapping() -> None:
    # Test valid literal configurations mapping cleanly to expected domain Enums
    mappings = {
        "seed_priority": "seed_priority",
        "enricher_priority": "enricher",
        "latest_timestamp": "latest",
        "explicit_rules": "explicit",
        "coalesce": "coalesce",
        # Test aliases mapping identically
        "enricher": "enricher",
        "latest": "latest",
        "explicit": "explicit",
    }

    for literal_val, expected_domain_val in mappings.items():
        merge = MergeSchema.model_validate(
            {
                "strategy": "left_outer",
                "conflict_resolution": literal_val,
                "output": {"silver": "silver/path", "gold": "gold/path"},
                "sort_by": {"silver": ["entity_id"], "gold": ["entity_id"]},
                **(
                    {"field_priorities": {"f": ["x"]}}
                    if literal_val in ("explicit_rules", "explicit")
                    else {}
                ),
            }
        )
        assert merge.to_domain().conflict_resolution.value == expected_domain_val


def test_merge_schema_invalid_conflict_resolution() -> None:
    # Prove unknown literal fails validation explicitly before hitting Domain
    with pytest.raises(ValidationError, match="Input should be"):
        MergeSchema.model_validate(
            {
                "strategy": "left_outer",
                "conflict_resolution": "unknown_value",
                "output": {"silver": "silver/path", "gold": "gold/path"},
                "sort_by": {"silver": ["entity_id"], "gold": ["entity_id"]},
            }
        )


@pytest.mark.parametrize("strategy", ["explicit_rules", "explicit"])
@pytest.mark.parametrize("priorities", [None, {}])
def test_merge_schema_explicit_alias_requires_priorities(
    strategy: str, priorities: dict[str, list[str]] | None
) -> None:
    """Reject both explicit spellings before domain conversion without priorities."""
    payload = {
        "conflict_resolution": strategy,
        "output": {"silver": "silver/path", "gold": "gold/path"},
        "sort_by": {"silver": ["entity_id"], "gold": ["entity_id"]},
    }
    if priorities is not None:
        payload["field_priorities"] = priorities
    with pytest.raises(ValidationError, match="field_priorities required"):
        MergeSchema.model_validate(payload)


def test_merge_sort_by_schema_forbids_extra() -> None:
    """Reject unknown fields in sort_by (like leaked field_priorities)."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        MergeSchema.model_validate(
            {
                "strategy": "left_outer",
                "conflict_resolution": "coalesce",
                "output": {"silver": "s", "gold": "g"},
                "sort_by": {"silver": ["id"], "gold": ["id"], "unknown_key": ["x"]},
            }
        )


def test_merge_sort_by_json_schema_forbids_additional_properties() -> None:
    """Published MergeSortBySchema must reject keys outside silver/gold."""
    schema = MergeSortBySchema.model_json_schema()
    assert schema["additionalProperties"] is False


def _assert_extra_forbidden(exc_info: pytest.ExceptionInfo[ValidationError]) -> None:
    assert any(err["type"] == "extra_forbidden" for err in exc_info.value.errors())


@pytest.mark.parametrize(
    ("schema_cls", "payload"),
    [
        (
            AggregationFieldSchema,
            {"source": "term", "agg": "collect_list", "unknown_key": 1},
        ),
        (
            AggregationSchema,
            {
                "group_by": "publication_id",
                "fields": {"terms": {"source": "term", "agg": "first"}},
                "unknown_key": 1,
            },
        ),
        (
            SeedSchema,
            {
                "pipeline": "chembl_publication",
                "output_keys": ["doi"],
                "silver_table": "silver/chembl/publication",
                "unknown_key": 1,
            },
        ),
        (
            EnricherSchema,
            {
                "pipeline": "crossref_publication",
                "join_keys": ["doi"],
                "unknown_key": 1,
            },
        ),
        (MergeOutputSchema, {"silver": "s", "gold": "g", "unknown_key": 1}),
        (
            ColumnGroupSchema,
            {"name": "system", "fields": ["entity_id"], "unknown_key": 1},
        ),
        (TargetProteinClassificationProjectionSchema, {"unknown_key": 1}),
        (
            DependencySchema,
            {
                "pipeline": "uniprot_idmapping",
                "join_keys": ["target_id"],
                "filter_condition": "target_id IS NOT NULL",
            },
        ),
        (RetrySchema, {"max_attempts": 2, "unknown_key": 1}),
        (ExecutionSchema, {"max_concurrency": 2, "unknown_key": 1}),
        (LineageSchema, {"track_status": False, "unknown_key": 1}),
        (
            FieldComparisonSpecSchema,
            {"field": "doi", "method": "exact", "unknown_key": 1},
        ),
        (
            EnricherFieldPairingSchema,
            {
                "enricher_pipeline": "crossref_publication",
                "fields": [{"field": "doi"}],
                "unknown_key": 1,
            },
        ),
        (CrossValidationSchema, {"enabled": True, "unknown_key": 1}),
        (CompositeConfigSchema, {"name": "composite_publication", "unknown_key": 1}),
        (CompositeConfigFileSchema, {"schema_version": "2.0.0", "unknown_key": 1}),
        (
            PublicationIdentityJoinPolicySchema,
            {"rationale": "identifiers first", "unknown_key": 1},
        ),
        (
            NormalizedJoinKeyPolicySchema,
            {
                "publication_identity": {"rationale": "identifiers first"},
                "unknown_key": 1,
            },
        ),
        (
            PubchemCompoundJoinBoundarySchema,
            {
                "active_join_keys": ["inchi_key"],
                "retained_validation_anchors": ["standardized_inchi_key"],
                "activation_condition": "seed emits anchors",
                "rationale": "retained for validation",
                "unknown_key": 1,
            },
        ),
        (
            PubchemCompoundAnchorSchema,
            {
                "join_boundary": {
                    "active_join_keys": ["inchi_key"],
                    "retained_validation_anchors": ["standardized_inchi_key"],
                    "activation_condition": "seed emits anchors",
                    "rationale": "retained for validation",
                },
                "unknown_key": 1,
            },
        ),
        (
            UniprotIdMappingJoinBoundarySchema,
            {
                "source_anchor": "target_id",
                "normalized_output_anchor": "uniprot_accession",
                "required_status": "found",
                "downstream_pipeline": "uniprot_protein",
                "rationale": "chain through idmapping",
                "unknown_key": 1,
            },
        ),
        (
            UniprotIdMappingAnchorSchema,
            {
                "join_boundary": {
                    "source_anchor": "target_id",
                    "normalized_output_anchor": "uniprot_accession",
                    "required_status": "found",
                    "downstream_pipeline": "uniprot_protein",
                    "rationale": "chain through idmapping",
                },
                "unknown_key": 1,
            },
        ),
        (
            NormalizedAnchorPolicySchema,
            {
                "pubchem_compound": {
                    "join_boundary": {
                        "active_join_keys": ["inchi_key"],
                        "retained_validation_anchors": ["standardized_inchi_key"],
                        "activation_condition": "seed emits anchors",
                        "rationale": "retained for validation",
                    }
                },
                "unknown_key": 1,
            },
        ),
    ],
)
def test_composite_schema_classes_reject_unknown_keys(
    schema_cls: type,
    payload: dict[str, object],
) -> None:
    """Unknown keys fail as extra_forbidden, not as an import or runtime error."""
    with pytest.raises(ValidationError) as exc_info:
        schema_cls.model_validate(payload)
    _assert_extra_forbidden(exc_info)


def test_nested_composite_config_rejects_unknown_keys() -> None:
    """Unknown keys inside the real composite payload use extra_forbidden."""
    nested_payloads: list[dict[str, object]] = []

    seed_payload = _base_payload()
    seed = seed_payload["seed"]
    assert isinstance(seed, dict)
    seed["unknown_key"] = 1
    nested_payloads.append(seed_payload)

    enricher_payload = _base_payload()
    enrichers = enricher_payload["enrichers"]
    assert isinstance(enrichers, list)
    enrichers[0]["unknown_key"] = 1
    nested_payloads.append(enricher_payload)

    aggregation_payload = _base_payload()
    aggregation_enrichers = aggregation_payload["enrichers"]
    assert isinstance(aggregation_enrichers, list)
    aggregation_enrichers[0]["cardinality"] = "many_to_one"
    aggregation_enrichers[0]["aggregation"] = {
        "group_by": "doi",
        "unknown_key": 1,
        "fields": {"terms": {"source": "term", "agg": "collect_list"}},
    }
    nested_payloads.append(aggregation_payload)

    field_payload = _base_payload()
    field_enrichers = field_payload["enrichers"]
    assert isinstance(field_enrichers, list)
    field_enrichers[0]["cardinality"] = "many_to_one"
    field_enrichers[0]["aggregation"] = {
        "group_by": "doi",
        "fields": {
            "terms": {"source": "term", "agg": "collect_list", "unknown_key": 1}
        },
    }
    nested_payloads.append(field_payload)

    output_payload = _base_payload()
    merge = output_payload["merge"]
    assert isinstance(merge, dict)
    output = merge["output"]
    assert isinstance(output, dict)
    output["unknown_key"] = 1
    nested_payloads.append(output_payload)

    group_payload = _base_payload()
    group_merge = group_payload["merge"]
    assert isinstance(group_merge, dict)
    group_merge["column_groups"] = [
        {"name": "system", "fields": ["entity_id"], "unknown_key": 1}
    ]
    nested_payloads.append(group_payload)

    projection_payload = _base_payload()
    projection_merge = projection_payload["merge"]
    assert isinstance(projection_merge, dict)
    projection_merge["target_protein_classification_projection"] = {"unknown_key": 1}
    nested_payloads.append(projection_payload)

    for payload in nested_payloads:
        with pytest.raises(ValidationError) as exc_info:
            CompositeConfigSchema.model_validate(payload)
        _assert_extra_forbidden(exc_info)


def test_nested_dependency_execution_and_policy_reject_unknown_keys() -> None:
    """Unknown keys fail inside dependency, execution, and declared policy blocks."""
    dependency_payload = _base_payload()
    dependency_payload["dependencies"] = [
        {
            "pipeline": "uniprot_idmapping",
            "join_keys": ["target_id"],
            "filter_condition": "target_id IS NOT NULL",
        }
    ]
    execution_payload = _base_payload()
    execution_payload["execution"] = {"retry": {"max_attempts": 2, "unknown_key": 1}}
    policy_payload = _base_payload()
    policy_payload["normalized_join_key_policy"] = {
        "publication_identity": {
            "primary_join_keys": ["doi"],
            "fallback_join_keys": [],
            "rationale": "identifiers first",
            "unknown_key": 1,
        }
    }
    file_payload = {
        "schema_version": "2.0.0",
        "composite": _base_payload(),
        "unknown_key": 1,
    }

    for payload in (dependency_payload, execution_payload, policy_payload):
        with pytest.raises(ValidationError) as exc_info:
            CompositeConfigSchema.model_validate(payload)
        _assert_extra_forbidden(exc_info)

    with pytest.raises(ValidationError) as exc_info:
        CompositeConfigFileSchema.model_validate(file_payload)
    _assert_extra_forbidden(exc_info)


def test_real_composite_configs_keep_domain_and_declared_policies() -> None:
    """Tracked composite YAML stays loadable, and the removed dependency key stays absent."""
    config_dir = Path("configs/composites")
    for config_path in sorted(config_dir.glob("*.yaml")):
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert isinstance(raw, dict)
        schema = validate_composite_config_payload(raw)
        domain = load_composite_config(config_path.stem)
        assert schema.to_domain().name == domain.name
        assert schema.composite.normalized_anchor_policy is not None
        assert schema.composite.normalized_join_key_policy is not None

    target_raw = yaml.safe_load(
        (config_dir / "target.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(target_raw, dict)
    dependencies = target_raw["composite"]["dependencies"]
    assert isinstance(dependencies, list)
    assert all("filter_condition" not in item for item in dependencies)

    target = load_composite_config("target")
    dependency = next(
        item for item in target.dependencies if item.pipeline == "uniprot_idmapping"
    )
    assert dependency.join_keys == ("target_id",)
    assert dependency.key_filter is None
    assert not hasattr(dependency, "filter_condition")

    target_schema = validate_composite_config_payload(
        yaml.safe_load((config_dir / "target.yaml").read_text(encoding="utf-8"))
    )
    anchor = target_schema.composite.normalized_anchor_policy
    assert anchor is not None
    assert anchor.uniprot_idmapping.join_boundary.source_anchor == "target_id"
    join_policy = target_schema.composite.normalized_join_key_policy
    assert join_policy is not None
    assert join_policy.publication_identity.primary_join_keys == []


def test_forbid_schemas_keep_valid_defaults_and_to_domain() -> None:
    """Declared defaults and domain conversion stay intact."""
    field = AggregationFieldSchema(source="term", agg="first")
    assert field.filter is None
    assert field.to_domain("terms").output_field == "terms"

    aggregation = AggregationSchema(group_by="publication_id", fields={"terms": field})
    assert aggregation.order_by == []
    domain_aggregation = aggregation.to_domain()
    assert domain_aggregation.group_by == "publication_id"
    assert domain_aggregation.order_by == ()

    seed = SeedSchema(
        pipeline="chembl_publication",
        output_keys=["doi"],
        silver_table="silver/chembl/publication",
    )
    assert seed.limit is None
    assert seed.to_domain().limit is None

    enricher = EnricherSchema(pipeline="crossref_publication", join_keys=["doi"])
    assert enricher.required is False
    assert enricher.fallback_strategy == "skip"
    assert enricher.cardinality == "one_to_one"
    assert enricher.to_domain().filter_condition is None

    output = MergeOutputSchema(silver="silver/path", gold="gold/path")
    assert output.silver == "silver/path"
    group = ColumnGroupSchema(name="system", fields=["entity_id"])
    assert group.pattern is None
    assert group.provider_order[0] == "chembl"
    projection = TargetProteinClassificationProjectionSchema()
    assert projection.include_protein_classifications is True
    assert projection.levels == [1, 2, 3, 4, 5]
    assert (
        projection.expand_field_mappings()[
            "chembl.target_protein_classification.protein_classifications"
        ]
        == "protein_classifications"
    )

    payload = _base_payload()
    merge = payload["merge"]
    assert isinstance(merge, dict)
    merge["column_groups"] = [{"name": "system", "fields": ["entity_id"]}]
    merge["target_protein_classification_projection"] = {
        "levels": [1],
        "include_protein_classifications": False,
    }
    loaded = CompositeConfigSchema.model_validate(payload)
    domain = loaded.to_domain()
    assert loaded.normalized_anchor_policy is None
    assert loaded.normalized_join_key_policy is None
    assert domain.seed.pipeline == "chembl_publication"
    assert domain.merge.column_groups[0].name == "system"
    assert domain.enrichers[0].join_keys == ("doi",)

    dependency = DependencySchema(pipeline="uniprot_idmapping", join_keys=["target_id"])
    assert dependency.required is False
    assert dependency.timeout_seconds == 600
    assert dependency.key_filter is None
    assert dependency.to_domain().key_filter is None

    execution = ExecutionSchema()
    assert execution.max_concurrency == 4
    assert execution.retry.max_attempts == 3
    assert execution.to_domain().retry_max_attempts == 3
    assert LineageSchema().track_field_sources is True
    assert CrossValidationSchema().enabled is True


@pytest.mark.parametrize(
    "schema_cls",
    [
        AggregationFieldSchema,
        AggregationSchema,
        SeedSchema,
        EnricherSchema,
        MergeOutputSchema,
        ColumnGroupSchema,
        TargetProteinClassificationProjectionSchema,
        DependencySchema,
        RetrySchema,
        ExecutionSchema,
        LineageSchema,
        FieldComparisonSpecSchema,
        EnricherFieldPairingSchema,
        CrossValidationSchema,
        CompositeConfigSchema,
        CompositeConfigFileSchema,
        NormalizedAnchorPolicySchema,
        NormalizedJoinKeyPolicySchema,
    ],
)
def test_composite_schema_json_forbids_additional_properties(schema_cls: type) -> None:
    schema = schema_cls.model_json_schema()
    assert schema["additionalProperties"] is False
