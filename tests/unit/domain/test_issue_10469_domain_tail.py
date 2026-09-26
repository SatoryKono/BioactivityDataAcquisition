"""Focused domain tests for one-line coverage residuals in issue #10469."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from bioetl.domain.aggregates.pipeline_run import (
    PipelineRun,
    PipelineRunState,
    StageResult,
    StageStatus,
)
import bioetl.domain.behavior as behavior_facade
import bioetl.domain.config as config_facade
import bioetl.domain.exceptions as exceptions_facade
import bioetl.domain.filtering as filtering_facade
import bioetl.domain.mapping.publication_controlled_vocabulary as publication_vocabulary
import bioetl.domain.normalization.profiles as profiles_facade
import bioetl.domain.registry.publication_data as publication_data
from bioetl.domain.behavior._dq_serializer_yaml import format_yaml_scalar
from bioetl.domain.behavior.validation_result_envelopes import (
    _require_composite_validation_report,
)
from bioetl.domain.behavior.composite_validation_shapes import (
    precheck_cross_validation_config,
)
from bioetl.domain.behavior.composite_metadata_cv import summarize_composite_cv_dq
from bioetl.domain.behavior.cross_validation_validator import _collect_blocker_issues
from bioetl.domain.behavior.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.behavior.normalization_config import (
    NormalizationConfig,
    PChemblRangeConfig,
)
from bioetl.domain.behavior.organism_classification_service_models import (
    ClassificationStats,
)
from bioetl.domain.behavior.staged_enforcement import (
    EnforcementPolicy,
    EnforcementStage,
    StagedEnforcementEngine,
)
from bioetl.domain.composite.field_groups_models import FieldMapping
from bioetl.domain.composite.config_cross_validation import _require_finite_number
from bioetl.domain.composite.lineage import _status_error_message
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.table import _normalize_idempotency_contract
from bioetl.domain.context_run import PipelineRunContext
from bioetl.domain.entities._chembl_reference_models import TargetComponentRecord
from bioetl.domain.entities.bioactivity._extractors import _first_truthy_value
from bioetl.domain.entities.chembl_tissue import Tissue
from bioetl.domain.exceptions.base_exceptions import _plain_context_mapping
from bioetl.domain.filtering.silver_filter_identity import (
    DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE,
    normalize_silver_filter_compatibility_mode,
)
from bioetl.domain.mapping.publication_controlled_vocabulary import (
    PublicationControlledVocabularyRegistry,
    initialize_publication_controlled_vocabulary,
    is_publication_controlled_vocabulary_initialized,
)
from bioetl.domain.models._metadata_common import validate_utc_datetime
from bioetl.domain.normalization.profiles._profile_governed_value_normalizers import (
    normalize_profile_standard_unit_enum,
)
from bioetl.domain.normalization.profiles._profile_target_normalizers import (
    normalize_profile_target_organism_class,
)
from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.registry.publication_data import (
    get_publication_entity_type_validation_error,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.domain.types.gold_contracts_scd import ScdConfig
from bioetl.domain.types.validation_severity import ValidationSeverity
from bioetl.domain.value_objects.academic_ids import ISSN

pytestmark = pytest.mark.unit


class _StringableValue:
    def __str__(self) -> str:
        return "value with space"


@pytest.mark.parametrize(
    "facade",
    [
        behavior_facade,
        config_facade,
        exceptions_facade,
        filtering_facade,
        profiles_facade,
    ],
)
def test_domain_lazy_facade_directory_contains_public_exports(facade: Any) -> None:
    assert set(facade.__all__).issubset(facade.__dir__())


def test_yaml_scalar_falls_back_to_string_representation() -> None:
    assert format_yaml_scalar(_StringableValue()) == '"value with space"'


def test_empty_composite_cv_summary_is_explicitly_signal_free() -> None:
    assert summarize_composite_cv_dq([]) == {
        "has_signal": False,
        "warning_records": 0,
        "error_records": 0,
        "quarantine_records": 0,
        "validation_passed": True,
        "rule_provenance": [],
    }


def test_collect_blocker_issues_filters_other_severities() -> None:
    blocker = SimpleNamespace(severity=ValidationSeverity.BLOCKER)
    warning = SimpleNamespace(severity=ValidationSeverity.WARNING)
    assert _collect_blocker_issues(cast(Any, [warning, blocker])) == [blocker]


def test_dq_metrics_empty_batch_has_no_incoming_fields() -> None:
    assert DQMetricsCalculator._extract_incoming_fields([]) == set()


def test_cross_validation_threshold_rejects_bool() -> None:
    with pytest.raises(ValueError, match="must be a number"):
        _require_finite_number(True, "threshold")


def test_lineage_error_message_stringifies_non_string_value() -> None:
    assert _status_error_message({"error_message": 404}) == "404"


def test_blank_idempotency_contract_normalizes_to_none() -> None:
    assert _normalize_idempotency_contract("  ") is None


def test_missing_silver_filter_mode_uses_compatibility_default() -> None:
    assert (
        normalize_silver_filter_compatibility_mode(None)
        == DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE
    )


def test_publication_vocabulary_reports_registry_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(publication_vocabulary, "_registry", None)
    assert is_publication_controlled_vocabulary_initialized() is False

    initialize_publication_controlled_vocabulary(
        PublicationControlledVocabularyRegistry(allowed_values_by_field={})
    )

    assert is_publication_controlled_vocabulary_initialized() is True


def test_metadata_datetime_rejects_naive_value() -> None:
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        validate_utc_datetime(datetime(2026, 1, 1))


def test_scd_config_rejects_non_positive_type() -> None:
    with pytest.raises(ValueError, match="scd_type must be positive"):
        ScdConfig(scd_type=0)


def test_composite_validation_report_guard_rejects_replacement_type_drift() -> None:
    with pytest.raises(TypeError, match="did not preserve CompositeValidationReport"):
        _require_composite_validation_report(object())


def test_cross_validation_precheck_rejects_non_mapping_config() -> None:
    issues = precheck_cross_validation_config([])

    assert len(issues) == 1
    assert "must be a dictionary" in issues[0].message


def test_normalization_config_rejects_potency_above_configured_maximum() -> None:
    with pytest.raises(ValueError, match="potency_threshold cannot exceed"):
        NormalizationConfig(
            pchembl_range=PChemblRangeConfig(max_value=10.0, typical_max=9.0),
            potency_threshold=11.0,
            high_potency_threshold=11.0,
        )


def test_classification_stats_rejects_negative_counter() -> None:
    with pytest.raises(ValueError, match="conflict_count cannot be negative"):
        ClassificationStats(
            total=0,
            acellular=0,
            unicellular=0,
            multicellular=0,
            unresolved=0,
            conflict_count=-1,
        )


def test_hard_fail_verdict_reports_threshold_crossing() -> None:
    policy = EnforcementPolicy(
        check_name="coverage",
        current_stage=EnforcementStage.HARD_FAIL,
        warning_threshold=0.25,
        failure_threshold=0.5,
    )
    stage, message = StagedEnforcementEngine(
        {"coverage": policy}
    ).get_enforcement_verdict("coverage", failure_count=3, total_count=4)

    assert stage is EnforcementStage.HARD_FAIL
    assert message == "Hard fail threshold exceeded (75.0% >= 50.0%)"


def test_field_mapping_ignores_malformed_provider_column() -> None:
    mapping = FieldMapping(
        base_name="title",
        provider_columns=("malformed", "chembl.publication.title"),
    )

    assert mapping.providers == ("chembl",)


def test_dq_config_rejects_unsupported_disposition_override_container() -> None:
    with pytest.raises(TypeError, match="must be a mapping or sequence"):
        DQConfig(disposition_overrides=cast(Any, object()))


def test_bioactivity_alias_extractor_returns_first_truthy_value() -> None:
    assert (
        _first_truthy_value({"primary": "", "fallback": 7}, "primary", "fallback") == 7
    )


def test_chembl_tissue_text_helper_preserves_non_strings() -> None:
    marker = object()
    assert Tissue._stripped_text(marker) is marker


def test_exception_context_non_mapping_normalizes_to_empty_mapping() -> None:
    assert _plain_context_mapping("not-a-mapping") == {}


def test_unknown_standard_unit_is_rejected_after_normalization() -> None:
    assert (
        normalize_profile_standard_unit_enum(
            "definitely-not-a-unit", allowed_values=frozenset({"nM"})
        )
        is None
    )


def test_boolean_taxonomy_id_is_not_treated_as_integer() -> None:
    assert (
        normalize_profile_target_organism_class(
            None,
            record={"taxonomy_id": True, "organism": None},
        )
        is None
    )


def test_unknown_legacy_publication_alias_has_no_rewrite_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        publication_data,
        "LEGACY_PUBLICATION_ALIASES",
        frozenset({"unknown_legacy_alias"}),
    )

    assert (
        get_publication_entity_type_validation_error(
            "unknown_legacy_alias", provider="chembl"
        )
        is None
    )


def test_checkpoint_without_execution_identity_has_no_fingerprint() -> None:
    assert (
        CheckpointMetadata(
            records_processed=0
        ).checkpoint_execution_identity_fingerprint()
        is None
    )


def test_issn_rejects_checksum_mismatch() -> None:
    with pytest.raises(ValueError, match="Invalid ISSN checksum"):
        ISSN("0378-5954")


def test_value_object_facade_directory_includes_public_exports() -> None:
    import bioetl.domain.value_objects as value_objects

    assert set(value_objects.__all__).issubset(value_objects.__dir__())


def test_pipeline_context_without_contract_identity_has_no_consistency_errors() -> None:
    context = PipelineRunContext(
        pipeline_name="chembl_assay",
        run_id=cast(Any, "run-1"),
        run_type=cast(Any, "incremental"),
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert context.validate_contract_consistency() == []


def test_target_component_detaches_nested_classification_ids() -> None:
    source = [1, 2]
    record = TargetComponentRecord(component_id=7, protein_classification_ids=source)
    source.append(3)

    assert record.protein_classification_ids == (1, 2)


def test_entity_rejects_missing_ingestion_timestamp() -> None:
    with pytest.raises(ValueError, match="ingestion_ts is required"):
        Tissue(
            entity_id=cast(Any, "CHEMBL_TISSUE_1"),
            content_hash=cast(Any, "hash"),
            run_id=cast(Any, "run-1"),
            run_type=cast(Any, "incremental"),
            ingestion_ts=cast(Any, None),
            _index=0,
            tissue_id="CHEMBL_TISSUE_1",
            pref_name="Liver",
        )


def test_empty_standard_unit_normalizes_to_none_before_enum_lookup() -> None:
    assert (
        normalize_profile_standard_unit_enum("", allowed_values=frozenset({"nM"}))
        is None
    )


def test_normalization_profile_reports_both_missing_and_extra_fields() -> None:
    profile = NormalizationProfile(
        profile_name="test-profile",
        field_rules={"extra": FieldRule(field_name="extra")},
    )

    with pytest.raises(ValueError, match=r"missing=\['required'\].*extra=\['extra'\]"):
        profile.assert_covers_schema({"required"})


def test_value_object_allows_assignment_during_manual_initialization() -> None:
    value = object.__new__(ISSN)
    value._initialized = False
    value._value = "0378-5955"

    assert value.value == "0378-5955"


def test_duplicate_failed_stage_is_idempotent_during_rehydration() -> None:
    now = datetime(2026, 9, 16, tzinfo=UTC)
    run = PipelineRun(
        run_id=cast(Any, "run-1"),
        run_type=cast(Any, "incremental"),
        pipeline_name="chembl_assay",
    )
    run.start(now)
    existing = StageResult(
        stage="extract",
        status=StageStatus.FAILED,
        started_at=now,
        completed_at=now,
        error="persisted failure",
    )
    run._stages.append(existing)

    run.record_stage_failure(
        "extract",
        "duplicate failure",
        started_at=now,
        completed_at=now,
    )

    assert run.status is PipelineRunState.RUNNING
    assert run.stages == (existing,)
