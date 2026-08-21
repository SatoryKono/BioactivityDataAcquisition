"""Regression matrix for the remaining CodeRabbit findings in issue #8863."""

from __future__ import annotations

import math

import pandera.pandas as pa
import pytest

from bioetl.domain.behavior._author_helpers import collect_affiliations_from_authors
from bioetl.domain.behavior._dq_serializer_html._styles import _REPORT_STYLES
from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.composite_validation_helpers import (
    _optional_unit_interval,
)
from bioetl.domain.behavior.composite_validation_layer import (
    CompositeValidator,
)
from bioetl.domain.behavior.cross_validation_helpers import (
    _collect_covered_sources,
    _validate_pairs,
)
from bioetl.domain.behavior.cross_validation_validator import (
    CrossValidationConfig,
    CrossValidationDispositionPolicy,
    CrossValidationValidator,
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
from bioetl.domain.behavior.schema_classifier import create_schema_classifier
from bioetl.domain.behavior.value_validator import ValueValidator
from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
)
from bioetl.domain.composite.aggregation_filters import (
    _validate_aggregation_filter_condition,
)
from bioetl.domain.composite.result_merge import MergeResult
from bioetl.domain.config.table import IdempotencyContract, TableConfig
from bioetl.domain.contracts.gold._chembl_target_lookup_schemas import (
    ChEMBLSubcellularFractionGoldSchema,
)
from bioetl.domain.contracts.gold.composite_bioassay import (
    CompositeTargetGoldSchema,
)
from bioetl.domain.contracts.gold.publications_pubmed import (
    PubMedPublicationGoldSchema,
)
from bioetl.domain.types.schema_policy import ChangeClassification
from bioetl.domain.types.validation_severity import IssueCode
from tests.contract.schemas._schema_row_helpers import minimal_schema_dataframe

pytestmark = pytest.mark.unit


def _composite_validator() -> CompositeValidator:
    return CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )


def test_configured_molar_window_covers_pm_and_fm() -> None:
    validator = ValueValidator(
        config=NormalizationConfig(
            concentration_range=ConcentrationRangeConfig(
                min_molar=1e-12,
                max_molar=1e-6,
            )
        )
    )

    assert validator.validate_concentration(1.0, "pM") == (True, None)
    assert validator.validate_concentration(0.5, "pM")[0] is False
    assert validator.validate_concentration(1000.0, "fM") == (True, None)
    assert validator.validate_concentration(999.0, "fM")[0] is False


def test_warning_badge_css_matches_rendered_status_class() -> None:
    assert ".status-warn {" in _REPORT_STYLES
    assert ".status-warning {" not in _REPORT_STYLES


def test_author_affiliation_dicts_use_known_name_fields() -> None:
    assert collect_affiliations_from_authors(
        [{"affiliations": [{"name": "MIT"}, {"display_name": "Harvard"}]}]
    ) == ["MIT", "Harvard"]


def test_scalar_required_value_is_not_split_into_field_names() -> None:
    classifier = create_schema_classifier()
    old_schema = {"properties": {"n": {"type": "string"}}, "required": []}
    new_schema = {"properties": {"n": {"type": "string"}}, "required": "name"}

    result = classifier.classify_changes(old_schema, new_schema)

    assert result.classification == ChangeClassification.PATCH


@pytest.mark.parametrize(
    "config",
    [
        NormalizationConfig(),
        NormalizationConfig.for_screening(),
        NormalizationConfig.for_medicinal_chemistry(),
    ],
)
def test_all_potency_labels_are_reachable_for_presets(
    config: NormalizationConfig,
) -> None:
    normalizer = BioactivityNormalizer(config=config)
    potency = config.potency_threshold
    high = config.high_potency_threshold
    inactive = potency - (high - potency) / 2.0
    midpoint = (potency + high) / 2.0

    labels = {
        normalizer.classify_potency(inactive - 0.5),
        normalizer.classify_potency(potency - 0.5),
        normalizer.classify_potency((potency + midpoint) / 2.0),
        normalizer.classify_potency((midpoint + high) / 2.0),
        normalizer.classify_potency(high),
    }

    assert labels == {"inactive", "weak", "moderate", "potent", "highly_potent"}


@pytest.mark.parametrize("malformed", [["id"], "id"])
def test_malformed_schema_properties_require_manual_review(malformed: object) -> None:
    result = create_schema_classifier().classify_changes(
        {"properties": malformed},
        {"properties": {"id": {"type": "string"}}},
    )

    assert result.classification == ChangeClassification.MANUAL_REVIEW
    assert result.requires_manual_review is True


def test_enrichment_rate_is_record_rate_not_enricher_count_rate() -> None:
    explanations = [
        MergedRecordExplanation("a", "run", (), (), "priority", enrichment_count=2),
        MergedRecordExplanation("b", "run", (), (), "priority", enrichment_count=0),
    ]

    summary = MergedMetadataExplainer().generate_explainability_summary(explanations)

    assert summary["enrichment_summary"] == {
        "total_enrichments": 2,
        "enrichment_rate": 0.5,
        "records_with_enrichments": 1,
    }


def test_frozen_explanations_copy_caller_lists_to_tuples() -> None:
    providers = ["chembl"]
    fields = [MergedFieldExplanation("id", providers, "priority")]

    explanation = MergedRecordExplanation(
        "record",
        "run",
        providers,  # type: ignore[arg-type]
        fields,  # type: ignore[arg-type]
        "priority",
    )
    providers.append("pubmed")
    fields.clear()

    assert explanation.source_providers == ("chembl",)
    assert len(explanation.field_explanations) == 1


def test_self_only_cross_validation_pair_is_invalid_and_uncovered() -> None:
    issues = _validate_pairs([{"chembl": ["chembl"]}], ["chembl"])

    assert [issue.code for issue in issues] == [IssueCode.CMP_PF_CV_007]
    assert _collect_covered_sources([{"chembl": ["chembl"]}]) == set()


def test_quarantine_disposition_is_idempotent() -> None:
    validator = CrossValidationValidator()
    config = CrossValidationConfig(
        pairs=[],
        rules={},
        disposition_policy=CrossValidationDispositionPolicy.QUARANTINE,
    )
    initial = validator.validate_cross_validation_config(config, ["chembl"])

    once = validator.apply_disposition(initial, config)
    twice = validator.apply_disposition(once, config)

    assert twice.issues == once.issues
    assert all(issue.message.count("(quarantined)") == 1 for issue in twice.issues)


def test_composite_config__explicit_null_cross_validation_is_absent() -> None:
    issues = _composite_validator()._deep_preflight_issues(
        {
            "sources": ["chembl"],
            "merge_strategy": "prioritize",
            "output_schema": {"properties": {"id": {}}},
            "cross_validation": None,
        }
    )

    assert issues == []


def test_structured_group_keys_are_canonical_across_mapping_order() -> None:
    result = AggregationValidator().validate_post_aggregation_uniqueness(
        [{"group": {"a": 1, "b": 2}}, {"group": {"b": 2, "a": 1}}],
        ["group"],
    )

    assert result.has_blockers()


def test_dq_metrics__empty_existing_schema_reports_all_incoming_fields() -> None:
    metrics = DQMetricsCalculator().calculate(
        DQMetricsInput(records=[{"id": 1}], existing_schema_fields=set())
    )

    assert metrics.schema_drift is not None
    assert metrics.schema_drift.new_fields == ("id",)


def test_null_identifier_falls_back_to_deterministic_record_identity() -> None:
    record = {"id": None, "name": "aspirin"}

    assert _resolve_record_id(record) == _deterministic_record_id(record)
    assert _resolve_record_id(record) != "None"


def test_record_identity_rejects_unsupported_values_and_sorts_sets() -> None:
    assert _deterministic_record_id({"tags": {"a", "b"}}) == (
        _deterministic_record_id({"tags": {"b", "a"}})
    )
    assert _deterministic_record_id({1: "one", "2": "two"}) == (
        _deterministic_record_id({"2": "two", 1: "one"})
    )
    with pytest.raises(TypeError, match="Unsupported value"):
        _deterministic_record_id({"unsupported": object()})


@pytest.mark.parametrize("value", [True, False, math.nan, math.inf])
def test_optional_unit_interval__rejects_bool_and_non_finite(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        _optional_unit_interval(value, "threshold")


def test_invalid_fallback_schema_descriptors_do_not_become_field_names() -> None:
    fields = AggregationValidator()._get_source_fields(
        {"columns": [1, {"name": "valid"}], "field_names": [None, "explicit"]}
    )

    assert fields == {"valid", "explicit"}


def test_quoted_literal_cannot_hide_nested_comparison() -> None:
    with pytest.raises(ValueError, match="additional operators"):
        _validate_aggregation_filter_condition("status == 'foo' == 'bar'")
    _validate_aggregation_filter_condition("status == 'foo'")


def test_aggregation_null_filter__rejects_trailing_text() -> None:
    with pytest.raises(ValueError, match="trailing text"):
        _validate_aggregation_filter_condition("field IS NULL OR other == 1")
    _validate_aggregation_filter_condition("field IS NOT NULL")


def test_aggregation_output_field_is_non_empty_and_normalized() -> None:
    with pytest.raises(ValueError, match="output_field"):
        AggregationFieldSpec("value", AggregationFunction.FIRST, output_field="   ")
    spec = AggregationFieldSpec(
        "value",
        AggregationFunction.FIRST,
        output_field=" normalized ",
    )
    assert spec.effective_output_field == "normalized"


def test_aggregation_rejects_duplicate_effective_output_fields() -> None:
    with pytest.raises(ValueError, match="duplicate output field"):
        AggregationConfig(
            group_by="id",
            fields=(
                AggregationFieldSpec("title", AggregationFunction.FIRST),
                AggregationFieldSpec(
                    "name",
                    AggregationFunction.FIRST,
                    output_field="title",
                ),
            ),
        )


def test_enriched_records_cannot_exceed_zero_merged_records() -> None:
    with pytest.raises(ValueError, match="cannot exceed records_merged"):
        MergeResult(records_merged=0, records_enriched=1)


def test_table_config__partition_append_requires_partition_columns() -> None:
    with pytest.raises(ValueError, match="partition_cols"):
        TableConfig(
            silver_idempotency_contract=(
                IdempotencyContract.PARTITION_APPEND_WITH_STABLE_PARTITION_KEY
            )
        )


def _subcellular_fraction_frame():
    frame = minimal_schema_dataframe(ChEMBLSubcellularFractionGoldSchema)
    frame.loc[0, "entity_id"] = "0123456789abcdef"
    frame.loc[0, "content_hash"] = "a" * 64
    frame.loc[0, "subcellular_fraction"] = "Microsomes"
    return frame


def test_subcellular_fraction_contract_enforces_identifier_formats() -> None:
    valid = _subcellular_fraction_frame()
    valid.loc[0, "example_assay_id"] = "CHEMBL12345"
    ChEMBLSubcellularFractionGoldSchema.validate(valid)

    invalid_entity = valid.copy()
    invalid_entity.loc[0, "entity_id"] = "not-a-sha-prefix"
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        ChEMBLSubcellularFractionGoldSchema.validate(invalid_entity)

    invalid_assay = valid.copy()
    invalid_assay.loc[0, "example_assay_id"] = "ASSAY123"
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        ChEMBLSubcellularFractionGoldSchema.validate(invalid_assay)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [("pub_month", 1.5), ("pub_day", 30.5)],
)
def test_pubmed_contract_rejects_fractional_calendar_values(
    field_name: str,
    value: float,
) -> None:
    frame = minimal_schema_dataframe(PubMedPublicationGoldSchema)
    frame.loc[0, field_name] = value

    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        PubMedPublicationGoldSchema.validate(frame)


def test_composite_bioassay_contract_rejects_fractional_count() -> None:
    frame = minimal_schema_dataframe(CompositeTargetGoldSchema)
    frame.loc[0, "top_level_count"] = 2.0
    CompositeTargetGoldSchema.validate(frame)

    frame.loc[0, "top_level_count"] = 1.5
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        CompositeTargetGoldSchema.validate(frame)
