"""Unit tests for checkpoint compatibility service v2."""

import pytest

from bioetl.application.services.checkpoint_compatibility_service_v2 import (
    CheckpointCompatibilityConfig,
    CheckpointCompatibilityMode,
    CheckpointCompatibilityServiceV2,
    CheckpointIdentity,
    CompatibilityVerdict,
    ExecutionPhase,
    create_checkpoint_compatibility_service_v2,
)

HASH_A = "a" * 64
HASH_B = "b" * 64

CONFIG_MISMATCH_SUGGESTION = (
    "Configuration mismatch detected. Review config changes and update checkpoint "
    "or configuration to match."
)
CONFIG_OVERRIDE_SUGGESTION = (
    "Configuration mismatch can be overridden with --allow-config-mismatch if "
    "changes are backward-compatible."
)
DEPENDENCY_PHASE_SUGGESTION = (
    "For dependency/enrichment phases, consider re-running only affected sources "
    "instead of full resume."
)
MAJOR_SCHEMA_SUGGESTION = (
    "Major schema version incompatibility. Checkpoint cannot be used. Consider "
    "schema migration or starting fresh execution."
)
MERGE_PHASE_SUGGESTION = (
    "For merge/cross-validation phases, review conflict resolution and validation "
    "rules as they may be affected by config changes."
)


def _assert_component(
    result,
    component_name: str,
    *,
    compatible: bool,
    reason: str,
    severity: str,
) -> None:
    component = result.details[component_name]
    assert component["compatible"] is compatible
    assert component["reason"] == reason
    assert component["severity"] == severity


def _assert_hex_fingerprint(value: str) -> None:
    assert len(value) == 64
    assert all(char in "0123456789abcdef" for char in value)


def test_service_creation():
    """Test that service can be created."""
    service = CheckpointCompatibilityServiceV2()
    assert isinstance(service, CheckpointCompatibilityServiceV2)
    assert service.config.mode == CheckpointCompatibilityMode.STRICT
    assert service.config.max_schema_version_delta == 1


def test_factory_function():
    """Test factory function."""
    service = create_checkpoint_compatibility_service_v2()
    assert isinstance(service, CheckpointCompatibilityServiceV2)


def test_custom_config():
    """Test service with custom configuration."""
    config = CheckpointCompatibilityConfig(
        mode=CheckpointCompatibilityMode.LENIENT,
        allow_policy_override=True,
        max_schema_version_delta=2,
    )
    service = CheckpointCompatibilityServiceV2(config)
    assert service.config.mode == CheckpointCompatibilityMode.LENIENT
    assert service.config.allow_policy_override is True
    assert service.config.max_schema_version_delta == 2


def test_identical_checkpoint_compatibility():
    """Test compatibility with identical checkpoints."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.COMPATIBLE
    assert result.message == "Checkpoint is compatible for dependency_execution phase"
    assert result.execution_phase == ExecutionPhase.DEPENDENCY_EXECUTION
    _assert_component(
        result,
        "phase_compatibility",
        compatible=True,
        reason="same_execution_phase",
        severity="none",
    )
    _assert_component(
        result,
        "config_compatibility",
        compatible=True,
        reason="identical_config_hash",
        severity="none",
    )
    _assert_component(
        result,
        "execution_identity_compatibility",
        compatible=True,
        reason="identical_degraded_runtime_anchor_fingerprint",
        severity="none",
    )
    _assert_component(
        result,
        "schema_compatibility",
        compatible=True,
        reason="identical_schema_version",
        severity="none",
    )
    assert result.recovery_suggestions == [DEPENDENCY_PHASE_SUGGESTION]


def test_phase_incompatibility():
    """Test incompatibility due to phase mismatch."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.MERGE,
        checkpoint_schema_version="1.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.PREFLIGHT,  # Too early
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MINOR_INCOMPATIBLE
    assert (
        result.message
        == "Checkpoint has minor incompatibilities with current merge phase"
    )
    _assert_component(
        result,
        "phase_compatibility",
        compatible=True,
        reason="compatible_phase_transition",
        severity="minor",
    )
    assert result.recovery_suggestions == [MERGE_PHASE_SUGGESTION]


def test_config_hash_incompatibility():
    """Test incompatibility due to config hash mismatch."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_B,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        result.message
        == "Checkpoint is incompatible with current dependency_execution phase"
    )
    _assert_component(
        result,
        "config_compatibility",
        compatible=False,
        reason="different_config_hash",
        severity="major",
    )
    _assert_component(
        result,
        "execution_identity_compatibility",
        compatible=False,
        reason="degraded_runtime_anchor_fingerprint_mismatch",
        severity="major",
    )
    assert result.recovery_suggestions == [
        CONFIG_MISMATCH_SUGGESTION,
        DEPENDENCY_PHASE_SUGGESTION,
    ]


def test_schema_version_incompatibility():
    """Test incompatibility due to schema version mismatch."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="2.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",  # Different major version
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        result.message
        == "Checkpoint is incompatible with current dependency_execution phase"
    )
    _assert_component(
        result,
        "schema_compatibility",
        compatible=False,
        reason="incompatible_major_version",
        severity="major",
    )
    assert result.recovery_suggestions == [
        MAJOR_SCHEMA_SUGGESTION,
        DEPENDENCY_PHASE_SUGGESTION,
    ]


def test_minor_schema_version_compatibility():
    """Test compatibility with minor schema version difference."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.1.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",  # Minor version difference
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MINOR_INCOMPATIBLE
    assert (
        result.message
        == "Checkpoint has minor incompatibilities with current dependency_execution phase"
    )
    _assert_component(
        result,
        "schema_compatibility",
        compatible=True,
        reason="compatible_minor_version_delta_1",
        severity="minor",
    )
    assert result.recovery_suggestions == [DEPENDENCY_PHASE_SUGGESTION]


def test_lenient_mode_compatibility():
    """Test compatibility in lenient mode."""
    config = CheckpointCompatibilityConfig(mode=CheckpointCompatibilityMode.LENIENT)
    service = CheckpointCompatibilityServiceV2(config)

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.1.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        result.message
        == "Checkpoint is compatible for dependency_execution phase (mode: lenient)"
    )
    assert result.details["compatibility_mode"] == "lenient"
    _assert_component(
        result,
        "schema_compatibility",
        compatible=True,
        reason="compatible_minor_version_delta_1",
        severity="minor",
    )
    assert result.recovery_suggestions == [DEPENDENCY_PHASE_SUGGESTION]


def test_legacy_mode_compatibility():
    """Test compatibility in legacy mode."""
    config = CheckpointCompatibilityConfig(mode=CheckpointCompatibilityMode.LEGACY)
    service = CheckpointCompatibilityServiceV2(config)

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="2.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_B,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",  # Different version
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        result.message
        == "Checkpoint is compatible for dependency_execution phase (mode: legacy)"
    )
    assert result.details["compatibility_mode"] == "legacy"
    _assert_component(
        result,
        "config_compatibility",
        compatible=False,
        reason="different_config_hash",
        severity="major",
    )
    _assert_component(
        result,
        "schema_compatibility",
        compatible=False,
        reason="incompatible_major_version",
        severity="major",
    )
    assert result.recovery_suggestions == [
        CONFIG_MISMATCH_SUGGESTION,
        MAJOR_SCHEMA_SUGGESTION,
        DEPENDENCY_PHASE_SUGGESTION,
    ]


def test_compatible_phase_transition():
    """Test compatible phase transition."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.PREFLIGHT,  # Earlier phase
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MINOR_INCOMPATIBLE
    assert (
        result.message
        == "Checkpoint has minor incompatibilities with current dependency_execution phase"
    )
    _assert_component(
        result,
        "phase_compatibility",
        compatible=True,
        reason="compatible_phase_transition",
        severity="minor",
    )
    assert result.recovery_suggestions == [DEPENDENCY_PHASE_SUGGESTION]


def test_incompatible_phase_transition():
    """Test incompatible phase transition."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.PREFLIGHT,
        checkpoint_schema_version="1.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.MERGE,  # Later phase
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert result.message == "Checkpoint is incompatible with current preflight phase"
    _assert_component(
        result,
        "phase_compatibility",
        compatible=False,
        reason="incompatible_phase_transition",
        severity="major",
    )
    assert result.recovery_suggestions == [
        "Cannot resume from preflight to incompatible phase. Consider restarting "
        "execution from beginning."
    ]


def test_terminal_phase_compatibility():
    """Test that terminal phases cannot be resumed."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.COMPLETED_SUCCESS,  # Terminal phase
        checkpoint_schema_version="1.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.COMPLETED_SUCCESS,
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.COMPATIBLE
    assert result.message == "Checkpoint is compatible for completed_success phase"
    assert result.recovery_suggestions == []


def test_recovery_suggestions():
    """Test that recovery suggestions are generated appropriately."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.MERGE,
        checkpoint_schema_version="2.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_B,
        execution_phase=ExecutionPhase.PREFLIGHT,
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    _assert_component(
        result,
        "config_compatibility",
        compatible=False,
        reason="different_config_hash",
        severity="major",
    )
    _assert_component(
        result,
        "schema_compatibility",
        compatible=False,
        reason="incompatible_major_version",
        severity="major",
    )
    assert result.recovery_suggestions == [
        CONFIG_MISMATCH_SUGGESTION,
        MAJOR_SCHEMA_SUGGESTION,
        MERGE_PHASE_SUGGESTION,
    ]


def test_compatibility_details():
    """Test that compatibility details are comprehensive."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.1.0",
        composite_run_identity="run-001",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_B,
        execution_phase=ExecutionPhase.PREFLIGHT,
        checkpoint_schema_version="1.0.0",
        composite_run_identity="run-002",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    # Check details structure
    details = result.details
    assert "phase_compatibility" in details
    assert "config_compatibility" in details
    assert "execution_identity_compatibility" in details
    assert "schema_compatibility" in details
    assert "current_identity" in details
    assert "checkpoint_identity" in details
    assert "compatibility_mode" in details

    # Check identity details
    assert details["current_identity"]["composite_run_identity"] == "run-001"
    assert details["checkpoint_identity"]["composite_run_identity"] == "run-002"
    assert details["current_identity"]["canonical_execution_identity_payload"] == {}
    assert details["checkpoint_identity"]["canonical_execution_identity_payload"] == {}
    _assert_hex_fingerprint(
        details["current_identity"]["degraded_runtime_anchor_fingerprint"]
    )
    _assert_hex_fingerprint(
        details["checkpoint_identity"]["degraded_runtime_anchor_fingerprint"]
    )


def test_composite_run_identity_mismatch_is_enforced():
    """Legacy composite drift alone no longer overrides compatibility."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        composite_run_identity="run-001",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        composite_run_identity="run-002",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        result.details["execution_identity_compatibility"]["reason"]
        == "identical_degraded_runtime_anchor_fingerprint"
    )


def test_composite_run_identity_missing_is_enforced():
    """Missing legacy composite identity alone no longer fails compatibility."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        composite_run_identity="run-001",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        composite_run_identity=None,
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        result.details["execution_identity_compatibility"]["reason"]
        == "identical_degraded_runtime_anchor_fingerprint"
    )


def test_matching_execution_fingerprint_overrides_composite_run_identity_drift():
    """Canonical execution identity should win over legacy composite drift."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        execution_fingerprint="fp-shared",
        composite_run_identity="run-001",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        execution_fingerprint="fp-shared",
        composite_run_identity="run-002",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        result.details["execution_identity_compatibility"]["reason"]
        == "identical_execution_fingerprint"
    )


def test_execution_fingerprint_takes_precedence_over_runtime_anchors():
    """Explicit execution fingerprints should drive identity compatibility first."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        execution_fingerprint="fp-current",
        manifest_id="manifest-shared",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        execution_fingerprint="fp-checkpoint",
        manifest_id="manifest-shared",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        result.details["execution_identity_compatibility"]["reason"]
        == "execution_fingerprint_mismatch"
    )


def test_runtime_anchor_fingerprint_is_used_when_execution_fingerprint_missing():
    """Fallback execution identity should use the normalized runtime-anchor contract."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        manifest_id="manifest-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-001",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        manifest_id="manifest-b",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-001",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        result.details["execution_identity_compatibility"]["reason"]
        == "degraded_runtime_anchor_fingerprint_mismatch"
    )


@pytest.mark.parametrize(
    ("current_identity", "checkpoint_identity"),
    [
        (
            CheckpointIdentity(
                effective_config_hash=HASH_A,
                execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
                checkpoint_schema_version="1.0.0",
                manifest_id=" manifest-a ",
                contract_ref="chembl.activity",
                contract_version="1.0.0",
                effective_config_artifact_id="artifact-001",
            ),
            CheckpointIdentity(
                effective_config_hash=HASH_A,
                execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
                checkpoint_schema_version="1.0.0",
                manifest_id="manifest-a",
                contract_ref="chembl.activity",
                contract_version="1.0.0",
                effective_config_artifact_id="artifact-001",
            ),
        ),
        (
            CheckpointIdentity(
                effective_config_hash=HASH_A,
                execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
                checkpoint_schema_version="1.0.0",
                manifest_id="manifest-a",
                contract_ref=" ChemBL.Activity ",
                contract_version=" v1 ",
                effective_config_artifact_id="artifact-001",
            ),
            CheckpointIdentity(
                effective_config_hash=HASH_A,
                execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
                checkpoint_schema_version="1.0.0",
                manifest_id="manifest-a",
                contract_ref="chembl.activity",
                contract_version="1.0.0",
                effective_config_artifact_id="artifact-001",
            ),
        ),
    ],
)
def test_runtime_anchor_fingerprint_normalizes_equivalent_dirty_anchors(
    current_identity: CheckpointIdentity,
    checkpoint_identity: CheckpointIdentity,
) -> None:
    """Whitespace and case drift should not fork degraded runtime-anchor identity."""
    service = CheckpointCompatibilityServiceV2()

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        result.details["execution_identity_compatibility"]["reason"]
        == "identical_degraded_runtime_anchor_fingerprint"
    )
    assert (
        result.details["current_identity"]["degraded_runtime_anchor_fingerprint"]
        == result.details["checkpoint_identity"]["degraded_runtime_anchor_fingerprint"]
    )


def test_runtime_anchor_fingerprint_normalizes_sha256_prefix_drift_in_service_details():
    """Degraded runtime-anchor fingerprints should normalize SHA256 prefix drift."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash=f" SHA256:{HASH_A.upper()} ",
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        manifest_id="manifest-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-001",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        manifest_id="manifest-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-001",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert result.details["config_compatibility"]["reason"] == "different_config_hash"
    assert (
        result.details["execution_identity_compatibility"]["reason"]
        == "identical_degraded_runtime_anchor_fingerprint"
    )
    assert (
        result.details["current_identity"]["degraded_runtime_anchor_fingerprint"]
        == result.details["checkpoint_identity"]["degraded_runtime_anchor_fingerprint"]
    )


def test_canonical_checkpoint_execution_identity_fallback_is_used_when_available():
    """Canonical checkpoint fallback should take precedence over degraded anchors."""
    service = CheckpointCompatibilityServiceV2()

    current_identity = CheckpointIdentity(
        effective_config_hash="a" * 64,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        pipeline_name="chembl_activity",
        run_type="incremental",
        pipeline_version="1.2.3",
        dq_contract_compatibility_hash="dq-hash-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        exact_replay=True,
        input_snapshot_fingerprint="snapshot-fp-a",
        manifest_id="manifest-a",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash="a" * 64,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        pipeline_name="chembl_activity",
        run_type="incremental",
        pipeline_version="1.2.3",
        dq_contract_compatibility_hash="dq-hash-b",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        exact_replay=True,
        input_snapshot_fingerprint="snapshot-fp-a",
        manifest_id="manifest-a",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        result.details["execution_identity_compatibility"]["reason"]
        == "checkpoint_execution_identity_fallback_mismatch"
    )
    current_fallback_fingerprint = result.details["current_identity"][
        "checkpoint_execution_identity_fallback_fingerprint"
    ]
    checkpoint_fallback_fingerprint = result.details["checkpoint_identity"][
        "checkpoint_execution_identity_fallback_fingerprint"
    ]
    _assert_hex_fingerprint(current_fallback_fingerprint)
    _assert_hex_fingerprint(checkpoint_fallback_fingerprint)
    assert current_fallback_fingerprint != checkpoint_fallback_fingerprint


def test_schema_version_delta_config():
    """Test schema version delta configuration."""
    config = CheckpointCompatibilityConfig(max_schema_version_delta=2)
    service = CheckpointCompatibilityServiceV2(config)

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.3.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",  # Delta of 3
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        result.details["schema_compatibility"]["reason"]
        == "exceeds_max_version_delta_3"
    )


def test_policy_override_suggestions():
    """Test policy override suggestions."""
    config = CheckpointCompatibilityConfig(allow_policy_override=True)
    service = CheckpointCompatibilityServiceV2(config)

    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_B,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert result.recovery_suggestions == [
        CONFIG_MISMATCH_SUGGESTION,
        CONFIG_OVERRIDE_SUGGESTION,
        DEPENDENCY_PHASE_SUGGESTION,
    ]


def test_phase_specific_suggestions():
    """Test phase-specific recovery suggestions."""
    service = CheckpointCompatibilityServiceV2()

    # Test dependency execution phase
    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_B,
        execution_phase=ExecutionPhase.PREFLIGHT,
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.recovery_suggestions == [
        CONFIG_MISMATCH_SUGGESTION,
        DEPENDENCY_PHASE_SUGGESTION,
    ]

    # Test merge phase
    current_identity = CheckpointIdentity(
        effective_config_hash=HASH_A,
        execution_phase=ExecutionPhase.MERGE,
        checkpoint_schema_version="1.0.0",
    )

    checkpoint_identity = CheckpointIdentity(
        effective_config_hash=HASH_B,
        execution_phase=ExecutionPhase.CROSS_VALIDATION,
        checkpoint_schema_version="1.0.0",
    )

    result = service.check_compatibility(current_identity, checkpoint_identity)

    assert result.recovery_suggestions == [
        "Cannot resume from merge to incompatible phase. Consider restarting execution "
        "from beginning.",
        CONFIG_MISMATCH_SUGGESTION,
        MERGE_PHASE_SUGGESTION,
    ]
