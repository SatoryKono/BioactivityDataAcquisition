# pyright: reportArgumentType=false
"""Focused tests for CR Stream B residual follow-up #8652."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import MappingProxyType

import pytest

from bioetl.domain.behavior._preflight_governance_types import (
    GovernancePolicy,
    PreflightGovernanceConfig,
)
from bioetl.domain.behavior.activity_aggregator import ActivityAggregator
from bioetl.domain.behavior.activity_aggregator._methods import AggregationMethod
from bioetl.domain.behavior.aggregation_validator import (
    AggregationConfig,
    AggregationValidator,
)
from bioetl.domain.behavior.composite_validation_helpers import (
    _convert_to_aggregation_config,
    _convert_to_cross_validation_config,
    _is_valid_field_priorities,
)
from bioetl.domain.behavior.composite_validation_layer import CompositeValidator
from bioetl.domain.behavior.cross_validation_validator import CrossValidationValidator
from bioetl.domain.behavior.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)
from bioetl.domain.behavior.preflight_governance import PreflightGovernor
from bioetl.domain.behavior.dq_serializer import DQReportSerializer, _serialize_value
from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.domain.behavior.merged_metadata_explainability import (
    MergedFieldExplanation,
    MergedMetadataExplainer,
    _count_conflicts_and_enrichments,
    _deterministic_record_id,
    _resolve_record_id,
)
from bioetl.domain.behavior.normalization_config import (
    NormalizationConfig,
    PChemblRangeConfig,
)
from bioetl.domain.behavior.organism_classification_service_models import (
    ClassificationStats,
)
from bioetl.domain.behavior.schema_classifier import SchemaClassifier
from bioetl.domain.behavior.schema_classifier_helpers import (
    build_field_type_change,
    removed_field_changes,
    added_field_changes,
)
from bioetl.domain.behavior.text_similarity import jaccard_similarity, normalize_text
from bioetl.domain.models.metadata import CompositeOutputExt
from bioetl.domain.types.schema_policy import (
    ChangeClassification,
    SchemaChangeType,
    SchemaCompatibilityPolicy,
)
from bioetl.domain.types.validation_severity import ValidationSeverity
from bioetl.domain.value_objects import Concentration, ConcentrationUnit

pytestmark = pytest.mark.unit


# --- 018 ---
def test_preflight_governance_overrides_are_immutable_proxy() -> None:
    raw = {"CMP-PF-001": ValidationSeverity.BLOCKER}
    cfg = PreflightGovernanceConfig(
        policy=GovernancePolicy.BLOCK_ON_ANY_ISSUE,
        issue_code_overrides=raw,
    )
    assert isinstance(cfg.issue_code_overrides, MappingProxyType)
    raw["CMP-PF-001"] = ValidationSeverity.WARNING
    assert cfg.issue_code_overrides["CMP-PF-001"] is ValidationSeverity.BLOCKER
    with pytest.raises(TypeError):
        cfg.issue_code_overrides["x"] = ValidationSeverity.WARNING  # type: ignore[index]


# --- 021 ---
def test_aggregator_extensions_propagate_none_to_default_method() -> None:
    agg = ActivityAggregator(default_method=AggregationMethod.MEAN)
    concentrations = [
        Concentration(value=1.0, unit=ConcentrationUnit.NANOMOLAR),
        Concentration(value=3.0, unit=ConcentrationUnit.NANOMOLAR),
    ]
    result = agg.aggregate_concentrations(concentrations, method=None)
    assert result.value == pytest.approx(2.0)
    filtered = agg.filter_and_aggregate([1.0, 3.0, 100.0], method=None, max_value=10.0)
    assert filtered == pytest.approx(2.0)


# --- 022 ---
def test_get_source_fields_extracts_names_from_field_descriptors() -> None:
    validator = AggregationValidator()
    schema = {
        "fields": [
            {"name": "x", "type": "string"},
            "y",
            {"name": "z"},
        ]
    }
    fields = validator._get_source_fields(schema)
    assert fields == {"x", "y", "z"}
    result = validator.validate_aggregation_config(
        AggregationConfig(group_by=["x"], aggregations={"y": "first"}),
        schema,
    )
    assert not any(issue.code.value.endswith("AGG-002") for issue in result.issues)


# --- 023-S1 / 023-S2 ---
def test_convert_aggregation_config_rejects_malformed_shapes() -> None:
    with pytest.raises(TypeError, match="group_by"):
        _convert_to_aggregation_config({"group_by": "x", "aggregations": {}})
    with pytest.raises(TypeError, match="aggregations"):
        _convert_to_aggregation_config({"group_by": ["x"], "aggregations": ["sum"]})


def test_convert_cross_validation_config_rejects_malformed_shapes() -> None:
    with pytest.raises(TypeError, match="pairs"):
        _convert_to_cross_validation_config({"pairs": "bad", "rules": {"a": "eq"}})
    with pytest.raises(TypeError, match="rules"):
        _convert_to_cross_validation_config({"pairs": [], "rules": ["eq"]})
    with pytest.raises(ValueError, match="coverage_threshold"):
        _convert_to_cross_validation_config(
            {"pairs": [], "rules": {"a": "eq"}, "coverage_threshold": 2.0}
        )


def _composite_validator() -> CompositeValidator:
    return CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )


def test_composite_validator_returns_issues_for_malformed_aggregation() -> None:
    validator = _composite_validator()
    issues = validator._validate_aggregation_config(
        {"group_by": "not-a-list", "aggregations": {"x": "sum"}},
        {"properties": {"x": {"type": "number"}}},
    )
    assert issues
    assert issues[0].severity is ValidationSeverity.BLOCKER


def test_composite_validator_returns_issues_for_malformed_cross_validation() -> None:
    validator = _composite_validator()
    issues = validator._validate_cross_validation_config(
        {"pairs": "bad", "rules": {"a": "eq"}},
        source_names=["chembl", "pubchem"],
    )
    assert issues
    assert issues[0].severity is ValidationSeverity.BLOCKER


# --- 026 ---
def test_disposition_overrides_unsupported_type_raises() -> None:
    from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
    from bioetl.domain.config.dq import DQConfig
    from bioetl.domain.types.dq_contracts import DQDisposition

    cfg = DQConfig(default_disposition_policy=DQDisposition.PASS)
    # Bypass model validation by injecting a bad attribute after construction
    object.__setattr__(cfg, "disposition_overrides", 123)  # type: ignore[misc]
    with pytest.raises(TypeError, match="disposition_overrides"):
        DQPolicyResolver(cfg)


# --- 028 / 053 ---
def test_field_explanation_propagates_merge_strategy_and_priority_source() -> None:
    explainer = MergedMetadataExplainer()
    metadata = CompositeOutputExt(
        composite_run_id="run-1",
        source_providers=["pubchem", "chembl"],
    )
    field = explainer.generate_field_explanation(
        "value",
        {"value": 1},
        metadata,
        field_priorities={"value": {"priority": ["chembl", "pubchem"]}},
        merge_strategy="union",
    )
    assert field.merge_strategy == "union"
    assert field.final_value_source == "chembl"
    assert field.conflict_resolution == "priority_based"

    record = explainer.generate_record_explanation(
        "r1",
        {"value": 1},
        metadata,
        field_priorities={"value": {"priority": ["chembl", "pubchem"]}},
        merge_strategy="union",
    )
    assert record.merge_strategy == "union"
    assert record.field_explanations[0].merge_strategy == "union"


# --- 030 / 047 / 065 ---
def test_serialize_value_handles_date_decimal_and_sets() -> None:
    assert _serialize_value(date(2026, 8, 11)) == "2026-08-11"
    assert _serialize_value(Decimal("1.25")) == "1.25"
    assert _serialize_value({3, 1, 2}) == [1, 2, 3]
    assert _serialize_value(frozenset({"b", "a"})) == ["a", "b"]


def test_yaml_empty_collections_and_scalar_quoting() -> None:
    serializer = DQReportSerializer()
    yaml_text = serializer._dict_to_yaml(
        {
            "validation_errors": [],
            "details": {},
            "label": "null",
            "quoted": 'a"b\\c',
        }
    )
    assert "validation_errors: []" in yaml_text
    assert "details: {}" in yaml_text
    # type-like and escaped strings stay quoted via safe_dump scalar path
    assert "null" in serializer._yaml_value("null")
    assert '"' in serializer._yaml_value('a"b') or "'" in serializer._yaml_value(
        'a"b'
    )


# --- 034 ---
def test_critical_drift_uses_required_schema_fields() -> None:
    calc = DQMetricsCalculator()
    metrics = calc.calculate(
        DQMetricsInput(
            records=[{"entity_id": "1"}],
            existing_schema_fields={"entity_id", "required_col", "optional_col"},
            required_schema_fields={"required_col"},
        )
    )
    assert metrics.schema_drift is not None
    assert metrics.schema_drift.status == "critical"
    assert "required_col" in metrics.schema_drift.missing_fields


# --- 036 ---
def test_group_key_preserves_types_and_absence() -> None:
    validator = AggregationValidator()
    key_int = validator._build_group_key({"g": 1}, ["g"])
    key_str = validator._build_group_key({"g": "1"}, ["g"])
    key_missing = validator._build_group_key({}, ["g"])
    key_literal = validator._build_group_key({"g": "MISSING"}, ["g"])
    assert key_int != key_str
    assert key_missing != key_literal
    result = validator.validate_post_aggregation_uniqueness(
        [{"g": 1}, {"g": "1"}],
        ["g"],
    )
    assert result.is_valid()  # distinct typed keys are not duplicates


# --- 040 ---
def test_field_priorities_reject_unhashable_and_duplicates() -> None:
    assert _is_valid_field_priorities({"a": {"priority": 1}, "b": {"priority": 2}})
    assert not _is_valid_field_priorities({"a": {"priority": [1, 2]}})
    assert not _is_valid_field_priorities(
        {"a": {"priority": 1}, "b": {"priority": 1}}
    )
    assert not _is_valid_field_priorities({"a": {}})


# --- 043 ---
def test_enrichment_count_dedupes_across_fields() -> None:
    fields = [
        MergedFieldExplanation(
            field_name="a",
            source_providers=["chembl"],
            merge_strategy="prioritize",
            enrichment_applied=["e1", "e2"],
        ),
        MergedFieldExplanation(
            field_name="b",
            source_providers=["chembl"],
            merge_strategy="prioritize",
            enrichment_applied=["e1", "e2"],
        ),
    ]
    conflicts, enrichments = _count_conflicts_and_enrichments(fields)
    assert conflicts == 0
    assert enrichments == 2


# --- 045 ---
def test_empty_include_set_is_explicit_hash_policy() -> None:
    service = EntityIdentityGenerator(content_hash_include_fields=set())
    assert service.has_explicit_content_hash_policy() is True
    empty_exclude = EntityIdentityGenerator(content_hash_exclude_fields=set())
    assert empty_exclude.has_explicit_content_hash_policy() is True
    default = EntityIdentityGenerator()
    assert default.has_explicit_content_hash_policy() is False
    assert default._content_hash_exclude_fields is None


# --- 048-S1 / 048-S2 ---
def test_resolve_record_id_preserves_falsy_identifiers() -> None:
    assert _resolve_record_id({"id": 0}) == "0"
    assert _resolve_record_id({"id": ""}) == ""
    assert _resolve_record_id({"_record_id": ""}) == ""


def test_deterministic_record_id_handles_non_json_native() -> None:
    record = {"when": date(2026, 1, 1), "tags": {1, 2}, "amt": Decimal("1.5")}
    rid = _deterministic_record_id(record)
    assert isinstance(rid, str)
    assert len(rid) == 64
    assert rid == _deterministic_record_id(record)


# --- 049-S1 / 055 ---
def test_potency_thresholds_cannot_exceed_pchembl_max() -> None:
    with pytest.raises(ValueError, match="potency_threshold"):
        NormalizationConfig(potency_threshold=15.0)
    with pytest.raises(ValueError, match="high_potency_threshold"):
        NormalizationConfig(high_potency_threshold=15.0)


def test_typical_range_must_lie_within_absolute_bounds() -> None:
    with pytest.raises(ValueError, match="typical_min and typical_max"):
        PChemblRangeConfig(min_value=0.0, max_value=10.0, typical_min=-1.0, typical_max=9.0)
    with pytest.raises(ValueError, match="typical_min and typical_max"):
        PChemblRangeConfig(min_value=0.0, max_value=10.0, typical_min=1.0, typical_max=11.0)


# --- 054 / 057 ---
def test_build_field_type_change_tolerates_non_mapping_properties() -> None:
    assert build_field_type_change("f", True, False) is None  # type: ignore[arg-type]
    change = build_field_type_change(
        "f",
        {"type": "string"},
        {"type": "integer"},
    )
    assert change is not None
    assert change.change_type is SchemaChangeType.FIELD_TYPE_CHANGED


def test_added_removed_field_changes_are_sorted() -> None:
    old = {"z": {}, "a": {}}
    new = {"m": {}, "b": {}}
    removed = removed_field_changes(old, new)
    added = added_field_changes(old, new)
    assert [c.field_path for c in removed] == [
        "properties.a",
        "properties.z",
    ]
    assert [c.field_path for c in added] == [
        "properties.b",
        "properties.m",
    ]


# --- 056 ---
def test_classification_stats_rejects_conflict_above_total() -> None:
    with pytest.raises(ValueError, match="conflict_count"):
        ClassificationStats(
            total=2,
            acellular=1,
            unicellular=1,
            multicellular=0,
            unresolved=0,
            conflict_count=3,
        )


# --- 059 ---
def test_classify_from_registry_diff_non_object_payloads() -> None:
    classifier = SchemaClassifier()
    result = classifier.classify_from_registry_diff("[]", "{}")
    assert result.requires_manual_review is True


# --- 062 ---
def test_normalize_text_handles_unicode_punctuation() -> None:
    assert normalize_text("O’Brien") == normalize_text("O'Brien")
    assert normalize_text("well—known") == normalize_text("well-known")
    assert jaccard_similarity("well—known drug", "well-known drug") == pytest.approx(
        1.0
    )


# --- 067-S1 ---
def test_newly_added_required_field_can_be_breaking() -> None:
    classifier = SchemaClassifier(
        policy=SchemaCompatibilityPolicy(required_field_additions_as_breaking=True)
    )
    old = {"properties": {"id": {"type": "string"}}, "required": ["id"]}
    new = {
        "properties": {
            "id": {"type": "string"},
            "new_req": {"type": "string"},
        },
        "required": ["id", "new_req"],
    }
    result = classifier.classify_changes(old, new)
    assert result.classification is ChangeClassification.MAJOR
    assert any(
        c.change_type is SchemaChangeType.REQUIRED_FIELD_ADDED
        for c in result.breaking_changes
    )
