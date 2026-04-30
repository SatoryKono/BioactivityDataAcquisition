"""Integration tests for run-manifest CLI wiring."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from click.testing import CliRunner

from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestDiffEntry,
    RunManifestDiffResult,
    RunManifestInspectionResult,
    RunManifestVerifyResult,
)
from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.types import RunID, RunType
from bioetl.interfaces.cli.main import cli


pytestmark = pytest.mark.integration


class _FakeRunManifestService:
    def __init__(self) -> None:
        created_at = datetime.now(UTC)
        self.run_id = RunID(uuid4())
        self.manifest = RunManifest(
            manifest_id="manifest-integration",
            execution_fingerprint="fingerprint-integration",
            schema_version="1.0",
            created_at=created_at,
            run_id=self.run_id,
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={"limit": 25},
            runtime_config={"run_type": "incremental", "limit": 25},
            resolved_config={"provider": "chembl", "entity_type": "activity"},
            code_provenance=RunCodeProvenance(
                pipeline_version="1.0.0",
                git_commit="abc1234",
                config_hash="deadbeef",
            ),
        )

    def show(self, identifier: str) -> RunManifestInspectionResult:
        if identifier not in {"manifest-integration", str(self.run_id)}:
            raise ValueError(identifier)
        return RunManifestInspectionResult(
            manifest=self.manifest,
            diagnostics={
                "latest_status": "success",
                "latest_event_type": "run_finished",
                "event_family_counts": {"pipeline.lifecycle": 1},
                "event_type_counts": {"run_finished": 1},
                "artifact_refs": [],
                "missing_artifact_links": 0,
                "correlation_anchor_gaps": {
                    "effective_config_hash": 0,
                    "contract_ref": 0,
                    "contract_version": 0,
                    "composite_run_id": 0,
                },
                "cross_validation_signal_present": False,
                "alert_signals": {
                    "run_failed": False,
                    "run_shutdown": False,
                    "artifact_linkage_gap": False,
                    "lineage_gap": False,
                    "dq_signal_present": False,
                    "cross_validation_signal_present": False,
                },
            },
            identity_graph={
                "run_id": str(self.run_id),
                "manifest_id": "manifest-integration",
                "execution_fingerprint": "fingerprint-integration",
                "effective_config_hash": "deadbeef",
                "contract_ref": None,
                "contract_version": None,
                "planned_artifacts": [],
                "published_artifacts": [],
            },
        )

    def diff(
        self, left_identifier: str, right_identifier: str
    ) -> RunManifestDiffResult:
        if "missing" in {left_identifier, right_identifier}:
            raise ValueError("missing")
        return RunManifestDiffResult(
            left_manifest_id="manifest-integration",
            right_manifest_id="manifest-other",
            classification="semantic_drift",
            semantic_equivalent=False,
            occurrence_only=False,
            occurrence_difference_fields=("manifest_id", "run_id"),
            semantic_difference_fields=("launch_context",),
            differences=(
                RunManifestDiffEntry(
                    field="launch_context",
                    left={"limit": 25},
                    right={"limit": 50},
                ),
            ),
        )

    def verify(
        self,
        left_identifier: str,
        right_identifier: str,
    ) -> RunManifestVerifyResult:
        if "missing" in {left_identifier, right_identifier}:
            raise ValueError("missing")
        return RunManifestVerifyResult(
            left_manifest_id="manifest-integration",
            right_manifest_id="manifest-other",
            left_run_id=str(self.run_id),
            right_run_id="00000000-0000-0000-0000-000000000003",
            verdict="cross_store_replay_verified",
            verified=True,
            semantic_equivalent=True,
            occurrence_only=False,
            missing_evidence=(),
            manifest_diff={"classification": "identical"},
            effective_config={
                "available": True,
                "semantic_equivalent": True,
                "missing_evidence": [],
            },
        )


def _patch_run_manifest_service(monkeypatch: Any, service: object) -> None:
    import bioetl.interfaces.cli.commands.run_manifest as run_manifest_cmd

    monkeypatch.setattr(
        run_manifest_cmd,
        "get_run_manifest_service",
        lambda: service,
        raising=True,
    )


def test_run_manifest_help_is_available() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["run-manifest", "--help"])

    assert result.exit_code == 0
    assert "show" in result.output
    assert "diff" in result.output


def test_run_manifest_show_yaml_uses_top_level_cli_wiring(
    monkeypatch: Any,
) -> None:
    runner = CliRunner()
    service = _FakeRunManifestService()
    _patch_run_manifest_service(monkeypatch, service)

    result = runner.invoke(
        cli,
        ["run-manifest", "show", str(service.run_id), "--format", "yaml"],
    )

    assert result.exit_code == 0
    assert "manifest:" in result.output
    assert "diagnostics:" in result.output
    assert "identity_graph:" in result.output
    assert "latest_status: success" in result.output


def test_run_manifest_diff_yaml_uses_top_level_cli_wiring(
    monkeypatch: Any,
) -> None:
    runner = CliRunner()
    _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

    result = runner.invoke(
        cli,
        [
            "run-manifest",
            "diff",
            "manifest-integration",
            "manifest-other",
            "--format",
            "yaml",
        ],
    )

    assert result.exit_code == 0
    assert "left_manifest_id: manifest-integration" in result.output
    assert "right_manifest_id: manifest-other" in result.output
    assert "classification: semantic_drift" in result.output
    assert "semantic_equivalent: false" in result.output
    assert "field: launch_context" in result.output


def test_run_manifest_verify_yaml_uses_top_level_cli_wiring(
    monkeypatch: Any,
) -> None:
    runner = CliRunner()
    _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

    result = runner.invoke(
        cli,
        [
            "run-manifest",
            "verify",
            "manifest-integration",
            "manifest-other",
            "--format",
            "yaml",
        ],
    )

    assert result.exit_code == 0
    assert "verdict: cross_store_replay_verified" in result.output
    assert "verified: true" in result.output
    assert "effective_config:" in result.output
