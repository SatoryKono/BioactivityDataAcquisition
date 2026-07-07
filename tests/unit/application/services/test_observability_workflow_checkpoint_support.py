"""Unit tests for checkpoint compatibility helpers in observability workflow."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services._observability_workflow_checkpoint_support import (
    build_checkpoint_compatibility_section,
)
from bioetl.application.services.checkpoint_service import CheckpointInfo


pytestmark = pytest.mark.unit


def _manifest_result(*, exact_replay: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        manifest=SimpleNamespace(
            run_id="run-abc",
            manifest_id="manifest-abc",
            execution_fingerprint="fp-abc",
            code_provenance=SimpleNamespace(
                effective_config_hash="cfg-hash",
                effective_config_artifact_id="cfg-artifact",
                contract_ref="chembl/activity/gold",
                contract_version="1.0.0",
                dq_contract_compatibility_hash="dq-hash",
            ),
        ),
        diagnostics={
            "input_snapshot_identity_fingerprint": "snapshot-fp",
            "requested_exact_replay": exact_replay,
            "continuation_mode": "resume",
        },
        identity_graph={"replay_capability": "exact_replay_supported"},
    )


def _matching_checkpoint(*, exact_replay: bool = False) -> CheckpointInfo:
    return CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="run-abc",
        metadata={
            "manifest_id": "manifest-abc",
            "execution_fingerprint": "fp-abc",
            "effective_config_hash": "cfg-hash",
            "effective_config_artifact_id": "cfg-artifact",
            "contract_ref": "chembl/activity/gold",
            "contract_version": "1.0.0",
            "dq_contract_compatibility_hash": "dq-hash",
            "exact_replay": exact_replay,
            "input_snapshot_fingerprint": "snapshot-fp",
        },
    )


def test_build_checkpoint_compatibility_section_reports_missing_checkpoint() -> None:
    section = build_checkpoint_compatibility_section(
        checkpoint=None,
        run_manifest=_manifest_result(),
    )

    assert section["status"] == "missing_evidence"
    assert section["compatible"] is False
    assert section["taxonomy"] == "missing_checkpoint"
    assert section["missing_anchors"] == ["checkpoint"]


def test_build_checkpoint_compatibility_section_reports_compatible_anchors() -> None:
    checkpoint = _matching_checkpoint(exact_replay=False)

    section = build_checkpoint_compatibility_section(
        checkpoint=checkpoint,
        run_manifest=_manifest_result(exact_replay=False),
    )

    assert section["status"] == "compatible"
    assert section["compatible"] is True
    assert section["matched_anchors"]
    assert not section["mismatched_anchors"]
    assert not section["missing_anchors"]


def test_build_checkpoint_compatibility_section_marks_corrupt_checkpoint() -> None:
    checkpoint = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="run-abc",
        metadata={"status": "corrupt"},
    )

    section = build_checkpoint_compatibility_section(
        checkpoint=checkpoint,
        run_manifest=_manifest_result(),
    )

    assert section["status"] == "corruption"
    assert section["compatible"] is False
    assert section["taxonomy"] == "corrupted_checkpoint_payload"


def test_build_checkpoint_compatibility_section_reports_missing_manifest() -> None:
    section = build_checkpoint_compatibility_section(
        checkpoint=_matching_checkpoint(),
        run_manifest=None,
    )

    assert section["status"] == "missing_evidence"
    assert section["compatible"] is False
    assert section["taxonomy"] == "missing_run_manifest"
    assert section["missing_anchors"] == ["run_manifest"]
    assert section["replay_resume_rebuild_verdict"] == "non_replayable"


def test_build_checkpoint_compatibility_section_reports_anchor_drift() -> None:
    checkpoint = _matching_checkpoint()
    checkpoint.metadata["manifest_id"] = "manifest-other"
    checkpoint.metadata["effective_config_hash"] = None

    section = build_checkpoint_compatibility_section(
        checkpoint=checkpoint,
        run_manifest=_manifest_result(exact_replay=False),
    )

    assert section["status"] == "incompatible"
    assert section["compatible"] is False
    assert section["taxonomy"] == "blocked_resume"
    assert section["missing_anchors"] == ["effective_config_hash"]
    assert section["mismatched_anchors"] == [
        {
            "anchor": "manifest_id",
            "checkpoint": "manifest-other",
            "manifest": "manifest-abc",
        }
    ]


def test_exact_replay_request_is_blocked_when_manifest_only_supports_resume() -> None:
    checkpoint = _matching_checkpoint(exact_replay=True)

    section = build_checkpoint_compatibility_section(
        checkpoint=checkpoint,
        run_manifest=_manifest_result(exact_replay=True),
    )

    assert section["status"] == "incompatible"
    assert section["compatible"] is False
    assert section["taxonomy"] == "exact_replay_blocked_resume_semantics"
    assert section["mismatched_anchors"] == [
        {
            "anchor": "operator_replay_mode",
            "checkpoint": "resume",
            "manifest": "resume",
        }
    ]
    assert section["replay_resume_rebuild_verdict"] == "resume_only"
