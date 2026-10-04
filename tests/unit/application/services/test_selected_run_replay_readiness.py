"""Selected-run exact replay readiness does not treat capability as READY."""

from __future__ import annotations

import pytest

from bioetl.application.services.control_plane.manifest.diagnostics.selected_run_replay_readiness import (
    BLOCKED,
    INSUFFICIENT,
    READY,
    UNSUPPORTED,
    project_selected_run_replay_readiness,
)

pytestmark = pytest.mark.unit

_PASSING_IDENTITY = {
    "pipeline_name": "chembl_activity",
    "run_id": "run-a",
    "status": "success",
    "run_type": "full",
}
_PASSING_MANIFEST = {
    "replay_capability": "exact_replay_supported",
    "exact_replay_supported": True,
    "effective_config_hash": "abc",
    "dependency_lock_hash": "def",
    "input_snapshot_fingerprint": "ghi",
    "objects": {
        "effective_config_hash": True,
        "dependency_lock_hash": True,
        "input_snapshot_fingerprint": True,
    },
}


def _pass_probe() -> dict[str, str]:
    return {
        "code": "input_snapshot",
        "result": "pass",
        "reason": "digest_matches",
        "evidence_ref": "#/artifacts/0",
    }


def test_capability_without_artifact_inventory_is_not_ready() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        manifest=_PASSING_MANIFEST,
    )
    assert projection["verdict"] == INSUFFICIENT
    assert projection["unknown_checks"] == ["artifact_inventory"]


def test_report_without_manifest_is_insufficient() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == INSUFFICIENT
    assert projection["unknown_checks"] == ["manifest_not_recorded"]
    assert "effective_config_hash" not in projection["unknown_checks"]


def test_missing_artifact_blocks_even_when_capability_is_exact() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        inventory_present=True,
        manifest=_PASSING_MANIFEST,
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
        manifest={
            **_PASSING_MANIFEST,
            "objects": {"effective_config_hash": False},
        },
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == BLOCKED


def test_hash_without_recorded_verification_is_unknown() -> None:
    manifest = dict(_PASSING_MANIFEST)
    _ = manifest.pop("objects", None)
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        inventory_present=True,
        manifest=manifest,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == INSUFFICIENT
    checks = {item["code"]: item for item in projection["checks"]}
    assert checks["effective_config_hash"]["result"] == "unknown"
    assert checks["effective_config_hash"]["reason"] == "object_not_verified"


def test_source_run_without_replay_of_run_id_can_be_ready() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        manifest=_PASSING_MANIFEST,
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
        manifest=_PASSING_MANIFEST,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == BLOCKED
    assert "replay_of_run_id" in projection["blockers"]


def test_rebuild_only_inside_family_boundary_is_insufficient() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        manifest={**_PASSING_MANIFEST, "replay_capability": "rebuild_only"},
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == INSUFFICIENT
    family = next(
        item for item in projection["checks"] if item["code"] == "exact_replay_family"
    )
    assert family["result"] == "unknown"
    assert family["reason"] == "run_missing_input_snapshots"
    assert "family_outside_supported_exact_replay_boundary" not in family["reason"]


def test_unsupported_family_is_not_ready() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        manifest={
            **_PASSING_MANIFEST,
            "replay_capability": "rebuild_only",
            "exact_replay_supported": False,
        },
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == UNSUPPORTED
    family = next(
        item for item in projection["checks"] if item["code"] == "exact_replay_family"
    )
    assert family["result"] == "fail"
    assert family["reason"] == "family_outside_supported_exact_replay_boundary"


def test_unfinished_run_is_not_ready() -> None:
    identity = {**_PASSING_IDENTITY, "status": "running"}
    projection = project_selected_run_replay_readiness(
        identity=identity,
        manifest=_PASSING_MANIFEST,
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == BLOCKED


def test_replay_with_a_recorded_run_anchor_can_be_ready() -> None:
    projection = project_selected_run_replay_readiness(
        identity={
            **_PASSING_IDENTITY,
            "exact_replay": True,
            "replay_of_run_id": "source",
        },
        manifest=_PASSING_MANIFEST,
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == READY
    anchor = next(c for c in projection["checks"] if c["code"] == "replay_of_run_id")
    assert anchor["result"] == "pass"
    assert anchor["reason"] == "replay_anchor_present"


def test_unknown_terminal_state_is_insufficient_even_with_verified_artifacts() -> None:
    projection = project_selected_run_replay_readiness(
        identity={**_PASSING_IDENTITY, "status": "unrecognized"},
        manifest=_PASSING_MANIFEST,
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == INSUFFICIENT
    assert projection["unknown_checks"] == ["terminal_status"]


def test_present_but_empty_artifact_inventory_cannot_be_ready() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        manifest=_PASSING_MANIFEST,
        inventory_present=True,
    )
    assert projection["verdict"] == INSUFFICIENT
    assert projection["unknown_checks"] == ["artifact_inventory"]
    assert projection["checks"][-1]["reason"] == "artifact_inventory_empty"


@pytest.mark.parametrize("flag,expected", [("yes", READY), ("0", UNSUPPORTED)])
def test_legacy_family_support_tokens_retain_their_recorded_meaning(
    flag: str, expected: str
) -> None:
    manifest = {**_PASSING_MANIFEST, "strict_exact_replay_supported": flag}
    del manifest["exact_replay_supported"]
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        manifest=manifest,
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == expected


def test_unknown_capability_remains_insufficient() -> None:
    projection = project_selected_run_replay_readiness(
        identity=_PASSING_IDENTITY,
        manifest={**_PASSING_MANIFEST, "replay_capability": "unrecognized"},
        inventory_present=True,
        artifact_probes=(_pass_probe(),),
    )
    assert projection["verdict"] == INSUFFICIENT
    assert projection["unknown_checks"] == ["exact_replay_family"]
