"""Domain coverage regression vectors for #8775."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior import schema_metadata_extractor
from bioetl.domain.behavior._preflight_governance_types import (
    GovernancePolicy,
    PreflightGovernanceConfig,
)
from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.composite_metadata_cv import (
    _is_truthy_marker,
    build_explainability_summary,
    empty_explainability_summary,
    safe_ratio,
)
from bioetl.domain.behavior.composite_metadata_helpers import (
    extract_composite_lineage_metadata,
    extract_composite_output_ext,
    resolve_final_value_source,
    resolve_priority_order,
)
from bioetl.domain.behavior.composite_validation_helpers import (
    _append_config_issue_if_invalid,
    _append_named_config_issue_if_invalid,
    _convert_to_aggregation_config,
    _convert_to_cross_validation_config,
    _get_layer_for_code,
    as_output_schema,
    as_source_names,
)
from bioetl.domain.behavior.composite_validation_layer import CompositeValidator
from bioetl.domain.behavior.cross_validation_source_helpers import compares_only_to_self
from bioetl.domain.behavior.cross_validation_validator import CrossValidationValidator
from bioetl.domain.behavior.dq_serializer import DQReportSerializer, to_dict
from bioetl.domain.behavior.merged_metadata_explainability import (
    MergedRecordExplanation,
)
from bioetl.domain.behavior.merged_metadata_explainability import (
    _deterministic_record_id,
    _json_fallback,
)
from bioetl.domain.behavior.normalization_config import NormalizationConfig
from bioetl.domain.behavior.preflight_governance import PreflightGovernor
from bioetl.domain.behavior.validation_helpers import (
    aggregation_field_name,
    aggregation_group_key,
)
from bioetl.domain.composite.config_composite_section_decoders import (
    _enricher_field_pairings,
    _field_comparison_specs,
)
from bioetl.domain.composite.aggregation import _coerce_text_tuple
from bioetl.domain.config.dq import DQReportConfig
from bioetl.domain.config.validation_rules import FieldValidation
from bioetl.domain.models.metadata import (
    SchemaColumnInspection,
    SchemaInspectionResult,
)
from bioetl.domain.lineage._shared import normalize_mapping
from bioetl.domain.mapping.publication_type_mapping import _normalize_pipe_separated
from bioetl.domain.normalization._control_plane_payloads import (
    _normalize_manifest_code_provenance,
)
from bioetl.domain.schemas.chembl.publication import _is_iso_calendar_date
from bioetl.domain.schemas.validators import _is_scalar_missing
from bioetl.domain.types._checkpoint_metadata_support import coerce_records_processed
from bioetl.domain.types.contract_identity import (
    _normalization_profile_identity_issues,
    _normalize_semver,
)
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)
from bioetl.domain.value_objects._run_context_create_support import (
    _coerce_transform_step_sequence,
    _resolve_create_input_value,
)


pytestmark = pytest.mark.unit


def test_preflight_config_hash_includes_immutable_overrides() -> None:
    config = PreflightGovernanceConfig(
        policy=GovernancePolicy.CI_STRICT,
        issue_code_overrides={"DQ-1": ValidationSeverity.WARNING},
    )

    assert isinstance(hash(config), int)


def test_aggregation_schema_helpers_cover_descriptor_shapes() -> None:
    assert AggregationValidator._field_names_from_list([{"name": "entity_id"}]) == {
        "entity_id"
    }
    assert AggregationValidator._collect_fallback_fields(
        {"columns": [{"name": "score"}], "field_names": ["entity_id"]}
    ) == {"score", "entity_id"}
    assert AggregationValidator._build_group_key({"group": None}, ["group"]) == (
        ("present", "NoneType", "null"),
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"group_by": [1]},
        {"aggregations": {1: "sum"}},
        {"aggregations": {"x": 1}},
        {"source_field": 1},
        {"provenance_tracking": "yes"},
    ],
)
def test_aggregation_config_rejects_typed_shape_errors(
    payload: dict[str, object],
) -> None:
    with pytest.raises(TypeError):
        _convert_to_aggregation_config(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"pairs": [1]},
        {"rules": {1: "equals"}},
        {"rules": {"x": 1}},
        {"strict_mode": "yes"},
        {"coverage_threshold": "high"},
        {"consistency_threshold": 2.0},
    ],
)
def test_cross_validation_config_rejects_typed_shape_errors(
    payload: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        _convert_to_cross_validation_config(payload)


def test_dq_serializer_handles_binary_and_nested_empty_collections() -> None:
    serializer = DQReportSerializer()

    assert to_dict({"payload": b"\x0f"})["payload"] == "0f"
    rendered = serializer._dict_to_yaml(
        {
            "nested": {"value": 1},
            "items": [{}, [], [1]],
        }
    )

    assert "nested:" in rendered
    assert "- {}" in rendered
    assert "- []" in rendered
    assert serializer._quote_yaml_string("a: b")


def test_explainability_ids_handle_mixed_keys_and_fallback_scalars() -> None:
    mixed = {1: "one", "2": "two"}  # type: ignore[dict-item]
    reordered = {"2": "two", 1: "one"}  # type: ignore[dict-item]
    assert _deterministic_record_id(mixed) == _deterministic_record_id(reordered)
    with pytest.raises(TypeError, match="Ambiguous mapping keys"):
        _deterministic_record_id({1: "numeric", "1": "string"})  # type: ignore[dict-item]
    assert _json_fallback(b"\x0f") == "0f"
    with pytest.raises(TypeError, match="Unsupported value"):
        _json_fallback(object())


def test_normalization_rejects_negative_high_potency_threshold() -> None:
    with pytest.raises(ValueError, match="high_potency_threshold cannot be negative"):
        NormalizationConfig(high_potency_threshold=-1)


def test_schema_metadata_normalizes_neutral_inspection() -> None:
    metadata = schema_metadata_extractor.extract_schema_metadata(
        SchemaInspectionResult(
            columns=(
                SchemaColumnInspection(
                    name="entity_id",
                    dtype="pandera.dtypes.String",
                    nullable=False,
                ),
            )
        )
    )
    assert metadata.columns[0].type == "String"
    assert metadata.columns[0].nullable is False


def test_schema_metadata_handles_missing_schema_surface() -> None:
    assert schema_metadata_extractor.extract_schema_metadata(None).columns == []


def test_composite_optional_sections_normalize_to_empty_tuples() -> None:
    assert _field_comparison_specs(None, path="fields") == ()
    assert _enricher_field_pairings(None) == ()


def test_dq_and_validation_rule_invalid_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="sample_size"):
        DQReportConfig(sample_size=-1)
    assert (
        FieldValidation(field="x", validation_type="range", max_value=1).max_value == 1
    )
    with pytest.raises(ValueError, match="min_value must be"):
        FieldValidation(field="x", validation_type="range", min_value=2, max_value=1)
    with pytest.raises(ValueError, match="validator name"):
        FieldValidation(field="x", validation_type="custom")


def test_run_context_create_coercion_rejects_invalid_vectors() -> None:
    with pytest.raises(TypeError, match="sequence of strings"):
        _coerce_transform_step_sequence([1])
    with pytest.raises(TypeError, match="sequence of strings"):
        _coerce_transform_step_sequence(object())
    with pytest.raises(TypeError, match="missing required argument"):
        _resolve_create_input_value(
            field_name="provider",
            inputs=None,
            overrides={},
        )


def test_composite_metadata_summary_helpers_cover_empty_and_populated_shapes() -> None:
    explanation = MergedRecordExplanation(
        record_id="record-1",
        composite_run_id="run-1",
        source_providers=("chembl",),
        field_explanations=(object(),),
        merge_strategy="prioritize",
        conflict_count=1,
        enrichment_count=1,
    )

    assert empty_explainability_summary()["record_count"] == 0
    assert safe_ratio(1, 0) == 0.0
    assert build_explainability_summary([explanation]) == {
        "record_count": 1,
        "field_count": 1,
        "avg_fields_per_record": 1.0,
        "source_provider_distribution": {"chembl": 1},
        "merge_strategy_distribution": {"prioritize": 1},
        "conflict_summary": {
            "total_conflicts": 1,
            "conflict_rate": 1.0,
            "records_with_conflicts": 1,
        },
        "enrichment_summary": {
            "total_enrichments": 1,
            "enrichment_rate": 1.0,
            "records_with_enrichments": 1,
        },
    }
    assert _is_truthy_marker(" yes ")
    assert _is_truthy_marker(1)


def test_composite_metadata_resolution_helpers_cover_priority_fallbacks() -> None:
    assert resolve_priority_order("title", None) is None
    assert resolve_priority_order("title", {"title": {"priority": "chembl"}}) == ()
    assert resolve_priority_order(
        "title", {"title": {"priority": ["pubmed", "chembl"]}}
    ) == ("pubmed", "chembl")
    assert resolve_final_value_source(source_providers=(), priority_order=None) is None
    assert (
        resolve_final_value_source(
            source_providers=("chembl", "pubmed"),
            priority_order=("pubmed", "chembl"),
        )
        == "pubmed"
    )
    assert (
        resolve_final_value_source(
            source_providers=("chembl",), priority_order=("pubmed",)
        )
        == "chembl"
    )
    assert (
        extract_composite_output_ext(
            [{"_source_providers": ["chembl"]}], partition_count=None
        )
        is not None
    )
    assert extract_composite_lineage_metadata([], composite_name="empty") is None


def test_composite_validation_compatibility_delegates_cover_all_shapes() -> None:
    issues = []
    _append_config_issue_if_invalid(
        issues=issues,
        is_valid=True,
        code=IssueCode.CMP_PF_FIELD_001,
        severity=ValidationSeverity.WARNING,
        message="unused",
    )
    assert issues == []
    assert as_output_schema({"properties": {}}) == ({"properties": {}}, [])
    assert as_output_schema("bad")[0] is None
    assert as_source_names(["chembl"]) == (["chembl"], [])
    assert as_source_names([1])[0] is None
    _append_named_config_issue_if_invalid(
        issues=issues,
        composite_config={},
        config_key="field_priorities",
        validator=lambda _value: True,
        code=IssueCode.CMP_PF_FIELD_001,
        severity=ValidationSeverity.WARNING,
        message="invalid",
        details_key="priorities",
    )
    _append_named_config_issue_if_invalid(
        issues=issues,
        composite_config={"field_priorities": "bad"},
        config_key="field_priorities",
        validator=lambda _value: True,
        code=IssueCode.CMP_PF_FIELD_001,
        severity=ValidationSeverity.WARNING,
        message="invalid",
        details_key="priorities",
    )
    assert len(issues) == 1
    assert (
        _get_layer_for_code(IssueCode.CMP_RT_CARD_001) is ValidationLayer.RUNTIME_GUARD
    )


def test_composite_validator_compatibility_methods_remain_wired() -> None:
    validator = CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )
    assert validator._deep_preflight_issues("bad")  # type: ignore[arg-type]
    issues = []
    validator._append_config_issue_if_invalid(
        issues=issues,
        composite_config={"field_priorities": "bad"},
        config_key="field_priorities",
        validator=lambda _value: True,
        code=IssueCode.CMP_PF_FIELD_001,
        severity=ValidationSeverity.WARNING,
        message="invalid",
        details_key="priorities",
    )
    assert (
        validator._create_issue(
            IssueCode.CMP_RT_CARD_001, ValidationSeverity.BLOCKER, "runtime"
        ).layer
        is ValidationLayer.RUNTIME_GUARD
    )
    assert validator._is_valid_field_priorities({}) is True
    assert issues


def test_low_level_group_key_and_self_comparison_helpers_preserve_types() -> None:
    assert aggregation_field_name(1) is None
    assert aggregation_group_key(
        {"none": None, "value": 1}, ["missing", "none", "value"]
    ) == (
        ("absent", "", ""),
        ("present", "NoneType", "null"),
        ("present", "int", "1"),
    )
    assert compares_only_to_self("chembl", ["chembl"])


def test_domain_normalization_edge_vectors_remain_fail_closed() -> None:
    assert _coerce_text_tuple(None, "group_by") == ()
    assert normalize_mapping({"tags": {"a"}})["tags"] == frozenset({"a"})
    assert _normalize_pipe_separated(" | ") is None
    assert _normalize_manifest_code_provenance(None) == {}
    assert _is_iso_calendar_date(20260817) is False
    with pytest.raises(ValueError, match="records_processed"):
        coerce_records_processed("")
    assert _normalize_semver("release") == "release"
    assert len(_normalization_profile_identity_issues("profile", None, "bad")) == 2


def test_scalar_missing_guard_handles_array_protocol_errors() -> None:
    class BrokenArray:
        def __array__(self) -> object:
            raise ValueError("broken array protocol")

    assert _is_scalar_missing(BrokenArray()) is False
