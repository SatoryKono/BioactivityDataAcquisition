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
"""Regression tests for canonical checkpoint execution-identity semantics."""

from __future__ import annotations

import pytest

from pathlib import Path
from unittest.mock import MagicMock

import yaml

from bioetl.application.core.lifecycle.checkpoint_runtime import (
    enrich_metadata_with_execution_identity,
)
from bioetl.application.services.checkpoint._checkpoint_execution_identity_payload import (
    build_checkpoint_execution_identity_payload,
    has_canonical_checkpoint_execution_identity_fields,
)
from bioetl.application.services.checkpoint._checkpoint_compatibility_runtime_identity_details import (
    IdentityDetailsSpec,
    build_identity_details,
)
from bioetl.application.services.checkpoint.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
    normalize_runtime_anchor_payload,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.domain.types.execution_phase import ExecutionPhase

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = ROOT / "configs" / "quality" / "determinism_identity_policy.yaml"


def _service() -> CheckpointCompatibilityService:
    return CheckpointCompatibilityService(logger=MagicMock())


def _metadata(
    *,
    effective_config_hash: str | None = "a" * 64,
    composite_run_identity: str | None = None,
    execution_fingerprint: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    pipeline_version: str | None = None,
    manifest_id: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    git_commit: str | None = None,
    dependency_lock_hash: str | None = None,
    normalization_profile_ref: str | None = None,
    normalization_profile_version: str | None = None,
    normalization_profile_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    required_persistence_profile: str | None = None,
    input_snapshot_refs: tuple[dict[str, object], ...] = (),
    input_snapshot_ids: tuple[str, ...] = (),
    input_snapshot_fingerprint: str | None = None,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    exact_replay: bool | None = None,
    silver_filter_compatibility_mode: str | None = None,
) -> CheckpointMetadata:
    return CheckpointMetadata(
        records_processed=100,
        pipeline_name=pipeline_name,
        run_type=run_type,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        pipeline_version=pipeline_version,
        effective_config_hash=effective_config_hash,
        composite_run_identity=composite_run_identity,
        execution_fingerprint=execution_fingerprint,
        manifest_id=manifest_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        git_commit=git_commit,
        dependency_lock_hash=dependency_lock_hash,
        normalization_profile_ref=normalization_profile_ref,
        normalization_profile_version=normalization_profile_version,
        normalization_profile_hash=normalization_profile_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        required_persistence_profile=required_persistence_profile,
        input_snapshot_refs=input_snapshot_refs,
        input_snapshot_ids=input_snapshot_ids,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        exact_replay=exact_replay,
        silver_filter_compatibility_mode=silver_filter_compatibility_mode,
    )


def test_checkpoint_metadata_emits_canonical_execution_identity_fingerprint() -> None:
    metadata = _metadata(
        pipeline_name=" chembl_activity ",
        run_type=" INCREMENTAL ",
        pipeline_version=" 1.2.3 ",
        git_commit=" ABCDEF123 ",
        effective_config_hash=f" SHA256:{'a' * 64} ",
        dq_contract_compatibility_hash=" DEADBEEF ",
        contract_ref=" ChemBL.Activity ",
        contract_version=" v2 ",
        effective_config_artifact_id=" artifact-42 ",
        exact_replay=True,
        input_snapshot_fingerprint=" FACE ",
        silver_filter_compatibility_mode=" structural_only_compat ",
    )

    expected_payload = build_execution_identity_payload(
        pipeline_name=" chembl_activity ",
        run_type=" INCREMENTAL ",
        pipeline_version=" 1.2.3 ",
        git_commit=" ABCDEF123 ",
        effective_config_hash=f" SHA256:{'a' * 64} ",
        dq_contract_compatibility_hash=" DEADBEEF ",
        contract=(" ChemBL.Activity ", " v2 "),
        effective_config_artifact_id=" artifact-42 ",
        exact_replay=True,
        input_snapshot_fingerprint=" FACE ",
        silver_filter_compatibility_mode=" structural_only_compat ",
    )

    assert metadata.checkpoint_execution_identity_payload() == {
        key: value for key, value in expected_payload.items() if value is not None
    }
    assert metadata.checkpoint_execution_identity_fingerprint() == (
        compute_execution_identity_fingerprint(expected_payload)
    )


def test_checkpoint_execution_identity_payload_excludes_occurrence_only_identifiers() -> (
    None
):
    metadata = _metadata(
        pipeline_name="chembl_activity",
        run_type="incremental",
        pipeline_version="1.2.3",
        git_commit="abcdef123",
        effective_config_hash="a" * 64,
        effective_config_artifact_id="artifact-42",
        contract_ref="chembl.activity",
        contract_version="2.0.0",
        execution_fingerprint="fingerprint-checkpoint",
        manifest_id="manifest-occurrence-only",
        exact_replay=True,
        input_snapshot_fingerprint="snapshot-face",
    )
    payload = metadata.checkpoint_execution_identity_payload()
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(policy, dict)
    artifact_contract = policy["artifact_identity_contract"]
    assert isinstance(artifact_contract, dict)
    semantic_anchors = artifact_contract["semantic_identity_anchors"]
    assert isinstance(semantic_anchors, list)
    checkpoint_contract = next(
        entry
        for entry in semantic_anchors
        if isinstance(entry, dict)
        and entry.get("artifact") == "runtime.checkpoint_execution_identity"
    )
    forbidden_fields = checkpoint_contract["forbidden_occurrence_identity_fields"]
    assert isinstance(forbidden_fields, list)

    for field in forbidden_fields:
        assert field not in payload


def test_checkpoint_execution_identity_payload_helper_filters_none_fields() -> None:
    payload = build_checkpoint_execution_identity_payload(
        pipeline_name="chembl_activity",
        run_type="incremental",
        pipeline_version=None,
        git_commit="abc1234",
        dependency_lock_hash=None,
        effective_config_hash="a" * 64,
        dq_contract_compatibility_hash=None,
        contract=("chembl.activity", "1.0.0"),
        normalization_profile=(None, None, None),
        effective_config_artifact_id="effective-config-1",
        exact_replay=True,
        input_snapshot_fingerprint="snapshot-fp",
    )

    assert payload == {
        "contract_ref": "chembl.activity",
        "contract_version": "1.0.0",
        "effective_config_artifact_id": "effective-config-1",
        "effective_config_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "exact_replay": "true",
        "git_commit": "abc1234",
        "input_snapshot_fingerprint": "snapshot-fp",
        "pipeline_name": "chembl_activity",
        "run_type": "incremental",
        "silver_filter_compatibility_mode": "structural_only_compat",
    }


def test_checkpoint_execution_identity_payload_helper_can_fail_closed_empty() -> None:
    assert (
        build_checkpoint_execution_identity_payload(
            pipeline_name=None,
            run_type=None,
            pipeline_version=None,
            git_commit=None,
            dependency_lock_hash=None,
            effective_config_hash=None,
            dq_contract_compatibility_hash=None,
            contract=(None, None),
            normalization_profile=(None, None, None),
            effective_config_artifact_id=None,
            exact_replay=None,
            input_snapshot_fingerprint=None,
        )
        == {}
    )
    assert (
        build_checkpoint_execution_identity_payload(
            pipeline_name=None,
            run_type=None,
            pipeline_version=None,
            git_commit=None,
            dependency_lock_hash=None,
            effective_config_hash=None,
            dq_contract_compatibility_hash=None,
            contract=(None, None),
            normalization_profile=(None, None, None),
            effective_config_artifact_id=None,
            exact_replay=None,
            input_snapshot_fingerprint=None,
            silver_filter_compatibility_mode="structural_only_compat",
        )
        == {}
    )


def test_initial_execution_identity_outcome_honors_compatible_flag() -> None:
    from bioetl.application.services.checkpoint._checkpoint_compatibility_execution_validation import (
        _initial_execution_identity_outcome,
    )

    compatible, continuity_proven, messages = _initial_execution_identity_outcome(
        {
            "compatible": False,
            "reason": "execution_fingerprint_mismatch",
        }
    )

    assert compatible is False
    assert continuity_proven is True
    assert messages == []


def test_has_canonical_checkpoint_execution_identity_fields_detects_resume_fields() -> (
    None
):
    assert not has_canonical_checkpoint_execution_identity_fields(
        {"silver_filter_compatibility_mode": "structural_only_compat"}
    )
    assert has_canonical_checkpoint_execution_identity_fields(
        {"silver_filter_compatibility_mode": "structural_only_auto_promote"}
    )
    assert not has_canonical_checkpoint_execution_identity_fields(
        {"effective_config_hash": "a" * 64}
    )


def test_enrich_metadata_with_execution_identity_backfills_canonical_resume_anchors() -> (
    None
):
    checkpoint = _metadata(pipeline_version=None, git_commit=None)
    identity = _metadata(
        pipeline_version="1.2.3",
        git_commit="abcdef123",
        manifest_id="manifest-123",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-42",
        input_snapshot_fingerprint="face",
    )

    enriched = enrich_metadata_with_execution_identity(checkpoint, identity=identity)

    assert enriched.pipeline_version == "1.2.3"
    assert enriched.git_commit == "abcdef123"
    assert enriched.manifest_id == "manifest-123"
    assert enriched.contract_ref == "chembl.activity"
    assert enriched.contract_version == "1.0.0"
    assert enriched.effective_config_artifact_id == "artifact-42"
    assert enriched.input_snapshot_fingerprint == "face"


def test_resume_service_accepts_matching_execution_fingerprint() -> None:
    service = _service()
    current_metadata = _metadata(execution_fingerprint="fp-same")
    checkpoint_metadata = _metadata(execution_fingerprint="fp-same")

    result = service.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )

    assert result.compatible is True
    assert result.execution_identity_compatible is True


def test_resume_service_rejects_execution_fingerprint_mismatch() -> None:
    service = _service()
    current_metadata = _metadata(execution_fingerprint="fp-current")
    checkpoint_metadata = _metadata(execution_fingerprint="fp-checkpoint")

    result = service.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )

    assert result.compatible is False
    assert result.execution_identity_compatible is False
    assert any("Execution fingerprint mismatch" in msg for msg in result.messages)


def test_resume_service_rejects_runtime_anchor_fingerprint_mismatch() -> None:
    service = _service()
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

    result = service.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )

    assert result.compatible is False
    assert result.execution_identity_compatible is False
    assert any(
        "Degraded runtime-anchor fingerprint mismatch" in msg for msg in result.messages
    )


def test_runtime_anchor_fingerprint_matches_domain_contract() -> None:
    raw_payload = {
        "effective_config_hash": "a" * 64,
        "effective_config_artifact_id": " artifact-001 ",
        "contract_ref": " ChemBL.Activity ",
        "contract_version": " v1 ",
        "manifest_id": " manifest-a ",
    }
    expected_fingerprint = compute_execution_identity_fingerprint(
        normalize_runtime_anchor_payload(raw_payload)
    )
    details = build_identity_details(
        IdentityDetailsSpec(
            effective_config_hash="a" * 64,
            execution_phase=ExecutionPhase.DEPENDENCY_EXECUTION,
            checkpoint_schema_version="1.0.0",
            manifest_id=raw_payload["manifest_id"],
            contract_ref=raw_payload["contract_ref"],
            contract_version=raw_payload["contract_version"],
            effective_config_artifact_id=raw_payload["effective_config_artifact_id"],
        )
    )

    assert details["degraded_runtime_anchor_fingerprint"] == expected_fingerprint


def test_resume_service_ignores_composite_identity_drift_when_canonical_fingerprint_matches() -> (
    None
):
    service = _service()
    current_metadata = _metadata(
        dq_contract_compatibility_hash="same-hash",
        pipeline_version="1.0.0",
        execution_fingerprint="fp-same",
        composite_run_identity="run-current",
    )
    checkpoint_metadata = _metadata(
        dq_contract_compatibility_hash="same-hash",
        pipeline_version="1.0.0",
        execution_fingerprint="fp-same",
        composite_run_identity="run-checkpoint",
    )

    result = service.validate_checkpoint_compatibility(
        current_metadata,
        checkpoint_metadata,
    )

    assert result.compatible is True
    assert result.execution_identity_compatible is True
    assert not any("Composite run identity mismatch" in msg for msg in result.messages)
