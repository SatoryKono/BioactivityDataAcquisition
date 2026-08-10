"""Profile matrix against the production file-backed lifecycle planner."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.evidence import (
    ControlPlaneEvidenceService,
    EvidenceScope,
)
from bioetl.domain.control_plane import (
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import (
    FileControlPlaneArtifactLifecycleStore,
)

pytestmark = pytest.mark.integration

_NOW = datetime(2026, 8, 9, tzinfo=UTC)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _manifest(
    profile: str,
    *,
    snapshot_payloads: tuple[bytes, ...] | None = None,
) -> RunManifest:
    suffix = {
        "degraded_observable": 84930,
        "replay_ready": 84931,
        "forensic_grade": 84932,
    }[profile]
    run_id = RunID(UUID(f"00000000-0000-0000-0000-{suffix:012d}"))
    source_refs: tuple[RunSourceRef, ...] = ()
    if profile != "degraded_observable":
        payloads = snapshot_payloads or (profile.encode(),)
        snapshots = tuple(
            RunInputSnapshotRef(
                snapshot_id=f"sha256:{hashlib.sha256(payload).hexdigest()}",
                content_hash=hashlib.sha256(payload).hexdigest(),
            )
            for payload in payloads
        )
        source_refs = (
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                input_snapshots=snapshots,
            ),
        )
    return RunManifest(
        manifest_id=f"manifest-{profile}",
        execution_fingerprint=f"fingerprint-{profile}",
        created_at=_NOW,
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"required_persistence_profile": profile},
        code_provenance=RunCodeProvenance(
            effective_config_artifact_id=f"effective-config-{profile}"
        ),
        source_refs=source_refs,
    )


def _persist_profile_evidence(
    control_root: Path,
    manifest: RunManifest,
    *,
    observed_snapshot_payloads: tuple[bytes, ...] | None = None,
) -> None:
    _write_json(
        control_root / "run_manifest" / f"{manifest.manifest_id}.json",
        manifest.to_dict(),
    )
    profile = str(manifest.launch_context["required_persistence_profile"])
    if profile == "degraded_observable":
        return
    _write_json(
        control_root / "effective_config" / f"effective-config-{profile}.json",
        {"artifact_id": f"effective-config-{profile}"},
    )
    payloads = observed_snapshot_payloads or (profile.encode(),)
    for index, payload in enumerate(payloads):
        snapshot_path = control_root.parent / "bronze" / f"{profile}-{index}.zst"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_bytes(payload)
    if profile != "forensic_grade":
        return
    ledger_path = control_root / "run_ledger" / f"{manifest.manifest_id}.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(
            {
                "manifest_id": manifest.manifest_id,
                "run_id": str(manifest.run_id),
                "occurred_at": _NOW.isoformat(),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        control_root / "lineage" / "fragments" / "fragment-forensic.json",
        {
            "stored_fragment_id": "fragment-forensic",
            "fragment_id": "fragment-forensic",
            "manifest_id": manifest.manifest_id,
            "run_id": str(manifest.run_id),
        },
    )


def _scope(manifest: RunManifest) -> EvidenceScope:
    return EvidenceScope(
        requested_pipeline=manifest.pipeline_name,
        selected_run_id=str(manifest.run_id),
        selected_run_types=(manifest.run_type.value,),
        resolved_via="selected_run_id",
        manifest=manifest,
    )


def _rows(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    rows = cast("list[dict[str, object]]", payload["rows"])
    return {str(row["check"]): row for row in rows}


@pytest.mark.parametrize(
    "profile",
    ("degraded_observable", "replay_ready", "forensic_grade"),
)
def test_retention_profile_matrix_uses_production_planner(
    tmp_path: Path,
    profile: str,
) -> None:
    control_root = tmp_path / "control"
    manifest = _manifest(profile)
    _persist_profile_evidence(control_root, manifest)
    service = ControlPlaneEvidenceService(
        lifecycle_planner=FileControlPlaneArtifactLifecycleStore(control_root)
    )

    payload = service.retention_compliance(scope=_scope(manifest), now=_NOW)

    rows = _rows(payload)
    assert rows["retention_policy"]["status"] == "OK"
    assert rows["required_evidence"]["status"] == "OK"
    assert rows["evidence_floor"]["status"] == "OK"
    assert rows["snapshot_evidence"]["status"] == "OK"
    expected_snapshot_reason = (
        "snapshot_evidence_not_required"
        if profile == "degraded_observable"
        else "snapshot_lifecycle_evidence_present"
    )
    assert rows["snapshot_evidence"]["reason"] == expected_snapshot_reason


@pytest.mark.parametrize(
    ("observed_count", "expected_status", "expected_reason"),
    (
        (1, "UNKNOWN", "snapshot_lifecycle_evidence_incomplete"),
        (2, "OK", "snapshot_lifecycle_evidence_present"),
    ),
)
def test_retention_requires_every_manifested_snapshot_in_lifecycle_plan(
    tmp_path: Path,
    observed_count: int,
    expected_status: str,
    expected_reason: str,
) -> None:
    snapshot_payloads = (b"snapshot-a", b"snapshot-b")
    manifest = _manifest("replay_ready", snapshot_payloads=snapshot_payloads)
    control_root = tmp_path / "control"
    _persist_profile_evidence(
        control_root,
        manifest,
        observed_snapshot_payloads=snapshot_payloads[:observed_count],
    )
    service = ControlPlaneEvidenceService(
        lifecycle_planner=FileControlPlaneArtifactLifecycleStore(control_root)
    )

    payload = service.retention_compliance(scope=_scope(manifest), now=_NOW)

    snapshot_row = _rows(payload)["snapshot_evidence"]
    assert snapshot_row["status"] == expected_status
    assert snapshot_row["reason"] == expected_reason
    if observed_count == 1:
        assert snapshot_row["detail"] == (
            "Missing cached snapshot lifecycle evidence count: 1."
        )
        assert "sha256:" not in str(snapshot_row)
