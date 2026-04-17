"""Unit tests for the unified diagnostics CLI command family."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli.main import cli


class _FakeInspectionResult:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, object]:
        return self._payload


class _FakeHealthSummary:
    def __init__(self, payload: dict[str, dict[str, str | float]]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, dict[str, str | float]]:
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
                        "replay_capability": "exact_replay_supported",
                        "requested_exact_replay": True,
                        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
                        "replay_capability_reason": "immutable_input_snapshots_present",
                        "exact_replay_blockers": [],
                        "input_snapshot_ids": ["snapshot-1"],
                        "input_snapshot_identity_fingerprint": "fingerprint-1",
                    },
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
                    "metadata": {"records_processed": 100},
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
                    }
                },
            }
        )


class _FakeRunManifestService:
    def show(self, identifier: str) -> _FakeInspectionResult:
        return _FakeInspectionResult(
            {
                "manifest": {
                    "manifest_id": "manifest-1",
                    "run_id": identifier,
                    "pipeline_name": "chembl_activity",
                    "provider": "chembl",
                    "entity": "activity",
                    "run_type": "incremental",
                    "created_at": "2026-04-10T10:00:00+00:00",
                    "execution_fingerprint": "fingerprint-1",
                    "schema_version": "1.0",
                },
                "ledger_entries": [],
                "diagnostics": {
                    "latest_status": "success",
                    "latest_event_type": "run_finished",
                    "total_events": 1,
                },
                "identity_graph": {},
            }
        )


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def _build_bundle(
    *,
    health_service: object | None = None,
    workflow_service: object | None = None,
    run_manifest_service: object | None = None,
) -> object:
    return SimpleNamespace(
        health_service=health_service,
        workflow_service=workflow_service,
        run_manifest_service=run_manifest_service,
    )


@pytest.mark.unit
def test_diagnostics_help_displays_subcommands(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["diagnostics", "--help"])

    assert result.exit_code == 0
    assert "guide" in result.output
    assert "health" in result.output
    assert "metrics" in result.output
    assert "run" in result.output
    assert "checkpoint" in result.output
    assert "manifest" in result.output
    assert "quarantine" in result.output


@pytest.mark.unit
def test_diagnostics_guide_displays_canonical_routes(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["diagnostics", "guide"])

    assert result.exit_code == 0
    assert "BioETL Diagnostics Guide" in result.output
    assert "bioetl diagnostics metrics" in result.output
    assert "bioetl diagnostics health" in result.output
    assert "bioetl diagnostics checkpoint" in result.output
    assert "bioetl diagnostics manifest" in result.output
    assert "bioetl diagnostics quarantine" in result.output
    assert "auto-managed during pipeline runs" in result.output
    assert "report-observability-metric-inventory" in result.output
    assert "grafana/prometheus-rules/bioetl_observability.yml" in result.output


@pytest.mark.unit
def test_diagnostics_metrics_json_uses_operator_profile(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    def _profile_to_dict() -> dict[str, object]:
        return {
            "metrics_enabled": True,
            "metrics_server_enabled": True,
            "metrics_server_running": False,
            "metrics_port": 8000,
            "metrics_addr": "0.0.0.0",
            "metrics_started_at": None,
            "metrics_endpoint": "http://0.0.0.0:8000/metrics",
            "metrics_server_mode": "auto_managed_during_pipeline_runs",
            "pushgateway_mode": "best_effort_on_run_completion",
            "pushgateway_gateway": "localhost:9091",
            "tracing_enabled": False,
            "audit_enabled": False,
        }

    profile = SimpleNamespace(to_dict=_profile_to_dict)
    import bioetl.interfaces.cli.commands.diagnostics as diagnostics_module

    monkeypatch.setattr(
        diagnostics_module,
        "get_metrics_operator_profile",
        lambda: profile,
        raising=True,
    )

    result = cli_runner.invoke(cli, ["diagnostics", "metrics", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["metrics_server_mode"] == "auto_managed_during_pipeline_runs"
    assert payload["pushgateway_mode"] == "best_effort_on_run_completion"


@pytest.mark.unit
def test_diagnostics_metrics_text_displays_operator_workflow(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    profile = SimpleNamespace(
        metrics_enabled=True,
        metrics_server_enabled=True,
        metrics_server_running=False,
        metrics_port=8000,
        metrics_addr="0.0.0.0",
        metrics_started_at=None,
        metrics_endpoint="http://0.0.0.0:8000/metrics",
        metrics_server_mode="auto_managed_during_pipeline_runs",
        pushgateway_mode="best_effort_on_run_completion",
        pushgateway_gateway="localhost:9091",
        tracing_enabled=False,
        audit_enabled=False,
    )
    import bioetl.interfaces.cli.commands.diagnostics as diagnostics_module

    monkeypatch.setattr(
        diagnostics_module,
        "get_metrics_operator_profile",
        lambda: profile,
        raising=True,
    )

    result = cli_runner.invoke(cli, ["diagnostics", "metrics"])

    assert result.exit_code == 0
    assert "BioETL Metrics Diagnostics" in result.output
    assert "metrics_server_mode: auto_managed_during_pipeline_runs" in result.output
    assert "pushgateway_mode: best_effort_on_run_completion" in result.output
    assert (
        "inspect metrics/admin state: bioetl diagnostics metrics [--json]"
        in result.output
    )
    assert "report-observability-metric-inventory" in result.output


@pytest.mark.unit
def test_diagnostics_health_json_uses_bundle_health_service(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    health_service = MagicMock()
    health_service.check_providers = AsyncMock(
        return_value=_FakeHealthSummary(
            {"chembl": {"status": "healthy", "latency_ms": 12.0}}
        )
    )
    bundle = _build_bundle(health_service=health_service)
    import bioetl.interfaces.cli.commands.diagnostics as diagnostics_module

    monkeypatch.setattr(
        diagnostics_module,
        "get_observability_diagnostics_bundle",
        lambda: bundle,
        raising=True,
    )

    result = cli_runner.invoke(cli, ["diagnostics", "health", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["chembl"]["status"] == "healthy"
    health_service.check_providers.assert_awaited_once_with(providers=None)


@pytest.mark.unit
def test_diagnostics_run_text_outputs_correlated_summary(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    workflow_service = _FakeWorkflowService()
    bundle = _build_bundle(workflow_service=workflow_service)
    import bioetl.interfaces.cli.commands.diagnostics as diagnostics_module

    monkeypatch.setattr(
        diagnostics_module,
        "get_observability_diagnostics_bundle",
        lambda: bundle,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        ["diagnostics", "run", "--run-id", "00000000-0000-0000-0000-000000000001"],
    )

    assert result.exit_code == 0
    assert "Audit Run Diagnostics" in result.output
    assert "manifest_id: manifest-1" in result.output
    assert (
        "exact_replay_support_boundary: snapshot_backed_source_runs_only"
        in result.output
    )
    assert (
        "replay_capability_reason: immutable_input_snapshots_present" in result.output
    )
    assert workflow_service.audit_run_calls == [
        ("00000000-0000-0000-0000-000000000001", 100)
    ]


@pytest.mark.unit
def test_diagnostics_manifest_json_outputs_manifest_payload(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    bundle = _build_bundle(run_manifest_service=_FakeRunManifestService())
    import bioetl.interfaces.cli.commands.diagnostics as diagnostics_module

    monkeypatch.setattr(
        diagnostics_module,
        "get_observability_diagnostics_bundle",
        lambda: bundle,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        ["diagnostics", "manifest", "manifest-1", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["manifest"]["manifest_id"] == "manifest-1"
    assert payload["diagnostics"]["latest_status"] == "success"


@pytest.mark.unit
def test_diagnostics_quarantine_json_reuses_quarantine_stats_helper(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    manager = MagicMock()
    manager.get_stats = AsyncMock(return_value={"total_count": 3})
    bundle = _build_bundle(run_manifest_service=None)
    import bioetl.interfaces.cli.commands.diagnostics as diagnostics_module

    monkeypatch.setattr(
        diagnostics_module,
        "get_observability_diagnostics_bundle",
        lambda: bundle,
        raising=True,
    )
    monkeypatch.setattr(
        diagnostics_module,
        "get_quarantine_manager",
        lambda pipeline: manager,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        ["diagnostics", "quarantine", "--pipeline", "chembl_activity", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total_count"] == 3
    manager.get_stats.assert_awaited_once_with(error_code=None, run_id=None)
