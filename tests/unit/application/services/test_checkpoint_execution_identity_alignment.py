<<<<<<< Updated upstream
"""Regression tests that keep legacy and V2 execution identity semantics aligned."""

from __future__ import annotations

from unittest.mock import MagicMock

from bioetl.application.services.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.application.services.checkpoint_compatibility_service_v2 import (
    CheckpointCompatibilityServiceV2,
    CheckpointIdentity,
    CompatibilityVerdict,
    ExecutionPhase,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def _legacy_service() -> CheckpointCompatibilityService:
    return CheckpointCompatibilityService(logger=MagicMock())


def _v2_service() -> CheckpointCompatibilityServiceV2:
    return CheckpointCompatibilityServiceV2()


def _metadata(
    *,
    effective_config_hash: str = "a" * 64,
    composite_run_identity: str | None = None,
    execution_fingerprint: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    pipeline_version: str | None = None,
    manifest_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    effective_config_artifact_id: str | None = None,
) -> CheckpointMetadata:
    return CheckpointMetadata(
        records_processed=100,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        pipeline_version=pipeline_version,
        effective_config_hash=effective_config_hash,
        composite_run_identity=composite_run_identity,
        execution_fingerprint=execution_fingerprint,
        manifest_id=manifest_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        effective_config_artifact_id=effective_config_artifact_id,
    )


def _identity(
    *,
    effective_config_hash: str = "a" * 64,
    composite_run_identity: str | None = None,
    execution_fingerprint: str | None = None,
    manifest_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    effective_config_artifact_id: str | None = None,
) -> CheckpointIdentity:
    return CheckpointIdentity(
        effective_config_hash=effective_config_hash,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        composite_run_identity=composite_run_identity,
        execution_fingerprint=execution_fingerprint,
        manifest_id=manifest_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        effective_config_artifact_id=effective_config_artifact_id,
    )


def test_legacy_and_v2_align_when_execution_fingerprint_matches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(execution_fingerprint="fp-same")
    checkpoint_metadata = _metadata(execution_fingerprint="fp-same")
    current_identity = _identity(execution_fingerprint="fp-same")
    checkpoint_identity = _identity(execution_fingerprint="fp-same")

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is True
    assert v2_result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "identical_execution_fingerprint"
    )


def test_legacy_and_v2_align_when_execution_fingerprint_mismatches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(execution_fingerprint="fp-current")
    checkpoint_metadata = _metadata(execution_fingerprint="fp-checkpoint")
    current_identity = _identity(execution_fingerprint="fp-current")
    checkpoint_identity = _identity(execution_fingerprint="fp-checkpoint")

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is False
    assert legacy_result.execution_identity_compatible is False
    assert any(
        "Execution fingerprint mismatch" in msg for msg in legacy_result.messages
    )
    assert v2_result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "execution_fingerprint_mismatch"
    )


def test_legacy_and_v2_align_when_runtime_anchor_fingerprint_mismatches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(
        manifest_id="manifest-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )
    checkpoint_metadata = _metadata(
        manifest_id="manifest-b",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )
    current_identity = _identity(
        manifest_id="manifest-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )
    checkpoint_identity = _identity(
        manifest_id="manifest-b",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is False
    assert legacy_result.execution_identity_compatible is False
    assert any(
        "Degraded runtime-anchor fingerprint mismatch" in msg
        for msg in legacy_result.messages
    )
    assert v2_result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "degraded_runtime_anchor_fingerprint_mismatch"
    )


def test_legacy_and_v2_align_when_composite_run_identity_mismatches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(composite_run_identity="run-a")
    checkpoint_metadata = _metadata(composite_run_identity="run-b")
    current_identity = _identity(composite_run_identity="run-a")
    checkpoint_identity = _identity(composite_run_identity="run-b")

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is False
    assert legacy_result.execution_identity_compatible is False
    assert any(
        "Composite run identity mismatch" in msg for msg in legacy_result.messages
    )
    assert v2_result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "composite_run_identity_mismatch"
    )
||||||| Stash base
=======
"""Regression tests that keep legacy and V2 execution identity semantics aligned."""

from __future__ import annotations

from unittest.mock import MagicMock

from bioetl.application.services.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.application.services.checkpoint_compatibility_service_v2 import (
    CheckpointCompatibilityServiceV2,
    CheckpointIdentity,
    CompatibilityVerdict,
    ExecutionPhase,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def _legacy_service() -> CheckpointCompatibilityService:
    return CheckpointCompatibilityService(logger=MagicMock())


def _v2_service() -> CheckpointCompatibilityServiceV2:
    return CheckpointCompatibilityServiceV2()


def _metadata(
    *,
    effective_config_hash: str = "a" * 64,
    execution_fingerprint: str | None = None,
    manifest_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    effective_config_artifact_id: str | None = None,
) -> CheckpointMetadata:
    return CheckpointMetadata(
        records_processed=100,
        dq_contract_compatibility_hash="dq-same",
        pipeline_version="1.0.0",
        effective_config_hash=effective_config_hash,
        execution_fingerprint=execution_fingerprint,
        manifest_id=manifest_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        effective_config_artifact_id=effective_config_artifact_id,
    )


def _identity(
    *,
    effective_config_hash: str = "a" * 64,
    execution_fingerprint: str | None = None,
    manifest_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    effective_config_artifact_id: str | None = None,
) -> CheckpointIdentity:
    return CheckpointIdentity(
        effective_config_hash=effective_config_hash,
        execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
        checkpoint_schema_version="1.0.0",
        execution_fingerprint=execution_fingerprint,
        manifest_id=manifest_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        effective_config_artifact_id=effective_config_artifact_id,
    )


def test_legacy_and_v2_align_when_execution_fingerprint_matches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(execution_fingerprint="fp-same")
    checkpoint_metadata = _metadata(execution_fingerprint="fp-same")
    current_identity = _identity(execution_fingerprint="fp-same")
    checkpoint_identity = _identity(execution_fingerprint="fp-same")

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is True
    assert v2_result.verdict == CompatibilityVerdict.COMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "identical_execution_fingerprint"
    )


def test_legacy_and_v2_align_when_execution_fingerprint_mismatches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(execution_fingerprint="fp-current")
    checkpoint_metadata = _metadata(execution_fingerprint="fp-checkpoint")
    current_identity = _identity(execution_fingerprint="fp-current")
    checkpoint_identity = _identity(execution_fingerprint="fp-checkpoint")

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is False
    assert legacy_result.execution_identity_compatible is False
    assert any("Execution fingerprint mismatch" in msg for msg in legacy_result.messages)
    assert v2_result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "execution_fingerprint_mismatch"
    )


def test_legacy_and_v2_align_when_runtime_anchor_fingerprint_mismatches() -> None:
    legacy = _legacy_service()
    v2 = _v2_service()

    current_metadata = _metadata(
        manifest_id="manifest-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )
    checkpoint_metadata = _metadata(
        manifest_id="manifest-b",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )
    current_identity = _identity(
        manifest_id="manifest-a",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )
    checkpoint_identity = _identity(
        manifest_id="manifest-b",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-1",
    )

    legacy_result = legacy.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )
    v2_result = v2.check_compatibility(current_identity, checkpoint_identity)

    assert legacy_result.compatible is False
    assert legacy_result.execution_identity_compatible is False
    assert any(
        "Runtime anchor fingerprint mismatch" in msg for msg in legacy_result.messages
    )
    assert v2_result.verdict == CompatibilityVerdict.MAJOR_INCOMPATIBLE
    assert (
        v2_result.details["execution_identity_compatibility"]["reason"]
        == "runtime_anchor_fingerprint_mismatch"
    )
>>>>>>> Stashed changes
