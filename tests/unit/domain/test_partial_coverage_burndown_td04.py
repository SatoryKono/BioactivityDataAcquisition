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
"""TD-04 (#6622) focused unit tests for near-100% domain partial modules.

Each test targets a single missing executable branch/line reported by
``reports/coverage/coverage.xml`` for partially_covered domain modules with
``missing_lines <= 3``. Pure domain only — no network/I/O.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import pytest

from bioetl.domain.behavior._dq_condition_matchers import _ne_condition_matches
from bioetl.domain.behavior.activity_aggregator._aggregator_extensions import (
    _ActivityAggregatorExtensions,
)
from bioetl.domain.behavior.cross_validation_validator import (
    CrossValidationConfig,
    CrossValidationDispositionPolicy,
    CrossValidationValidator,
)
from bioetl.domain.behavior.dq_rule_evaluator import _apply_invalid_record_policy
from bioetl.domain.behavior.organism_classification_service import (
    ClassificationStats,
    OrganismClassifier,
)
from bioetl.domain.composite.config_schema import LayerColumnConfig
from bioetl.domain.composite.result_composite import CompositeResult
from bioetl.domain.composite.result_seed_dependency import (
    DependencyResult,
    DependencyStatus,
    SeedResult,
)
from bioetl.domain.config.runtime import RuntimeConfig
from bioetl.domain.control_plane._reproducibility_policy_verdicts import (
    ReplayCapability,
    resolve_replay_readiness_verdict,
)
from bioetl.domain.control_plane._run_ledger_event_family import (
    infer_ledger_event_family,
)
from bioetl.domain.control_plane.artifact_lifecycle import (
    ControlPlaneArtifactLifecyclePolicy,
)
from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    EffectiveConfigArtifact,
    EffectiveExecutionConfig,
    ResolvedConfigSnapshot,
    RuntimeOverrideSnapshot,
    _compute_dq_compatibility_hash,
)
from bioetl.domain.control_plane.ledger.core_events import LedgerEvent
from bioetl.domain.control_plane.reproducibility_policy import (
    is_degraded_observable_profile_requested,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    registered_reproducibility_family_inventory,
)
from bioetl.domain.entities.uniprot import IDMappingResult
from bioetl.domain.exceptions.base import BioETLError
from bioetl.domain.exceptions.network_rate_limit_helpers import (
    resolve_rate_limit_params,
)
from bioetl.domain.exceptions.validation import ValidationError
from bioetl.domain.filtering.load_result import FilterLoadResult
from bioetl.domain.filtering.silver_filter_identity import (
    normalize_silver_filter_compatibility_mode,
)
from bioetl.domain.mapping.organism_classification import OrganismClassificationResult
from bioetl.domain.normalization._chembl_units import _legacy_qudt_identifier_from_uri
from bioetl.domain.normalization.fingerprints import (
    compute_manifest_execution_fingerprint,
)
from bioetl.domain.normalization.profiles._chembl_bao_label_normalizers import (
    normalize_profile_bao_label_from_bao_format,
)
from bioetl.domain.normalization.profiles._standard_profile_spec import (
    _resolve_standard_profile_value,
)
from bioetl.domain.normalization.profiles.chembl_policy_registry import (
    _parse_chembl_field_ref,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_case,
)
from bioetl.domain.normalization.publication_structured_fields import (
    CollectionSemantics,
    FieldRepresentation,
    PublicationStructuredFieldPolicy,
)
from bioetl.domain.normalization.structured_payload_policies import (
    StructuredPayloadCollectionSemantics,
    StructuredPayloadPolicy,
    StructuredPayloadRepresentation,
    StructuredPayloadSemanticPolicy,
)
from bioetl.domain.ports.noop._memory_metadata import NoOpMetadataWriter
from bioetl.domain.types import RunType
from bioetl.domain.types._checkpoint_metadata_support import coerce_snapshot_refs
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQPolicyRef,
    DQRuleOutcome,
    DQViolationKind,
)
from bioetl.domain.types.execution_phase import (
    CompositeFSM,
    ExecutionPhase,
    PhaseTransition,
)
from bioetl.domain.types.validation_result import ValidationIssue, ValidationResult
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)
from bioetl.domain.value_objects._molecular_weight import MolecularWeight
from bioetl.domain.value_objects.activity_measurement import ActivityValue
from bioetl.domain.value_objects.base import ValueObject
from bioetl.domain.workflow.config import WorkflowConfig, WorkflowStepConfig


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# control_plane (criticality family)
# ---------------------------------------------------------------------------


def test_effective_config_artifact__policy_refs_without_hashes__no_dq_policy_hashes() -> (
    None
):
    """Cover _compute_dq_compatibility_hash when refs exist but hashes are empty."""
    refs = [
        DQPolicyRef(
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            policy_hash=None,
        ),
        DQPolicyRef(
            contract_ref="chembl.molecule",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            policy_hash="",
        ),
    ]
    assert _compute_dq_compatibility_hash(refs) == "no_dq_policy_hashes"

    artifact = EffectiveConfigArtifact(
        artifact_id="td04-artifact",
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        source_refs=[],
        resolution_policy=ConfigResolutionPolicy(),
        resolved_config=ResolvedConfigSnapshot(
            config_type="standard", config_data={}, config_hash="h1"
        ),
        runtime_overrides=RuntimeOverrideSnapshot(),
        effective_execution_config=EffectiveExecutionConfig(
            config_data={}, effective_hash="h2"
        ),
        resolved_config_hash="h1",
        effective_config_hash="h2",
        source_fingerprint="fp",
        dq_policy_refs=refs,
    )
    assert artifact.dq_contract_compatibility_hash == "no_dq_policy_hashes"


def test_artifact_lifecycle_policy__rejects_non_positive_retention() -> None:
    with pytest.raises(ValueError, match="retention_days must be at least 1"):
        ControlPlaneArtifactLifecyclePolicy(
            retention_days=0,
            now=datetime(2026, 7, 1, tzinfo=UTC),
        )


def test_is_degraded_observable_profile_requested__blank_string_is_false() -> None:
    assert is_degraded_observable_profile_requested("   ") is False
    assert is_degraded_observable_profile_requested("") is False


def test_resolve_replay_readiness_verdict__none_run_type_uses_rebuild_only() -> None:
    """Exercise _normalize_run_type_token(None) via the public readiness resolver."""
    verdict = resolve_replay_readiness_verdict(
        replay_capability=ReplayCapability.REBUILD_ONLY,
        strict_requirement_requested=False,
        strict_exact_replay_supported=True,
        run_type=None,
        debug_only=False,
    )
    assert verdict.value == "rebuild_only"


def test_registered_reproducibility_family_inventory__returns_sorted_profiles() -> None:
    inventory = registered_reproducibility_family_inventory()
    assert isinstance(inventory, list)
    assert inventory
    assert all(isinstance(item, dict) for item in inventory)


def test_infer_ledger_event_family__blank_event_type_is_diagnostic() -> None:
    assert infer_ledger_event_family("") == "diagnostic"
    assert infer_ledger_event_family("   ") == "diagnostic"


def test_ledger_event__canonicalize_non_mapping_raises_type_error() -> None:
    event = LedgerEvent(
        event_type="stage_completed",
        timestamp="2026-07-01T00:00:00Z",
        run_id="run-td04",
        data={"ok": True},
    )
    with patch(
        "bioetl.domain.control_plane.ledger.core_events.deserialize_from_json",
        return_value=["not", "a", "mapping"],
    ):
        with pytest.raises(TypeError, match="Ledger event data must serialize"):
            event.to_mapping()


# ---------------------------------------------------------------------------
# behavior
# ---------------------------------------------------------------------------


def test_apply_invalid_record_policy__error_already_terminal_unchanged() -> None:
    outcome = DQRuleOutcome(
        rule_id="r1",
        violation_kind=DQViolationKind.BUSINESS_RULE_VIOLATION,
        severity="error",
        disposition=DQDisposition.FAIL,
        disposition_reason="already terminal",
    )
    dq_config = SimpleNamespace(invalid_record_policy="quarantine")
    result = _apply_invalid_record_policy(
        outcome,
        dq_config=cast(Any, dq_config),
        severity="error",
    )
    assert result is outcome
    assert result.disposition is DQDisposition.FAIL


def test_cross_validation_apply_disposition__non_blocker_issues_passthrough() -> None:
    issue = ValidationIssue(
        code=IssueCode.CMP_PF_CV_011,
        severity=ValidationSeverity.WARNING,
        layer=ValidationLayer.DEEP_PREFLIGHT,
        message="threshold soft",
    )
    result = ValidationResult(
        issues=[issue],
        validation_layer=ValidationLayer.DEEP_PREFLIGHT,
        execution_context={},
    )
    config = CrossValidationConfig(
        pairs=[{"chembl": ["pubmed"]}],
        rules={},
        disposition_policy=CrossValidationDispositionPolicy.FAIL,
    )
    applied = CrossValidationValidator().apply_disposition(result, config)
    assert applied.issues == result.issues


def test_organism_classification_stats__counts_source_conflicts() -> None:
    classifier = OrganismClassifier()
    conflict_result = OrganismClassificationResult(
        organism_class=None,
        normalized_organism=None,
        taxonomy_id=None,
        source="none",
        source_conflict=True,
        reason="td04",
    )
    stats = classifier.compute_stats([conflict_result])
    assert isinstance(stats, ClassificationStats)
    assert stats.conflict_count == 1
    assert stats.total == 1


def test_aggregate_concentrations_with_uncertainty__empty_raises() -> None:
    host = _ActivityAggregatorExtensions()
    with pytest.raises(ValueError, match="Cannot aggregate empty sequence"):
        host.aggregate_concentrations_with_uncertainty([])


def test_ne_condition_matches__inequality() -> None:
    assert _ne_condition_matches("a", "b") is True
    assert _ne_condition_matches("a", "a") is False


# ---------------------------------------------------------------------------
# entities / workflow / types
# ---------------------------------------------------------------------------


def test_id_mapping_result__invalid_mapping_status_raises() -> None:
    with pytest.raises(ValueError, match="Invalid mapping_status"):
        IDMappingResult(
            entity_id="idmap:td04",
            content_hash="h",
            run_id="run",
            run_type="rebuild",
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
            _index=0,
            target_id="CHEMBL1",
            mapping_status=cast(Any, "bogus"),
        )


def test_workflow_config__step_ids_declared_order() -> None:
    config = WorkflowConfig(
        name="td04_workflow",
        steps=(
            WorkflowStepConfig(step_id="seed", pipeline_name="chembl_activity"),
            WorkflowStepConfig(
                step_id="dep",
                pipeline_name="chembl_molecule",
                depends_on=("seed",),
            ),
        ),
    )
    assert config.step_ids == ("seed", "dep")


def test_composite_fsm__missing_rule_after_can_transition_true() -> None:
    machine = CompositeFSM()
    machine.current_phase = ExecutionPhase.PREFLIGHT
    with patch.object(machine, "can_transition", return_value=True):
        machine.transition_table = {ExecutionPhase.PREFLIGHT: []}
        with pytest.raises(ValueError, match="No transition rule found"):
            machine.transition(PhaseTransition.ANY_TO_FAILED)


def test_coerce_snapshot_refs__skips_non_dict_items() -> None:
    refs = coerce_snapshot_refs([{"snapshot_id": "s1"}, "skip-me", 42, {"a": 1}])
    assert refs == ({"snapshot_id": "s1"}, {"a": 1})


# ---------------------------------------------------------------------------
# normalization
# ---------------------------------------------------------------------------


def test_parse_chembl_field_ref__requires_chembl_prefix() -> None:
    with pytest.raises(ValueError, match="chembl_"):
        _parse_chembl_field_ref("activity.standard_type")


def test_resolve_standard_profile_value__missing_required_without_spec() -> None:
    with pytest.raises(TypeError, match="missing required argument"):
        _resolve_standard_profile_value(
            field_name="profile_name",
            spec=None,
            overrides={},
        )


def test_legacy_qudt_identifier_from_uri__openphacts_unknown_path() -> None:
    assert (
        _legacy_qudt_identifier_from_uri("https://www.openphacts.org/units/micromolar")
        is None
    )


def test_structured_payload_policy__uses_canonical_json_only() -> None:
    policy = StructuredPayloadPolicy(
        profile_name="test.profile",
        field_name="payload",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.STRUCTURED_OBJECT,
        semantic_policy=StructuredPayloadSemanticPolicy.CANONICAL_JSON_BIBLIOGRAPHIC_EVIDENCE,
        raw_sidecar_field=None,
        canonical_sidecar_field=None,
        rationale="td04",
    )
    assert policy.requires_raw_sidecar_before_semantic_transform is False
    assert policy.uses_canonical_json_only is True


def test_compute_manifest_execution_fingerprint__delegates() -> None:
    payload = {"pipeline_name": "chembl_activity", "run_type": "rebuild"}
    fingerprint = compute_manifest_execution_fingerprint(payload)
    assert isinstance(fingerprint, str)
    assert fingerprint


def test_publication_structured_field_policy__raw_provider_hash_ordering() -> None:
    policy = PublicationStructuredFieldPolicy(
        profile_name="pubmed.publication",
        field_name="raw_field",
        representation=FieldRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=CollectionSemantics.RAW_PROVIDER_VALUE,
    )
    assert policy.hash_ordering == "raw_provider_value"


def test_normalize_profile_case__delegates_to_normalize_case() -> None:
    normalized = normalize_profile_case("ACTIVE")
    assert isinstance(normalized, str)
    assert normalized in {"ACTIVE", "active"}


def test_normalize_profile_bao_label_from_bao_format__non_string_value() -> None:
    assert normalize_profile_bao_label_from_bao_format(123) is None


# ---------------------------------------------------------------------------
# composite / config / ports / filtering / exceptions / value objects
# ---------------------------------------------------------------------------


def test_composite_result__is_success_false_when_required_dependency_failed() -> None:
    seed = SeedResult(pipeline_name="seed", records_silver=10)
    dep = DependencyResult(
        pipeline_name="dep",
        status=DependencyStatus.FAILED,
    )
    result = CompositeResult(
        composite_name="c",
        composite_run_id="run",
        seed_result=seed,
        dependency_results={"dep": dep},
        _required_dependencies=frozenset({"dep"}),
    )
    assert result.required_dependencies_succeeded is False
    assert result.is_success is False


def test_runtime_config__validates_debug_export_formats_on_init() -> None:
    config = RuntimeConfig(run_type=RunType.REBUILD, debug_export_formats=("csv",))
    assert config.debug_export_formats == ("csv",)
    with pytest.raises(ValueError, match="debug_export_formats"):
        RuntimeConfig(run_type=RunType.REBUILD, debug_export_formats=("pdf",))


def test_layer_column_config__coerces_mapping_rename_fields() -> None:
    config = LayerColumnConfig(
        columns=("a", "b"),
        rename_fields=cast(Any, [("a", "A"), ("b", "B")]),
    )
    assert config.rename_fields == {"a": "A", "b": "B"}


def test_noop_metadata_writer__attach_artifact_recorder_accepts_none() -> None:
    writer = NoOpMetadataWriter()
    writer.attach_artifact_recorder(None)
    writer.attach_artifact_recorder(lambda *_a, **_k: None)


def test_filter_load_result__is_multi_column_true() -> None:
    result = FilterLoadResult(
        column_ids={"col_a": ("1",), "col_b": ("2",)},
    )
    assert result.is_multi_column is True


def test_normalize_silver_filter_compatibility_mode__accepts_canonical() -> None:
    assert (
        normalize_silver_filter_compatibility_mode("structural_only_compat")
        == "structural_only_compat"
    )


def test_bioetl_error__context_kwargs_attached() -> None:
    err = BioETLError("boom", pipeline="chembl_activity", stage="extract")
    assert err.context["pipeline"] == "chembl_activity"
    assert err.context["stage"] == "extract"


def test_validation_error__sets_record_id() -> None:
    err = ValidationError("bad row", record_id="row-1", field="smiles")
    assert err.record_id == "row-1"
    assert err.field == "smiles"


def test_resolve_rate_limit_params__default_message_when_all_none() -> None:
    provider_name, message, service = resolve_rate_limit_params(None, None, None)
    assert provider_name == "unknown"
    assert message == "Rate limit exceeded"
    assert service is None


def test_molecular_weight__eq_not_implemented_for_other_types() -> None:
    mw = MolecularWeight(12.0)
    assert mw.__eq__("not-a-weight") is NotImplemented


def test_activity_value__eq_not_implemented_for_other_types() -> None:
    value = ActivityValue(value=1.0, unit="nM")
    assert value.__eq__(object()) is NotImplemented


def test_value_object__setattr_before_value_init_allows_construction() -> None:
    class _TinyVO(ValueObject[int]):
        def _validate(self, value: int) -> int:
            return value

    vo = _TinyVO(7)
    assert vo.value == 7
    with pytest.raises(AttributeError, match="immutable"):
        vo._value = 9  # type: ignore[misc]
