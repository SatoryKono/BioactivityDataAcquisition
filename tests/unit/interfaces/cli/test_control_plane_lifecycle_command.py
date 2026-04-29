"""Unit tests for control-plane lifecycle maintenance CLI."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleApplyResult,
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
)
from bioetl.interfaces.cli.main import cli

CONTROL_PLANE_MANIFEST_PATH = "reports/control/run_manifest/manifest-old.json"


def _plan(*, dry_run: bool) -> ControlPlaneArtifactLifecyclePlan:
    generated_at = datetime(2026, 4, 22, tzinfo=UTC)
    return ControlPlaneArtifactLifecyclePlan(
        generated_at=generated_at,
        cutoff=generated_at - timedelta(days=90),
        dry_run=dry_run,
        artifacts=(
            ControlPlaneArtifactRef(
                surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
                path=CONTROL_PLANE_MANIFEST_PATH,
                artifact_id="manifest-old",
                decision=ControlPlaneArtifactLifecycleDecision.DELETE,
                reason="retention_expired",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        ),
    )


def test_control_plane_lifecycle_defaults_to_dry_run() -> None:
    runner = CliRunner()
    plan = _plan(dry_run=True)
    store = MagicMock()
    store.plan.return_value = plan
    store.apply.return_value = ControlPlaneArtifactLifecycleApplyResult(
        plan=plan,
        deleted_paths=(),
    )

    with patch(
        "bioetl.interfaces.cli.commands.domains.maintenance.control_plane_lifecycle.bootstrap_control_plane_lifecycle_store",
        return_value=store,
    ):
        result = runner.invoke(cli, ["maintenance", "control-plane-lifecycle"])

    assert result.exit_code == 0, result.output
    assert "[DRY-RUN]" in result.output
    assert "Would delete 1 artifacts" in result.output
    assert "replay_impact=no_replay_evidence" in result.output
    store.plan.assert_called_once()
    policy = store.plan.call_args.args[0]
    assert policy.retention_days == 90
    assert policy.allow_profile_floor_violation is False
    assert store.plan.call_args.kwargs == {"dry_run": True}


def test_control_plane_lifecycle_apply_json_outputs_deleted_paths() -> None:
    runner = CliRunner()
    plan = _plan(dry_run=False)
    store = MagicMock()
    store.plan.return_value = plan
    store.apply.return_value = ControlPlaneArtifactLifecycleApplyResult(
        plan=plan,
        deleted_paths=(CONTROL_PLANE_MANIFEST_PATH,),
    )

    with patch(
        "bioetl.interfaces.cli.commands.domains.maintenance.control_plane_lifecycle.bootstrap_control_plane_lifecycle_store",
        return_value=store,
    ):
        result = runner.invoke(
            cli,
            [
                "maintenance",
                "control-plane-lifecycle",
                "--apply",
                "--format",
                "json",
                "--protected-run-id",
                "run-1",
                "--protected-snapshot-id",
                "sha256:abc",
                "--allow-profile-floor-violation",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["dry_run"] is False
    assert payload["deleted_paths"] == [CONTROL_PLANE_MANIFEST_PATH]
    assert payload["artifacts"][0]["replay_impact"] == "no_replay_evidence"
    policy = store.plan.call_args.args[0]
    assert policy.protected_run_ids == frozenset({"run-1"})
    assert policy.protected_input_snapshot_ids == frozenset({"sha256:abc"})
    assert policy.allow_profile_floor_violation is True
    assert store.plan.call_args.kwargs == {"dry_run": False}


def test_control_plane_lifecycle_uses_sanctioned_now(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    plan = _plan(dry_run=True)
    store = MagicMock()
    store.plan.return_value = plan
    store.apply.return_value = ControlPlaneArtifactLifecycleApplyResult(
        plan=plan,
        deleted_paths=(),
    )
    fixed_now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "bioetl.interfaces.cli.commands.domains.maintenance.control_plane_lifecycle.current_utc_time",
        lambda: fixed_now,
    )

    with patch(
        "bioetl.interfaces.cli.commands.domains.maintenance.control_plane_lifecycle.bootstrap_control_plane_lifecycle_store",
        return_value=store,
    ):
        result = runner.invoke(cli, ["maintenance", "control-plane-lifecycle"])

    assert result.exit_code == 0, result.output
    policy = store.plan.call_args.args[0]
    assert policy.now == fixed_now
