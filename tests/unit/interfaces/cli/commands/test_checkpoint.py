"""Unit tests for checkpoint CLI commands."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli.main import cli

_SNAPSHOT_IDENTITY_FINGERPRINT = (
    "f29f1a5c18e94a4fe614b59ae8e68c5c65afd078155b95d1e7c4aa32f6291dcd"
)


class _FakeInspectionResult:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, object]:
        return self._payload


class _FakeWorkflowService:
    def __init__(self) -> None:
        self.audit_run_calls: list[tuple[str, int]] = []
        self.checkpoint_calls: list[tuple[str, str | None, int]] = []

    async def inspect_audit_run(
        self,
        run_id: str,
        *,
        limit: int = 100,
    ) -> _FakeInspectionResult:
        await asyncio.sleep(0)
        self.audit_run_calls.append((run_id, limit))
        return _FakeInspectionResult(
            {
                "run_id": run_id,
                "audit": {
                    "query": {"run_id": run_id, "limit": limit},
                    "entries": [
                        {
                            "timestamp": "2026-04-10T10:00:00+00:00",
                            "layer": "silver",
                            "table_name": "chembl.activity",
                            "operation": "merge",
                            "records_count": 42,
                        }
                    ],
                },
                "run_manifest": {
                    "manifest": {
                        "manifest_id": "manifest-1",
                        "pipeline_name": "chembl_activity",
                    },
                    "diagnostics": {
                        "operator_replay_mode": "Exact Replay",
                        "replay_capability": "exact_replay_supported",
                        "requested_exact_replay": True,
                        "continuation_mode": "exact_replay",
                        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
                        "replay_capability_reason": "immutable_input_snapshots_present",
                        "exact_replay_blockers": [],
                        "snapshot_status": "full",
                        "input_snapshot_ids": ["snapshot-1"],
                        "input_snapshot_identity_fingerprint": (
                            _SNAPSHOT_IDENTITY_FINGERPRINT
                        ),
                        "persistence_profile": {
                            "attained_profile": "forensic_grade",
                            "replay_ready_missing_requirements": [],
                            "forensic_grade_missing_requirements": [],
                            "composite_resume_reconstructability": {
                                "scope": "coarse_grained_composite_resume",
                                "resume_model": "checkpoint_snapshot_plus_ledger_suffix",
                                "reconstructs": [
                                    "state",
                                    "seed_completed",
                                    "merge_completed",
                                    "last_event_id",
                                    "last_event_occurred_at",
                                ],
                                "does_not_reconstruct": [
                                    "per_provider_result_maps",
                                    "rich_checkpoint_payloads",
                                ],
                            },
                        },
                        "alert_signals": {
                            "composite_resume_reconstructability_gap": False,
                        },
                        "next_steps": [
                            "No alert signals detected; continue routine monitoring."
                        ],
                    },
                },
                "compatibility": {
                    "status": "compatible",
                    "compatible": True,
                    "taxonomy": "exact_replay",
                    "replay_capability": "resume_only",
                    "replay_mode": "exact_replay",
                    "continuation_mode": "exact_replay",
                    "operator_replay_mode": "Exact Replay",
                    "replay_readiness_verdict": "exact_replay_ready",
                    "matched_anchors": [
                        "manifest_id",
                        "execution_fingerprint",
                        "effective_config_hash",
                    ],
                    "mismatched_anchors": [],
                    "missing_anchors": ["input_snapshot_fingerprint"],
                },
            }
        )

    async def inspect_checkpoint_workflow(
        self,
        pipeline_name: str,
        *,
        run_id: str | None = None,
        audit_limit: int = 100,
    ) -> _FakeInspectionResult:
        await asyncio.sleep(0)
        self.checkpoint_calls.append((pipeline_name, run_id, audit_limit))
        return _FakeInspectionResult(
            {
                "pipeline_name": pipeline_name,
                "checkpoint": {
                    "pipeline_name": pipeline_name,
                    "run_id": run_id or "00000000-0000-0000-0000-000000000123",
                    "metadata": {
                        "records_processed": 100,
                        "manifest_id": "manifest-2",
                        "execution_fingerprint": "fingerprint-2",
                        "effective_config_hash": "effective-hash-2",
                        "effective_config_artifact_id": "effective-artifact-2",
                        "contract_ref": "chembl.activity",
                        "contract_version": "1.0.0",
                        "dq_contract_compatibility_hash": "dq-hash-2",
                    },
                },
                "audit": {
                    "query": {"pipeline_name": pipeline_name, "limit": audit_limit},
                    "entries": [
                        {
                            "timestamp": "2026-04-10T11:00:00+00:00",
                            "layer": "gold",
                            "table_name": "chembl.activity_summary",
                            "operation": "overwrite",
                            "records_count": 5,
                        }
                    ],
                },
                "run_manifest": {
                    "manifest": {
                        "manifest_id": "manifest-2",
                        "run_id": run_id or "00000000-0000-0000-0000-000000000123",
                    },
                    "diagnostics": {
                        "operator_replay_mode": "Resume",
                        "replay_capability": "resume_only",
                        "requested_exact_replay": False,
                        "continuation_mode": "checkpoint_snapshot_only_resume",
                        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
                        "replay_capability_reason": "checkpoint_resume_without_exact_replay_request",
                        "exact_replay_blockers": ["exact_replay_not_requested"],
                        "snapshot_status": "partial",
                        "input_snapshot_ids": ["snapshot-2"],
                        "input_snapshot_identity_fingerprint": "snapshot-fingerprint-2",
                        "persistence_profile": {
                            "attained_profile": "replay_ready",
                            "replay_ready_missing_requirements": [],
                            "forensic_grade_missing_requirements": [
                                "lineage_closure",
                            ],
                        },
                        "alert_signals": {
                            "checkpoint_resume_blocked": False,
                        },
                        "next_steps": [
                            "Resume is compatible; this is not an exact replay.",
                        ],
                    },
                },
                "compatibility": {
                    "status": "compatible",
                    "compatible": True,
                    "taxonomy": "checkpoint_snapshot_only_resume",
                    "replay_capability": "resume_only",
                    "replay_mode": "resume",
                    "continuation_mode": "checkpoint_snapshot_only_resume",
                    "operator_replay_mode": "Resume",
                    "replay_readiness_verdict": "resume_only_ready",
                    "matched_anchors": [
                        "manifest_id",
                        "execution_fingerprint",
                        "effective_config_hash",
                    ],
                    "mismatched_anchors": [],
                    "missing_anchors": ["input_snapshot_fingerprint"],
                },
            }
        )


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def _patch_workflow_service(monkeypatch: Any, service: object) -> None:
    import bioetl.interfaces.cli.commands.checkpoint as checkpoint_module

    monkeypatch.setattr(
        checkpoint_module,
        "get_observability_workflow_service",
        lambda: service,
        raising=True,
    )


@pytest.mark.unit
def test_get_checkpoint_runtime_service_delegates_to_control_plane_api() -> None:
    """Checkpoint command module should lazily delegate runtime resolution."""
    import bioetl.interfaces.cli.commands.checkpoint as checkpoint_module

    manager = MagicMock()

    with patch(
        "bioetl.composition.control_plane_api.get_checkpoint_runtime_service",
        return_value=manager,
    ) as mock_get_checkpoint_runtime_service:
        result = checkpoint_module.get_checkpoint_runtime_service("chembl_activity")

    assert result is manager
    mock_get_checkpoint_runtime_service.assert_called_once_with("chembl_activity")


@pytest.mark.unit
def test_get_observability_workflow_service_delegates_to_interfaces_api() -> None:
    """Checkpoint command module should lazily delegate workflow resolution."""
    import bioetl.interfaces.cli.commands.checkpoint as checkpoint_module

    workflow = MagicMock()

    with patch(
        "bioetl.interfaces.observability.get_observability_workflow_service",
        return_value=workflow,
    ) as mock_get_workflow_service:
        result = checkpoint_module.get_observability_workflow_service()

    assert result is workflow
    mock_get_workflow_service.assert_called_once_with()


@pytest.mark.unit
class TestCheckpointCommands:
    def test_checkpoint_help_shows_subcommands(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(cli, ["checkpoint", "--help"])

        assert result.exit_code == 0
        assert "list" in result.output
        assert "inspect" in result.output
        assert "audit-run" in result.output

    def test_checkpoint_inspect_json_outputs_workflow_payload(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        service = _FakeWorkflowService()
        _patch_workflow_service(monkeypatch, service)

        result = cli_runner.invoke(
            cli,
            [
                "checkpoint",
                "inspect",
                "--pipeline",
                "chembl_activity",
                "--run-id",
                "00000000-0000-0000-0000-000000000123",
                "--audit-limit",
                "25",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["pipeline_name"] == "chembl_activity"
        assert payload["checkpoint"]["run_id"] == "00000000-0000-0000-0000-000000000123"
        assert service.checkpoint_calls == [
            ("chembl_activity", "00000000-0000-0000-0000-000000000123", 25)
        ]

    def test_checkpoint_audit_run_text_outputs_human_readable_summary(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        service = _FakeWorkflowService()
        _patch_workflow_service(monkeypatch, service)

        result = cli_runner.invoke(
            cli,
            [
                "checkpoint",
                "audit-run",
                "--run-id",
                "00000000-0000-0000-0000-000000000001",
            ],
        )

        assert result.exit_code == 0
        assert "Audit Run Diagnostics" in result.output
        assert "manifest_id: manifest-1" in result.output
        assert "mode: Exact Replay" in result.output
        assert "requested_exact_replay: True" in result.output
        assert "continuation_mode: exact_replay" in result.output
        assert (
            "exact_replay_support_boundary: snapshot_backed_source_runs_only"
            in result.output
        )
        assert (
            "replay_capability_reason: immutable_input_snapshots_present"
            in result.output
        )
        assert "input_snapshot_ids: ['snapshot-1']" in result.output
        assert "snapshot_status: full" in result.output
        assert _SNAPSHOT_IDENTITY_FINGERPRINT in result.output
        assert "persistence_profile: forensic_grade" in result.output
        assert "replay_ready_missing_requirements: []" in result.output
        assert "forensic_grade_missing_requirements: []" in result.output
        assert "composite_resume_reconstructability:" in result.output
        assert "checkpoint_snapshot_plus_ledger_suffix" in result.output
        assert "alert_signals:" in result.output
        assert "next_steps:" in result.output
        assert "silver/chembl.activity merge" in result.output
        assert service.audit_run_calls == [
            ("00000000-0000-0000-0000-000000000001", 100)
        ]

    def test_checkpoint_inspect_text_outputs_anchors_and_replay_taxonomy(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        service = _FakeWorkflowService()
        _patch_workflow_service(monkeypatch, service)

        result = cli_runner.invoke(
            cli,
            [
                "checkpoint",
                "inspect",
                "--pipeline",
                "chembl_activity",
                "--run-id",
                "00000000-0000-0000-0000-000000000123",
            ],
        )

        assert result.exit_code == 0
        assert "Checkpoint Workflow Diagnostics" in result.output
        assert "checkpoint_manifest_id: manifest-2" in result.output
        assert "checkpoint_execution_fingerprint: fingerprint-2" in result.output
        assert "checkpoint_effective_config_hash: effective-hash-2" in result.output
        assert (
            "checkpoint_effective_config_artifact_id: effective-artifact-2"
            in result.output
        )
        assert "checkpoint_contract_ref: chembl.activity" in result.output
        assert "checkpoint_contract_version: 1.0.0" in result.output
        assert "checkpoint_dq_contract_compatibility_hash: dq-hash-2" in result.output
        assert "replay_capability: resume_only" in result.output
        assert "compatibility_status: compatible" in result.output
        assert (
            "compatibility_taxonomy: checkpoint_snapshot_only_resume" in result.output
        )
        assert "compatibility_replay_mode: resume" in result.output
        assert (
            "compatibility_continuation_mode: checkpoint_snapshot_only_resume"
            in result.output
        )
        assert "compatibility_operator_replay_mode: Resume" in result.output
        assert (
            "compatibility_replay_readiness_verdict: resume_only_ready" in result.output
        )
        assert "compatibility_mismatched_anchors: []" in result.output
        assert (
            "compatibility_missing_anchors: ['input_snapshot_fingerprint']"
            in result.output
        )
        assert "requested_exact_replay: False" in result.output
        assert "exact_replay_blockers: ['exact_replay_not_requested']" in result.output
        assert "persistence_profile: replay_ready" in result.output
        assert "forensic_grade_missing_requirements: ['lineage_closure']" in (
            result.output
        )
        assert service.checkpoint_calls == [
            ("chembl_activity", "00000000-0000-0000-0000-000000000123", 100)
        ]
