"""Campaign determinism gate for tracked fixture control-plane replay."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import pytest

from tests.helpers.control_plane_replay import (
    build_tracked_fixture_exact_replay_matrix_payload,
)
from tests.integration._consolidation_suite_support import (
    run_tracked_fixture_replay_pair,
)

_PIPELINE_NAME = "chembl_activity"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.no_api,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        "microsoft" in platform.release().lower(),
        reason="Skipped on WSL due to asyncio teardown on cloud-mounted storage",
    ),
]


def _stable_manifest_payload(payload: dict) -> dict:
    """Extract replay-relevant stable fields for deterministic comparison."""
    return {
        "execution_fingerprint": payload.get("execution_fingerprint"),
        "provider": payload.get("provider"),
        "entity": payload.get("entity"),
        "replay_capability": payload.get("replay_capability"),
        "launch_context": {
            key: payload.get("launch_context", {}).get(key)
            for key in (
                "exact_replay",
                "execution_context",
                "required_persistence_profile",
            )
        },
        "runtime_config": {
            key: payload.get("runtime_config", {}).get(key)
            for key in (
                "exact_replay",
                "execution_context",
                "required_persistence_profile",
            )
        },
        "code_provenance": {
            "contract_ref": payload["code_provenance"]["contract_ref"],
            "config_hash": payload["code_provenance"]["config_hash"],
            "effective_config_artifact_id": payload["code_provenance"][
                "effective_config_artifact_id"
            ],
            "dq_contract_compatibility_hash": payload["code_provenance"][
                "dq_contract_compatibility_hash"
            ],
        },
        "source_refs": payload["source_refs"],
    }


def _canonical_manifest_fingerprint(payload: dict) -> str:
    normalized = _stable_manifest_payload(payload)
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@pytest.mark.asyncio
async def test_consolidation_determinism_replay_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        first_manifest,
        second_manifest,
        first_effective,
        second_effective,
        first_run_id,
        second_run_id,
    ) = await run_tracked_fixture_replay_pair(
        tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert first_manifest["run_id"] != second_manifest["run_id"]
    assert first_manifest["manifest_id"] != second_manifest["manifest_id"]
    assert first_manifest["manifest_id"] != ""
    assert second_manifest["manifest_id"] != ""

    assert first_manifest["replay_capability"] == "exact_replay_supported"
    assert second_manifest["replay_capability"] == "exact_replay_supported"
    assert (
        first_manifest["execution_fingerprint"]
        == second_manifest["execution_fingerprint"]
    )
    assert first_manifest["launch_context"]["exact_replay"] is True
    assert second_manifest["launch_context"]["exact_replay"] is True

    source_refs_first = first_manifest.get("source_refs")
    source_refs_second = second_manifest.get("source_refs")
    assert isinstance(source_refs_first, list) and source_refs_first
    assert isinstance(source_refs_second, list) and source_refs_second
    assert source_refs_first == source_refs_second

    assert (
        first_manifest["code_provenance"]["effective_config_artifact_id"]
        == second_manifest["code_provenance"]["effective_config_artifact_id"]
    )
    assert (
        first_manifest["code_provenance"]["config_hash"]
        == second_manifest["code_provenance"]["config_hash"]
    )
    assert (
        first_manifest["code_provenance"]["dq_contract_compatibility_hash"]
        == second_manifest["code_provenance"]["dq_contract_compatibility_hash"]
    )
    assert _canonical_manifest_fingerprint(
        first_manifest
    ) == _canonical_manifest_fingerprint(second_manifest)
    assert first_effective["artifact_id"] == second_effective["artifact_id"]

    evidence_dir = tmp_path / "reports" / "reproducibility"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "tracked_fixture_determinism.json"
    evidence_path.write_text(
        json.dumps(
            {
                "pipeline_name": _PIPELINE_NAME,
                "case": "tracked_fixture_determinism_gate",
                "manifest_fingerprint": _canonical_manifest_fingerprint(first_manifest),
                "evidence": build_tracked_fixture_exact_replay_matrix_payload(
                    pipeline_name=_PIPELINE_NAME,
                    manifest_payload=first_manifest,
                    effective_payload=first_effective,
                    occurrences=[
                        {
                            "run_id": first_run_id,
                            "manifest_id": str(first_manifest["manifest_id"]),
                        },
                        {
                            "run_id": second_run_id,
                            "manifest_id": str(second_manifest["manifest_id"]),
                        },
                    ],
                    case_name="tracked_fixture_determinism_gate",
                ),
                "source_snapshot_ids": [
                    snapshot["snapshot_id"]
                    for source_ref in first_manifest["source_refs"]
                    for snapshot in source_ref["input_snapshots"]
                ],
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
