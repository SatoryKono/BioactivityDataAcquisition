"""Behavior coverage for the remaining two-line domain residuals in #10469."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.domain.behavior._preflight_governance_helpers import (
    apply_issue_override,
    apply_overrides_to_issues,
)
from bioetl.domain.behavior.activity_aggregator._aggregator import ActivityAggregator
from bioetl.domain.behavior.composite_validation_helpers import (
    _append_named_config_issue_if_invalid,
)
from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.behavior.preflight_governance import PreflightGovernor
from bioetl.domain.behavior.schema_classifier import SchemaClassifier
from bioetl.domain.composite.config import CompositeDQConfig, DQOverrideConfig
from bioetl.domain.composite.result_composite import CompositeResult
from bioetl.domain.context_validation import (
    _validate_dq_contract_alignment,
    _validate_manifest_contract_alignment,
)
from bioetl.domain.control_plane._reproducibility_policy_support import (
    _source_ref_family_label,
    _source_ref_label,
)
from bioetl.domain.control_plane.workflow_manifest import (
    _load_list,
    _load_object_mapping,
)
from bioetl.domain.run_reports.models import ReasonRemoval, _copy_reason_items
from bioetl.domain.types.dq_contracts import DQDisposition, DQViolationKind
from bioetl.domain.types.schema_policy import (
    ChangeClassification,
    SchemaChangeClassification,
    SchemaCompatibilityPolicy,
)
from bioetl.domain.value_objects.dq_report_results_core import (
    _as_tuple,
    _freeze_type_change,
)
from bioetl.domain.workflow.foreign_key_reconciliation import (
    ForeignKeyReconciliationRequest,
)


pytestmark = pytest.mark.unit


def test_contract_alignment_shortcuts_and_missing_reference() -> None:
    identity = SimpleNamespace(contract_ref="", dq_policy_ref="dq-v1")

    assert _validate_dq_contract_alignment(identity, None) == []
    assert _validate_manifest_contract_alignment(identity, None) == []
    assert _validate_manifest_contract_alignment(identity, "manifest-1") == [
        "Contract identity missing contract reference"
    ]


def test_preflight_override_helpers_preserve_unconfigured_issues() -> None:
    issues = [object()]

    assert (
        apply_overrides_to_issues(issues, SimpleNamespace(issue_code_overrides=None))
        is issues
    )
    assert apply_issue_override(issues[0], None) is issues[0]


def test_named_composite_validator_accepts_valid_mapping() -> None:
    issues: list[object] = []

    _append_named_config_issue_if_invalid(
        issues=issues,
        composite_config={"section": {"enabled": True}},
        config_key="section",
        validator=lambda value: value == {"enabled": True},
        code=SimpleNamespace(),
        severity=SimpleNamespace(),
        message="invalid",
        details_key="section",
    )

    assert issues == []


def test_dq_policy_none_overrides_and_strict_contract_escalation() -> None:
    resolver = object.__new__(DQPolicyResolver)
    resolver.config = SimpleNamespace(
        disposition_overrides=None,
        strictness_mode="strict",
    )

    assert resolver._get_disposition_overrides_dict() == {}
    assert (
        resolver._apply_contract_adjustments(
            DQDisposition.WARN, DQViolationKind.BUSINESS_RULE_VIOLATION
        )
        is DQDisposition.QUARANTINE
    )


def test_preflight_governor_uses_first_available_timestamp() -> None:
    report = SimpleNamespace(
        runtime_guard_result=SimpleNamespace(timestamp="2026-09-17T00:00:00Z"),
        deep_preflight_result=SimpleNamespace(timestamp="older"),
        structural_result=None,
    )

    assert (
        PreflightGovernor._resolve_execution_timestamp(report) == "2026-09-17T00:00:00Z"
    )


def test_schema_classifier_handles_policy_fallback_and_nested_explanation() -> None:
    classifier = SchemaClassifier(
        SchemaCompatibilityPolicy(
            default_classification_for_unknown=ChangeClassification.UNKNOWN
        )
    )
    inconsistent_diff = SimpleNamespace(
        breaking_changes=[],
        non_breaking_changes=[],
        unknown_changes=[],
        has_breaking_changes=lambda: False,
        has_changes=lambda: True,
    )

    fallback = classifier._apply_policy_rules(inconsistent_diff)
    assert fallback.classification is ChangeClassification.UNKNOWN
    explanation = classifier._generate_explanation(inconsistent_diff, fallback)
    nested = SchemaChangeClassification(
        classification=ChangeClassification.UNKNOWN,
        explanation=explanation,
        requires_manual_review=True,
        breaking_changes=[],
        non_breaking_changes=[],
        unknown_changes=[],
    )
    assert classifier._generate_explanation(
        inconsistent_diff, nested
    ).summary.startswith(explanation.summary)


def test_activity_aggregator_rejects_unknown_enum_and_handles_nonpositive_logs() -> (
    None
):
    aggregator = ActivityAggregator()

    with pytest.raises(ValueError, match="Unsupported aggregation method"):
        aggregator._apply_aggregation([1.0], object())  # type: ignore[arg-type]
    assert aggregator._geometric_uncertainty([0.0, -1.0], 1.0) == 0.0


def test_composite_dq_uses_defaults_for_empty_overrides() -> None:
    config = CompositeDQConfig(
        soft_fail_threshold=0.2,
        hard_fail_threshold=0.8,
        enricher_overrides={"optional": DQOverrideConfig()},
    )

    assert config.get_enricher_soft_threshold("optional") == 0.2
    assert config.get_enricher_hard_threshold("optional") == 0.8


def test_composite_result_freezes_required_name_collections() -> None:
    result = CompositeResult(
        composite_name="publication",
        composite_run_id="run-1",
        seed_result=SimpleNamespace(is_success=True),
        _required_enrichers=["crossref"],  # type: ignore[arg-type]
        _required_dependencies=["pubmed"],  # type: ignore[arg-type]
    )

    assert result._required_enrichers == frozenset({"crossref"})
    assert result._required_dependencies == frozenset({"pubmed"})


def test_source_ref_labels_fall_back_to_pipeline_and_reject_empty_family() -> None:
    ref = SimpleNamespace(provider=" ", entity="", pipeline_name=" chembl_activity ")

    assert _source_ref_family_label(ref) is None
    assert _source_ref_label(ref) == "chembl_activity"


def test_workflow_manifest_loaders_reject_wrong_container_shapes() -> None:
    assert _load_object_mapping(("not", "a", "mapping")) == {}
    assert _load_list(("not", "a", "list")) == []


def test_run_report_reason_serialization_keeps_optional_details() -> None:
    payload: dict[str, object] = {}
    _copy_reason_items(payload, "reasons", ({"code": "filtered"},))
    reason = ReasonRemoval(
        outcome="filtered_out",
        reason_code="invalid_id",
        count=1,
        reason_family="validation",
        sample_refs=("row-1",),
    )

    assert payload == {"reasons": [{"code": "filtered"}]}
    assert reason.to_dict()["sample_refs"] == ["row-1"]


def test_dq_result_freezing_handles_generic_iterable_and_scalar() -> None:
    assert set(_as_tuple({"a", "b"})) == {"a", "b"}
    marker = object()
    assert _freeze_type_change(marker) is marker


def test_foreign_key_request_rejects_invalid_completeness_contracts() -> None:
    common = {
        "source_table": "silver/source",
        "reference_table": "silver/reference",
        "source_key": "target_id",
        "reference_key": "target_id",
        "primary_keys": ("record_id",),
    }

    with pytest.raises(ValueError, match="reference_completeness must be"):
        ForeignKeyReconciliationRequest(
            **common,
            reference_completeness="partial",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="requires reference_identity"):
        ForeignKeyReconciliationRequest(
            **common,
            reference_completeness="complete",
        )
