"""Unit tests for file-backed control-plane artifact lifecycle planning."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePolicy,
)
from bioetl.infrastructure.control_plane import FileControlPlaneArtifactLifecycleStore


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_text(path: Path, payload: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


def _set_mtime(path: Path, timestamp: datetime) -> None:
    os.utime(path, (timestamp.timestamp(), timestamp.timestamp()))


def test_lifecycle_plan_is_dry_run_and_retains_protected_references(
    tmp_path: Path,
) -> None:
    control_root = tmp_path / "control"
    now = datetime(2026, 4, 22, tzinfo=UTC)
    old = datetime(2026, 1, 1, tzinfo=UTC)
    _write_json(
        control_root / "run_manifest" / "manifest-live.json",
        {
            "created_at": now.isoformat(),
            "manifest_id": "manifest-live",
            "run_id": "run-live",
            "code_provenance": {
                "effective_config_artifact_id": "effective-config-live"
            },
        },
    )
    stale_manifest = _write_json(
        control_root / "run_manifest" / "manifest-stale.json",
        {
            "created_at": old.isoformat(),
            "manifest_id": "manifest-stale",
            "run_id": "run-stale",
        },
    )
    live_ledger = _write_text(
        control_root / "run_ledger" / "manifest-live.jsonl",
        json.dumps(
            {
                "occurred_at": old.isoformat(),
                "manifest_id": "manifest-live",
                "run_id": "run-live",
            },
            sort_keys=True,
        )
        + "\n",
    )
    stale_effective_config = _write_json(
        control_root / "effective_config" / "effective-config-stale.json",
        {"artifact_id": "effective-config-stale"},
    )
    protected_effective_config = _write_json(
        control_root / "effective_config" / "effective-config-live.json",
        {"artifact_id": "effective-config-live"},
    )
    protected_occurrence = _write_json(
        control_root / "effective_config" / "_occurrences" / "run-live.json",
        {"artifact_id": "effective-config-live", "run_id": "run-live"},
    )
    protected_lineage = _write_json(
        control_root / "lineage" / "fragments" / "fragment-live.json",
        {
            "stored_fragment_id": "fragment-live",
            "fragment_id": "semantic-fragment-live",
            "run_id": "run-live",
            "manifest_id": "manifest-live",
        },
    )
    for path in (
        live_ledger,
        stale_effective_config,
        protected_effective_config,
        protected_occurrence,
        protected_lineage,
    ):
        _set_mtime(path, old)

    store = FileControlPlaneArtifactLifecycleStore(base_path=control_root)
    plan = store.plan(
        ControlPlaneArtifactLifecyclePolicy(retention_days=30, now=now),
        dry_run=True,
    )

    by_path = {Path(artifact.path).name: artifact for artifact in plan.artifacts}
    assert plan.dry_run is True
    assert by_path["manifest-live.json"].decision is (
        ControlPlaneArtifactLifecycleDecision.RETAIN
    )
    assert by_path["manifest-stale.json"].decision is (
        ControlPlaneArtifactLifecycleDecision.DELETE
    )
    assert by_path["manifest-live.jsonl"].reason == "protected_reference"
    assert by_path["effective-config-live.json"].reason == "protected_reference"
    assert by_path["run-live.json"].reason == "protected_reference"
    assert by_path["fragment-live.json"].reason == "protected_reference"
    assert by_path["effective-config-stale.json"].decision is (
        ControlPlaneArtifactLifecycleDecision.DELETE
    )

    result = store.apply(plan)

    assert result.deleted_paths == ()
    assert stale_manifest.exists()
    assert stale_effective_config.exists()


def test_lifecycle_apply_deletes_only_expired_unprotected_files(tmp_path: Path) -> None:
    control_root = tmp_path / "control"
    now = datetime(2026, 4, 22, tzinfo=UTC)
    old = datetime(2026, 1, 1, tzinfo=UTC)
    stale_manifest = _write_json(
        control_root / "run_manifest" / "manifest-stale.json",
        {
            "created_at": old.isoformat(),
            "manifest_id": "manifest-stale",
            "run_id": "run-stale",
        },
    )
    retained_manifest = _write_json(
        control_root / "run_manifest" / "manifest-retained.json",
        {
            "created_at": old.isoformat(),
            "manifest_id": "manifest-retained",
            "run_id": "run-retained",
        },
    )

    store = FileControlPlaneArtifactLifecycleStore(base_path=control_root)
    plan = store.plan(
        ControlPlaneArtifactLifecyclePolicy(
            retention_days=30,
            now=now,
            protected_manifest_ids=frozenset({"manifest-retained"}),
        ),
        dry_run=False,
    )
    result = store.apply(plan)

    assert str(stale_manifest) in result.deleted_paths
    assert not stale_manifest.exists()
    assert retained_manifest.exists()
