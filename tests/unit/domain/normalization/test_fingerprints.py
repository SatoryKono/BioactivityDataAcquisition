"""Tests for canonical control-plane fingerprint contracts."""

from __future__ import annotations

from bioetl.domain.normalization import compute_execution_identity_fingerprint
from bioetl.domain.normalization import compute_degraded_runtime_anchor_fingerprint
from bioetl.domain.normalization import build_execution_identity_payload
from bioetl.domain.normalization import normalize_runtime_anchor_payload
from bioetl.domain.normalization import normalize_control_plane_sha256
from bioetl.domain.normalization import normalize_contract_ref
from bioetl.domain.normalization import normalize_contract_version


def _build_payload() -> dict[str, str | None]:
    return build_execution_identity_payload(
        pipeline_name="chembl_activity",
        run_type="incremental",
        pipeline_version=None,
        effective_config_hash=normalize_control_plane_sha256("a" * 64),
        dq_contract_compatibility_hash=None,
        contract_ref=normalize_contract_ref(" ChemBL.Activity "),
        contract_version=normalize_contract_version(" v2 "),
        effective_config_artifact_id=None,
        exact_replay=False,
        input_snapshot_fingerprint=(
            "b9b909fbc69f111484ed86aa0d8ec6f6390b76739145b2b2d6404fa17f6e05f8"
        ),
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
        "run_type": payload["run_type"],
        "pipeline_name": payload["pipeline_name"],
    }

    assert compute_execution_identity_fingerprint(
        payload
    ) == compute_execution_identity_fingerprint(reordered)


def test_execution_identity_fingerprint_matches_golden_value() -> None:
    payload = _build_payload()

    assert (
        compute_execution_identity_fingerprint(payload)
        == "ab7bface86b238e30828761b54e0423d890d7ca1c9c15e630f0ba668bb6d7677"
    )


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

    assert compute_degraded_runtime_anchor_fingerprint(
        normalize_runtime_anchor_payload(payload)
    ) == compute_degraded_runtime_anchor_fingerprint(
        normalize_runtime_anchor_payload(reordered)
    )
