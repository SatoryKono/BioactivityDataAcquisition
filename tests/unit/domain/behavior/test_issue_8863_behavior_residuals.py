"""Regression tests for confirmed behavior residuals in issue #8863."""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from bioetl.domain.behavior._author_helpers import _collect_affiliation_values
from bioetl.domain.behavior._dq_serializer_html._styles import _REPORT_STYLES
from bioetl.domain.behavior.aggregation_validation_helpers import (
    column_names as _column_names,
)
from bioetl.domain.behavior.aggregation_validation_helpers import (
    explicit_field_names as _explicit_field_names,
)
from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.composite_validation_helpers import (
    _optional_unit_interval,
)
from bioetl.domain.behavior.composite_validation_layer import CompositeValidator
from bioetl.domain.behavior.cross_validation_helpers import _collect_covered_sources
from bioetl.domain.behavior.cross_validation_validator import (
    CrossValidationConfig,
    CrossValidationDispositionPolicy,
    CrossValidationValidator,
    _build_disposed_issue,
)
from bioetl.domain.behavior.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)
from bioetl.domain.behavior.merged_metadata_explainability import (
    MergedFieldExplanation,
    MergedMetadataExplainer,
    MergedRecordExplanation,
    _deterministic_record_id,
    _resolve_record_id,
)
from bioetl.domain.behavior.normalization_config import (
    ConcentrationRangeConfig,
    NormalizationConfig,
)
from bioetl.domain.behavior.normalization_service import BioactivityNormalizer
from bioetl.domain.behavior.preflight_governance import PreflightGovernor
from bioetl.domain.behavior.schema_classifier import SchemaClassifier
from bioetl.domain.behavior.schema_classifier_helpers import changed_field_changes
from bioetl.domain.behavior.value_validator import ValueValidator
from bioetl.domain.types.validation_result import ValidationIssue
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)

pytestmark = pytest.mark.unit


def test_configured_molar_window_applies_to_pm_and_fm() -> None:
    validator = ValueValidator(
        config=NormalizationConfig(
            concentration_range=ConcentrationRangeConfig(
                min_molar=1e-9,
                max_molar=1e-6,
            )
        )
    )

    assert validator.validate_concentration(1_001.0, "pM") == (True, None)
    assert validator.validate_concentration(1_000_001.0, "fM") == (True, None)
    assert validator.validate_concentration(999.0, "pM")[0] is False
    assert validator.validate_concentration(999_999.0, "fM")[0] is False


def test_warning_badge_css_matches_rendered_class() -> None:
    assert ".status-warn {" in _REPORT_STYLES
    assert ".status-warning {" not in _REPORT_STYLES


def test_author_affiliation_collection_extracts_dictionary_names() -> None:
    assert _collect_affiliation_values(
        [{"name": "MIT"}, {"display_name": "Harvard"}, " Stanford ", 7]
    ) == ["MIT", "Harvard", "Stanford"]


def test_required_scalar_string_is_not_split_into_field_names() -> None:
    breaking, non_breaking = changed_field_changes(
        old_schema={"required": []},
        new_schema={"required": "ab"},
        old_properties={"a": {}, "b": {}},
        new_properties={"a": {}, "b": {}},
        required_field_additions_as_breaking=True,
    )

    assert breaking == []
    assert non_breaking == []


@pytest.mark.parametrize(
    "config",
    [
        NormalizationConfig(),
        NormalizationConfig.for_screening(),
        NormalizationConfig.for_medicinal_chemistry(),
    ],
)
def test_potency_presets_keep_all_five_labels_reachable(
    config: NormalizationConfig,
) -> None:
    normalizer = BioactivityNormalizer(config=config)
    span = config.high_potency_threshold - config.potency_threshold
    inactive_boundary = config.potency_threshold - span / 2
    potent_boundary = config.potency_threshold + span / 2
    values = (
        inactive_boundary - 0.1,
        (inactive_boundary + config.potency_threshold) / 2,
        (config.potency_threshold + potent_boundary) / 2,
        (potent_boundary + config.high_potency_threshold) / 2,
        config.high_potency_threshold,
    )

    assert [normalizer.classify_potency(value) for value in values] == [
        "inactive",
        "weak",
        "moderate",
        "potent",
        "highly_potent",
    ]


@pytest.mark.parametrize("properties", [["bad"], "bad"])
def test_schema_classifier_manual_reviews_malformed_properties(
    properties: object,
) -> None:
    result = SchemaClassifier().classify_from_registry_diff(
        '{"properties": {}}',
        __import__("json").dumps({"properties": properties}),
    )

    assert result.requires_manual_review is True
    assert result.unknown_changes


def _field_explanation() -> MergedFieldExplanation:
    return MergedFieldExplanation(
        field_name="activity",
        source_providers=["chembl"],
        merge_strategy="prioritize",
        priority_order=["chembl"],
        enrichment_applied=["uniprot", "pubmed"],
    )


def test_explanation_value_objects_freeze_nested_collections() -> None:
    providers = ["chembl"]
    fields = [_field_explanation()]
    record = MergedRecordExplanation(
        record_id="r1",
        composite_run_id="run1",
        source_providers=providers,
        field_explanations=fields,
        merge_strategy="prioritize",
    )
    providers.append("pubmed")
    fields.clear()

    assert record.source_providers == ("chembl",)
    assert len(record.field_explanations) == 1
    assert record.field_explanations[0].priority_order == ("chembl",)
    with pytest.raises(FrozenInstanceError):
        record.record_id = "changed"  # type: ignore[misc]


def test_enrichment_rate_counts_enriched_records_not_total_enrichments() -> None:
    explanations = [
        MergedRecordExplanation(
            record_id="r1",
            composite_run_id="run1",
            source_providers=(),
            field_explanations=(),
            merge_strategy="prioritize",
            enrichment_count=2,
        ),
        MergedRecordExplanation(
            record_id="r2",
            composite_run_id="run1",
            source_providers=(),
            field_explanations=(),
            merge_strategy="prioritize",
            enrichment_count=0,
        ),
    ]

    summary = MergedMetadataExplainer().generate_explainability_summary(explanations)

    assert summary["enrichment_summary"]["total_enrichments"] == 2
    assert summary["enrichment_summary"]["enrichment_rate"] == pytest.approx(0.5)


def test_self_comparison_is_blocking_and_does_not_count_as_coverage() -> None:
    validator = CrossValidationValidator()
    result = validator.validate_cross_validation_config(
        CrossValidationConfig(pairs=[{"chembl": ["chembl"]}], rules={"id": "strict"}),
        ["chembl"],
    )

    assert any(issue.code is IssueCode.CMP_PF_CV_007 for issue in result.issues)
    assert _collect_covered_sources([{"chembl": ["chembl"]}]) == set()


def test_disposed_issue_rewrite_is_idempotent() -> None:
    issue = ValidationIssue(
        code=IssueCode.CMP_PF_CV_002,
        severity=ValidationSeverity.BLOCKER,
        layer=ValidationLayer.DEEP_PREFLIGHT,
        message="bad pairs",
        details={},
    )
    disposed = _build_disposed_issue(
        issue=issue,
        severity=ValidationSeverity.WARNING,
        suffix="downgraded",
        extra_details={"disposition": "downgraded", "original_severity": "blocker"},
    )
    repeated = _build_disposed_issue(
        issue=disposed,
        severity=ValidationSeverity.BLOCKER,
        suffix="will fail execution",
        extra_details={"disposition": "fail", "execution_blocked": True},
    )

    assert repeated is disposed
    assert repeated.message.count("downgraded") == 1
    assert repeated.details["original_severity"] == "blocker"


def _composite_validator() -> CompositeValidator:
    return CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )


def test_explicit_null_cross_validation_is_absent_optional_config() -> None:
    issues = _composite_validator()._deep_preflight_issues(
        {
            "sources": ["chembl", "pubmed"],
            "merge_strategy": "left_outer",
            "output_schema": {},
            "cross_validation": None,
        }
    )

    assert issues == []


def test_group_keys_canonicalize_mapping_order_and_reject_unsupported_values() -> None:
    first = AggregationValidator._build_group_key(
        {"group": {"b": 2, "a": [1, 2]}}, ["group"]
    )
    second = AggregationValidator._build_group_key(
        {"group": {"a": [1, 2], "b": 2}}, ["group"]
    )

    assert first == second
    with pytest.raises(TypeError, match="JSON-serializable"):
        AggregationValidator._build_group_key({"group": object()}, ["group"])


def test_empty_existing_schema_reports_all_incoming_fields_as_drift() -> None:
    metrics = DQMetricsCalculator().calculate(
        DQMetricsInput(records=[{"entity_id": "1"}], existing_schema_fields=set())
    )

    assert metrics.schema_drift is not None
    assert metrics.schema_drift.new_fields == ("entity_id",)


def test_null_identifier_falls_back_while_falsy_identifiers_remain_valid() -> None:
    record = {"id": None, "value": 1}

    assert _resolve_record_id(record) == _deterministic_record_id(record)
    assert _resolve_record_id({"id": 0}) == "0"
    assert _resolve_record_id({"id": ""}) == ""


def test_deterministic_record_id_rejects_unsupported_values_without_repr() -> None:
    assert _deterministic_record_id(
        {"when": date(2026, 8, 16), "tags": {"b", "a"}}
    ) == _deterministic_record_id({"tags": {"a", "b"}, "when": date(2026, 8, 16)})
    with pytest.raises(TypeError, match="Unsupported value"):
        _deterministic_record_id({"bad": object()})


@pytest.mark.parametrize(
    ("value", "error_type"),
    [
        (True, TypeError),
        (False, TypeError),
        (math.nan, ValueError),
        (math.inf, ValueError),
    ],
)
def test_optional_unit_interval_rejects_bool_and_non_finite(
    value: object,
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type):
        _optional_unit_interval(value, "coverage_threshold")


def test_fallback_schema_names_do_not_coerce_arbitrary_values() -> None:
    assert _column_names(["title", {"name": "doi"}, 42, None]) == {
        "title",
        "doi",
    }
    assert _explicit_field_names(["title", 42, None]) == {"title"}


def test_disposition_policy_enum_remains_covered() -> None:
    assert CrossValidationDispositionPolicy.FAIL.value == "fail"
