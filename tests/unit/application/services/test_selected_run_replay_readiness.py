"""Selected-run exact replay readiness does not treat capability as READY."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.selected_run_replay_readiness import (
    BLOCKED,
    INSUFFICIENT,
    READY,
    UNSUPPORTED,
    project_selected_run_replay_readiness,
)

_PASSING_IDENTITY = {
    "pipeline_name": "chembl_activity",
    "run_id": "run-a",
    "status": "success",
    "run_type": "full",
    "replay_capability": "exact_replay_supported",
    "exact_replay_supported": True,
    "effective_config_hash": "abc",
    "dependency_lock_hash": "def",
    "input_snapshot_fingerprint": "ghi",
}


def _pass_probe() -> dict[str, str]:
    return {
        "code": "input_snapshot",
        "result": "pass",
        "reason": "digest_matches",
        "evidence_ref": "#/artifacts/0",
    }


def test_capability_without_artifact_inventory_is_not_ready() -> None:
    projection = project_selected_run_replay_readiness(identity=_PASSING_IDENTITY)
    assert projection["verdict"] == INSUFFICIENT
    assert "artifact_inventory" in projection["unknown_checks"]


def test_missing_artifact_blocks_even_when_capability_is_exact() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        inventory_present=True,
        artifact_probes=(
            {
                "code": "input_snapshot",
                "result": "fail",
                "reason": "artifact_missing",
                "evidence_ref": "#/artifacts/0",
            },
        ),
    )
    assert projection["verdict"] == BLOCKED
    assert projection["blockers"] == ["input_snapshot"]


def test_hash_without_object_is_not_ready() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        inventory_present=True,
        artifact_probes=(
            {
                "code": "input_snapshot",
                "result": "fail",
                "reason": "hash_without_object",
                "evidence_ref": "#/artifacts/0",
            },
        ),
    )
    assert projection["verdict"] == BLOCKED


def test_source_run_without_replay_of_run_id_can_be_ready() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
        evidence_revision="rev-1",
    )
    assert projection["verdict"] == READY
    replay_check = next(
        item for item in projection["checks"] if item["code"] == "replay_of_run_id"
    )
    assert replay_check["result"] == "n/a"


def test_replay_run_without_replay_of_run_id_is_blocked() -> None:
    identity = {**_PASSING_IDENTITY, "exact_replay": True}
    projection = project_selected_run_replay_readiness(
        identity=identity,
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == BLOCKED
    assert "replay_of_run_id" in projection["blockers"]


def test_unsupported_family_is_not_ready() -> None:
    identity = {**_PASSING_IDENTITY, "replay_capability": "rebuild_only"}
    projection = project_selected_run_replay_readiness(
        identity=identity,
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == UNSUPPORTED


def test_unfinished_run_is_not_ready() -> None:
    identity = {**_PASSING_IDENTITY, "status": "running"}
    projection = project_selected_run_replay_readiness(
        identity=identity,
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == BLOCKED
