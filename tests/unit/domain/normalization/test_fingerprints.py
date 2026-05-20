"""Tests for canonical control-plane fingerprint contracts."""

from __future__ import annotations

from bioetl.domain.normalization import build_execution_identity_payload
from bioetl.domain.normalization import compute_execution_identity_fingerprint
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.domain.normalization import normalize_runtime_anchor_payload
from bioetl.domain.normalization import normalize_contract_ref
from bioetl.domain.normalization import normalize_contract_version
from bioetl.domain.normalization import normalize_control_plane_sha256


def _build_payload() -> dict[str, str | None]:
    return build_execution_identity_payload(
        pipeline_name="chembl_activity",
        run_type="incremental",
        pipeline_version=None,
        git_commit="abc1234",
        effective_config_hash=normalize_control_plane_sha256("a" * 64),
        dq_contract_compatibility_hash=None,
        contract_ref=normalize_contract_ref(" ChemBL.Activity "),
        contract_version=normalize_contract_version(" v2 "),
        normalization_profile_ref=None,
        normalization_profile_version=None,
        normalization_profile_hash=None,
        effective_config_artifact_id=None,
        exact_replay=False,
        input_snapshot_fingerprint=(
            "b9b909fbc69f111484ed86aa0d8ec6f6390b76739145b2b2d6404fa17f6e05f8"
        ),
        silver_filter_compatibility_mode="structural_only_auto_promote",
    )


def test_execution_identity_fingerprint_is_deterministic_for_equivalent_payloads() -> (
    None
):
    payload = _build_payload()
    reordered = {
        "input_snapshot_fingerprint": payload["input_snapshot_fingerprint"],
        "exact_replay": payload["exact_replay"],
        "effective_config_artifact_id": payload["effective_config_artifact_id"],
        "contract_version": payload["contract_version"],
        "contract_ref": payload["contract_ref"],
        "dq_contract_compatibility_hash": payload["dq_contract_compatibility_hash"],
        "effective_config_hash": payload["effective_config_hash"],
        "pipeline_version": payload["pipeline_version"],
        "git_commit": payload["git_commit"],
        "run_type": payload["run_type"],
        "pipeline_name": payload["pipeline_name"],
        "silver_filter_compatibility_mode": (
            payload["silver_filter_compatibility_mode"]
        ),
    }

    assert compute_execution_identity_fingerprint(
        payload
    ) == compute_execution_identity_fingerprint(reordered)


def test_execution_identity_fingerprint_matches_golden_value() -> None:
    payload = _build_payload()

    assert (
        compute_execution_identity_fingerprint(payload)
        == "cdcc2db1ac5167f3bd769646977da4632d4ecf02729a521b53ad96d5b2a843fd"
    )


def test_execution_identity_fingerprint_changes_when_silver_mode_changes() -> None:
    payload = _build_payload()
    changed = dict(payload)
    changed["silver_filter_compatibility_mode"] = None

    assert compute_execution_identity_fingerprint(
        payload
    ) != compute_execution_identity_fingerprint(changed)


def test_runtime_anchor_fingerprint_is_deterministic_for_equivalent_payloads() -> None:
    payload = {
        "effective_config_hash": " SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ",
        "contract_ref": " ChemBL.Activity ",
        "contract_version": " v2 ",
        "manifest_id": " manifest-123 ",
        "dq_contract_compatibility_hash": " DEADBEEF ",
        "effective_config_artifact_id": " artifact-42 ",
    }
    reordered = {
        "effective_config_artifact_id": "artifact-42",
        "manifest_id": "manifest-123",
        "dq_contract_compatibility_hash": "deadbeef",
        "contract_version": "2.0.0",
        "contract_ref": "chembl.activity",
        "effective_config_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }

    assert compute_execution_identity_fingerprint(
        normalize_runtime_anchor_payload(payload)
    ) == compute_execution_identity_fingerprint(
        normalize_runtime_anchor_payload(reordered)
    )


def test_input_snapshot_identity_fingerprint_is_deterministic_for_equivalent_refs() -> (
    None
):
    first = [
        {
            "snapshot_id": "snapshot-a",
            "content_hash": "sha256:aaa",
            "immutable_uri": "bronze://a",
        },
        {
            "snapshot_id": "snapshot-b",
            "content_hash": "sha256:bbb",
            "immutable_uri": "bronze://b",
        },
    ]
    reordered = [first[1], first[0]]

    assert compute_input_snapshot_identity_fingerprint(
        first
    ) == compute_input_snapshot_identity_fingerprint(reordered)


def test_input_snapshot_identity_fingerprint_drifts_when_content_changes() -> None:
    baseline = [
        {
            "snapshot_id": "snapshot-a",
            "content_hash": "sha256:aaa",
            "immutable_uri": "bronze://a",
        }
    ]
    drifted = [
        {
            "snapshot_id": "snapshot-a",
            "content_hash": "sha256:bbb",
            "immutable_uri": "bronze://a",
        }
    ]

    assert compute_input_snapshot_identity_fingerprint(
        baseline
    ) != compute_input_snapshot_identity_fingerprint(drifted)
