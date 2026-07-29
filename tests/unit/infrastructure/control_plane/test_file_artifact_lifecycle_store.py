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
"""Unit tests for file-backed control-plane artifact lifecycle planning."""

from __future__ import annotations

import pytest

import json
import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePolicy,
    ControlPlaneArtifactReplayImpact,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)


pytestmark = pytest.mark.unit


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_text(path: Path, payload: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


def _write_bytes(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _set_mtime(path: Path, timestamp: datetime) -> None:
    os.utime(path, (timestamp.timestamp(), timestamp.timestamp()))


def test_lifecycle_plan_is_dry_run_and_retains_protected_references(
    tmp_path: Path,
) -> None:
    control_root = tmp_path / "control"
    now = datetime(2026, 4, 22, tzinfo=UTC)
    old = datetime(2026, 1, 1, tzinfo=UTC)
    cached_bronze_bytes = b"snapshot bytes"
    cached_bronze_snapshot_id = (
        f"sha256:{hashlib.sha256(cached_bronze_bytes).hexdigest()}"
    )
    _write_json(
        control_root / "run_manifest" / "manifest-live.json",
        {
            "created_at": now.isoformat(),
            "manifest_id": "manifest-live",
            "run_id": "run-live",
            "code_provenance": {
                "effective_config_artifact_id": "effective-config-live"
            },
            "source_refs": [
                {
                    "input_snapshots": [
                        {
                            "snapshot_id": cached_bronze_snapshot_id,
                            "content_hash": cached_bronze_snapshot_id.removeprefix(
                                "sha256:"
                            ),
                        }
                    ]
                }
            ],
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
    checkpoint_path = _write_json(
        control_root.parent / "checkpoints" / "chembl_activity.json",
        {
            "created_at": now.isoformat(),
            "run_id": "run-live",
            "metadata": {
                "manifest_id": "manifest-live",
                "effective_config_artifact_id": "effective-config-live",
            },
        },
    )
    cached_bronze_path = _write_bytes(
        control_root.parent
        / "bronze"
        / "2026-04-01"
        / "batch_2026-04-01_chembl_activity.jsonl.zst",
        cached_bronze_bytes,
    )
    for path in (
        live_ledger,
        stale_effective_config,
        protected_effective_config,
        protected_occurrence,
        protected_lineage,
        checkpoint_path,
        cached_bronze_path,
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
    assert by_path["manifest-live.json"].replay_impact is (
        ControlPlaneArtifactReplayImpact.RECOVERY_EVIDENCE_PROTECTED
    )
    assert by_path["manifest-stale.json"].decision is (
        ControlPlaneArtifactLifecycleDecision.DELETE
    )
    assert by_path["manifest-stale.json"].replay_impact is (
        ControlPlaneArtifactReplayImpact.UNPROTECTED_REPLAY_EVIDENCE_DELETE_CANDIDATE
    )
    assert by_path["manifest-live.jsonl"].reason == "protected_reference"
    assert by_path["effective-config-live.json"].reason == "protected_reference"
    assert by_path["run-live.json"].reason == "protected_reference"
    assert by_path["fragment-live.json"].reason == "protected_reference"
    assert by_path["chembl_activity.json"].reason == "protected_reference"
    assert (
        by_path["batch_2026-04-01_chembl_activity.jsonl.zst"].reason
        == "protected_reference"
    )
    assert by_path["effective-config-stale.json"].decision is (
        ControlPlaneArtifactLifecycleDecision.DELETE
    )

    result = store.apply(plan)

    assert result.deleted_paths == ()
    assert stale_manifest.exists()
    assert stale_effective_config.exists()


def test_lifecycle_retains_stale_replay_ready_evidence_floor_refs(
    tmp_path: Path,
) -> None:
    control_root = tmp_path / "control"
    now = datetime(2026, 4, 22, tzinfo=UTC)
    old = datetime(2026, 1, 1, tzinfo=UTC)
    cached_bronze_bytes = b"replay-ready snapshot bytes"
    cached_bronze_snapshot_id = (
        f"sha256:{hashlib.sha256(cached_bronze_bytes).hexdigest()}"
    )
    stale_manifest = _write_json(
        control_root / "run_manifest" / "manifest-replay-ready.json",
        {
            "created_at": old.isoformat(),
            "manifest_id": "manifest-replay-ready",
            "run_id": "run-replay-ready",
            "launch_context": {"required_persistence_profile": "replay_ready"},
            "code_provenance": {
                "effective_config_artifact_id": "effective-config-floor"
            },
            "source_refs": [
                {
                    "input_snapshots": [
                        {
                            "snapshot_id": cached_bronze_snapshot_id,
                            "content_hash": cached_bronze_snapshot_id.removeprefix(
                                "sha256:"
                            ),
                        }
                    ]
                }
            ],
        },
    )
    stale_ledger = _write_text(
        control_root / "run_ledger" / "manifest-replay-ready.jsonl",
        json.dumps(
            {
                "occurred_at": old.isoformat(),
                "manifest_id": "manifest-replay-ready",
                "run_id": "run-replay-ready",
            },
            sort_keys=True,
        )
        + "\n",
    )
    stale_effective_config = _write_json(
        control_root / "effective_config" / "effective-config-floor.json",
        {"artifact_id": "effective-config-floor"},
    )
    stale_lineage = _write_json(
        control_root / "lineage" / "fragments" / "fragment-floor.json",
        {
            "stored_fragment_id": "fragment-floor",
            "run_id": "run-replay-ready",
            "manifest_id": "manifest-replay-ready",
        },
    )
    stale_checkpoint = _write_json(
        control_root.parent / "checkpoints" / "chembl_activity.json",
        {
            "created_at": old.isoformat(),
            "metadata": {
                "run_id": "run-replay-ready",
                "manifest_id": "manifest-replay-ready",
                "effective_config_artifact_id": "effective-config-floor",
            },
        },
    )
    stale_cached_bronze = _write_bytes(
        control_root.parent / "bronze" / "batch.jsonl.zst",
        cached_bronze_bytes,
    )
    unrelated_manifest = _write_json(
        control_root / "run_manifest" / "manifest-unrelated.json",
        {
            "created_at": old.isoformat(),
            "manifest_id": "manifest-unrelated",
            "run_id": "run-unrelated",
        },
    )
    for path in (
        stale_manifest,
        stale_ledger,
        stale_effective_config,
        stale_lineage,
        stale_checkpoint,
        stale_cached_bronze,
        unrelated_manifest,
    ):
        _set_mtime(path, old)

    store = FileControlPlaneArtifactLifecycleStore(base_path=control_root)
    plan = store.plan(
        ControlPlaneArtifactLifecyclePolicy(retention_days=30, now=now),
        dry_run=True,
    )

    by_name = {Path(artifact.path).name: artifact for artifact in plan.artifacts}
    retained_names = (
        "manifest-replay-ready.json",
        "manifest-replay-ready.jsonl",
        "effective-config-floor.json",
        "fragment-floor.json",
        "chembl_activity.json",
        "batch.jsonl.zst",
    )
    for name in retained_names:
        assert by_name[name].decision is ControlPlaneArtifactLifecycleDecision.RETAIN
        assert by_name[name].reason == "reproducibility_evidence_floor"
        assert by_name[name].replay_impact is (
            ControlPlaneArtifactReplayImpact.STRICT_REPLAY_EVIDENCE_PROTECTED
        )
        assert any(
            reason.startswith("evidence_floor:")
            for reason in by_name[name].protected_by
        )
    assert by_name["manifest-unrelated.json"].decision is (
        ControlPlaneArtifactLifecycleDecision.DELETE
    )
    assert by_name["manifest-unrelated.json"].replay_impact is (
        ControlPlaneArtifactReplayImpact.UNPROTECTED_REPLAY_EVIDENCE_DELETE_CANDIDATE
    )


def test_lifecycle_profile_floor_override_allows_stale_replay_ready_deletion(
    tmp_path: Path,
) -> None:
    control_root = tmp_path / "control"
    now = datetime(2026, 4, 22, tzinfo=UTC)
    old = datetime(2026, 1, 1, tzinfo=UTC)
    stale_manifest = _write_json(
        control_root / "run_manifest" / "manifest-replay-ready.json",
        {
            "created_at": old.isoformat(),
            "manifest_id": "manifest-replay-ready",
            "run_id": "run-replay-ready",
            "launch_context": {"required_persistence_profile": "replay_ready"},
        },
    )
    _set_mtime(stale_manifest, old)

    store = FileControlPlaneArtifactLifecycleStore(base_path=control_root)
    plan = store.plan(
        ControlPlaneArtifactLifecyclePolicy(
            retention_days=30,
            now=now,
            allow_profile_floor_violation=True,
        ),
        dry_run=True,
    )

    by_name = {Path(artifact.path).name: artifact for artifact in plan.artifacts}
    assert by_name["manifest-replay-ready.json"].decision is (
        ControlPlaneArtifactLifecycleDecision.DELETE
    )
    assert by_name["manifest-replay-ready.json"].reason == "retention_expired"


def test_lifecycle_retains_stale_replay_supported_family_evidence_floor(
    tmp_path: Path,
) -> None:
    control_root = tmp_path / "control"
    now = datetime(2026, 4, 22, tzinfo=UTC)
    old = datetime(2026, 1, 1, tzinfo=UTC)
    cached_bronze_bytes = b"historical-certified-family snapshot bytes"
    cached_bronze_snapshot_id = (
        f"sha256:{hashlib.sha256(cached_bronze_bytes).hexdigest()}"
    )
    stale_manifest = _write_json(
        control_root / "run_manifest" / "manifest-supported-family.json",
        {
            "created_at": old.isoformat(),
            "manifest_id": "manifest-supported-family",
            "run_id": "run-supported-family",
            "pipeline_name": "pubmed_publication",
            "provider": "pubmed",
            "entity": "publication",
            "launch_context": {"execution_context": "source"},
            "code_provenance": {
                "contract_ref": "pubmed.publication",
                "effective_config_artifact_id": "effective-config-supported-family",
            },
            "source_refs": [
                {
                    "provider": "pubmed",
                    "entity": "publication",
                    "pipeline_name": "pubmed_publication",
                    "input_snapshots": [
                        {
                            "snapshot_id": cached_bronze_snapshot_id,
                            "content_hash": cached_bronze_snapshot_id.removeprefix(
                                "sha256:"
                            ),
                        }
                    ],
                }
            ],
        },
    )
    stale_ledger = _write_text(
        control_root / "run_ledger" / "manifest-supported-family.jsonl",
        json.dumps(
            {
                "occurred_at": old.isoformat(),
                "manifest_id": "manifest-supported-family",
                "run_id": "run-supported-family",
            },
            sort_keys=True,
        )
        + "\n",
    )
    stale_effective_config = _write_json(
        control_root / "effective_config" / "effective-config-supported-family.json",
        {"artifact_id": "effective-config-supported-family"},
    )
    stale_lineage = _write_json(
        control_root / "lineage" / "fragments" / "fragment-supported-family.json",
        {
            "stored_fragment_id": "fragment-supported-family",
            "run_id": "run-supported-family",
            "manifest_id": "manifest-supported-family",
        },
    )
    stale_checkpoint = _write_json(
        control_root.parent / "checkpoints" / "pubmed_publication.json",
        {
            "created_at": old.isoformat(),
            "metadata": {
                "run_id": "run-supported-family",
                "manifest_id": "manifest-supported-family",
                "effective_config_artifact_id": "effective-config-supported-family",
            },
        },
    )
    stale_cached_bronze = _write_bytes(
        control_root.parent / "bronze" / "pubmed_publication.jsonl.zst",
        cached_bronze_bytes,
    )
    for path in (
        stale_manifest,
        stale_ledger,
        stale_effective_config,
        stale_lineage,
        stale_checkpoint,
        stale_cached_bronze,
    ):
        _set_mtime(path, old)

    store = FileControlPlaneArtifactLifecycleStore(base_path=control_root)
    plan = store.plan(
        ControlPlaneArtifactLifecyclePolicy(retention_days=30, now=now),
        dry_run=True,
    )

    by_name = {Path(artifact.path).name: artifact for artifact in plan.artifacts}
    retained_names = (
        "manifest-supported-family.json",
        "manifest-supported-family.jsonl",
        "effective-config-supported-family.json",
        "fragment-supported-family.json",
        "pubmed_publication.json",
        "pubmed_publication.jsonl.zst",
    )
    for name in retained_names:
        assert by_name[name].decision is ControlPlaneArtifactLifecycleDecision.RETAIN
        assert by_name[name].reason == "reproducibility_evidence_floor"
        assert any(
            reason.startswith("evidence_floor:")
            for reason in by_name[name].protected_by
        )


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

    logger = MagicMock()
    metrics = MagicMock()
    store = FileControlPlaneArtifactLifecycleStore(
        base_path=control_root,
        logger=logger,
        metrics=metrics,
    )
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
    logger.info.assert_any_call(
        "control_plane_lifecycle_artifact_deleted",
        surface="run_manifest",
        artifact_id="manifest-stale",
        path=str(stale_manifest),
        reason="retention_expired",
        replay_impact="unprotected_replay_evidence_delete_candidate",
    )
    metrics.increment_counter.assert_any_call(
        "bioetl_control_plane_lifecycle_deleted_total",
        1,
        labels={
            "surface": "run_manifest",
            "replay_impact": "unprotected_replay_evidence_delete_candidate",
        },
    )
    metrics.set_gauge.assert_called_once_with(
        "bioetl_control_plane_lifecycle_delete_candidates",
        1.0,
    )
    metrics.increment_counter.assert_any_call(
        "bioetl_control_plane_lifecycle_apply_total",
        1,
        labels={"dry_run": "false"},
    )
    logger.info.assert_any_call(
        "control_plane_lifecycle_apply_summary",
        dry_run=False,
        cutoff=plan.cutoff.isoformat(),
        delete_count=1,
        retain_count=1,
        deleted_count=1,
        missing_count=0,
    )


def test_lifecycle_dry_run_emits_summary_metrics_without_deletions(
    tmp_path: Path,
) -> None:
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

    logger = MagicMock()
    metrics = MagicMock()
    store = FileControlPlaneArtifactLifecycleStore(
        base_path=control_root,
        logger=logger,
        metrics=metrics,
    )
    plan = store.plan(
        ControlPlaneArtifactLifecyclePolicy(retention_days=30, now=now),
        dry_run=True,
    )

    result = store.apply(plan)

    assert result.deleted_paths == ()
    assert stale_manifest.exists()
    metrics.set_gauge.assert_called_once_with(
        "bioetl_control_plane_lifecycle_delete_candidates",
        1.0,
    )
    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_lifecycle_apply_total",
        1,
        labels={"dry_run": "true"},
    )
    logger.info.assert_called_once_with(
        "control_plane_lifecycle_apply_summary",
        dry_run=True,
        cutoff=plan.cutoff.isoformat(),
        delete_count=1,
        retain_count=0,
        deleted_count=0,
        missing_count=0,
    )
