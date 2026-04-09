"""Unit tests for run-manifest CLI commands."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from click.testing import CliRunner

from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestDiffEntry,
    RunManifestDiffResult,
    RunManifestInspectionResult,
)
from bioetl.domain.control_plane import (
    RunCodeProvenance,
    RunLedgerEntry,
    RunManifest,
)
from bioetl.domain.types import RunID, RunType
from bioetl.interfaces.cli.main import cli


class _FakeRunManifestService:
    def __init__(self) -> None:
        run_id = RunID(uuid4())
        self._run_id = run_id
        created_at = datetime.now(UTC)
        self._manifest = RunManifest(
            manifest_id="manifest-1",
            execution_fingerprint="fingerprint-1",
            schema_version="1.0",
            created_at=created_at,
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={"limit": 100},
            runtime_config={"run_type": "incremental", "limit": 100},
            resolved_config={"provider": "chembl", "entity_type": "activity"},
            code_provenance=RunCodeProvenance(
                pipeline_version="1.0.0",
                git_commit="abc1234",
                config_hash="deadbeef",
            ),
        )
        self._ledger_entry = RunLedgerEntry(
            entry_id="entry-1",
            manifest_id="manifest-1",
            run_id=run_id,
            event_type="run_finished",
            occurred_at=created_at,
            status="success",
        )

    def show(self, identifier: str) -> RunManifestInspectionResult:
        if identifier == "missing":
            raise ValueError("missing")
        return RunManifestInspectionResult(
            manifest=self._manifest,
            ledger_entries=(self._ledger_entry,),
            diagnostics={
                "total_events": 1,
                "latest_event_type": "run_finished",
                "latest_status": "success",
                "execution_fingerprint": "fingerprint-1",
                "config_hash": "deadbeef",
                "contract_ref": "chembl_activity",
                "contract_version": "1.2.0",
                "dq_policy_ref": "chembl_activity.gold",
                "rule_bundle_version": "2026.03",
                "effective_config_artifact_id": "eca-123",
                "dq_contract_compatibility_hash": "compat-hash-1",
                "event_family_counts": {"pipeline.lifecycle": 1},
                "event_type_counts": {"run_finished": 1},
                "artifact_refs": [
                    {
                        "event_type": "artifact_published",
                        "stage": "gold",
                        "dataset_ref": "gold:chembl.activity@1",
                        "lineage_fragment_id": "gold:fragment-1",
                        "artifact_path": "/tmp/output/gold/chembl/activity",
                        "metadata_path": "/tmp/output/gold/chembl/activity/_metadata.yaml",
                        "run_id": str(self._run_id),
                        "manifest_id": "manifest-1",
                    }
                ],
                "planned_artifact_count": 1,
                "published_artifact_count": 1,
                "lineage_fragment_ids": ["gold:fragment-1"],
                "missing_artifact_links": 0,
                "identity_graph_complete": True,
                "identity_graph": {
                    "run_id": str(self._run_id),
                    "manifest_id": "manifest-1",
                    "execution_fingerprint": "fingerprint-1",
                    "effective_config_hash": "deadbeef",
                    "contract_ref": "chembl_activity",
                    "contract_version": "1.2.0",
                    "planned_artifacts": [
                        {
                            "layer": "gold",
                            "path": "/tmp/output/gold/chembl/activity",
                        }
                    ],
                    "published_artifacts": [
                        {
                            "event_type": "artifact_published",
                            "stage": "gold",
                            "dataset_ref": "gold:chembl.activity@1",
                            "lineage_fragment_id": "gold:fragment-1",
                            "artifact_path": "/tmp/output/gold/chembl/activity",
                            "metadata_path": "/tmp/output/gold/chembl/activity/_metadata.yaml",
                            "run_id": str(self._run_id),
                            "manifest_id": "manifest-1",
                        }
                    ],
                },
                "dq_rule_ids": ["gold.not_null.id"],
                "dq_dispositions": ["fail"],
                "dq_report_paths": ["/tmp/reports/gold_dq.json"],
                "dq_violation_kinds": ["cross_validation_mismatch"],
                "cross_validation_rule_ids": ["composite.cross_validation.quarantine"],
                "cross_validation_config_paths": ["cross_validation"],
                "cross_validation_signal_present": True,
                "correlation_anchor_gaps": {
                    "effective_config_hash": 0,
                    "contract_ref": 0,
                    "data_contract_version": 0,
                    "composite_run_id": 0,
                },
                "alert_signals": {
                    "run_failed": False,
                    "run_shutdown": False,
                    "artifact_linkage_gap": False,
                    "lineage_gap": False,
                    "dq_signal_present": True,
                    "cross_validation_signal_present": True,
                },
                "next_steps": [
                    "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation.",
                    (
                        "Review cross-validation mismatch outcomes and composite"
                        " policy anchors before retry or quarantine changes."
                    ),
                ],
            },
            identity_graph={
                "run_id": str(self._run_id),
                "manifest_id": "manifest-1",
                "execution_fingerprint": "fingerprint-1",
                "effective_config_hash": "deadbeef",
                "contract_ref": "chembl_activity",
                "contract_version": "1.2.0",
                "planned_artifacts": [
                    {
                        "layer": "gold",
                        "path": "/tmp/output/gold/chembl/activity",
                    }
                ],
                "published_artifacts": [
                    {
                        "event_type": "artifact_published",
                        "stage": "gold",
                        "dataset_ref": "gold:chembl.activity@1",
                        "lineage_fragment_id": "gold:fragment-1",
                        "artifact_path": "/tmp/output/gold/chembl/activity",
                        "metadata_path": "/tmp/output/gold/chembl/activity/_metadata.yaml",
                        "run_id": str(self._run_id),
                        "manifest_id": "manifest-1",
                    }
                ],
            },
        )

    def diff(
        self, left_identifier: str, right_identifier: str
    ) -> RunManifestDiffResult:
        if "missing" in {left_identifier, right_identifier}:
            raise ValueError("missing")
        return RunManifestDiffResult(
            left_manifest_id="manifest-1",
            right_manifest_id="manifest-2",
            differences=(
                RunManifestDiffEntry(
                    field="runtime_config",
                    left={"limit": 100},
                    right={"limit": 500},
                ),
            ),
        )


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def _patch_run_manifest_service(monkeypatch: Any, service: object) -> None:
    import bioetl.interfaces.cli.commands.run_manifest as run_manifest_cmd

    monkeypatch.setattr(
        run_manifest_cmd,
        "get_run_manifest_service",
        lambda: service,
        raising=True,
    )


@pytest.mark.unit
class TestRunManifestCommands:
    def test_run_manifest_help_shows_subcommands(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(cli, ["run-manifest", "--help"])

        assert result.exit_code == 0
        assert "show" in result.output
        assert "diff" in result.output

    def test_run_manifest_help_avoids_eager_registry_build(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        import importlib

        registry_helpers = importlib.import_module(
            "bioetl.interfaces.cli.registry_helpers"
        )

        monkeypatch.setattr(
            registry_helpers,
            "build_cli_registry",
            lambda: (_ for _ in ()).throw(AssertionError("registry should stay lazy")),
        )

        result = cli_runner.invoke(cli, ["run-manifest", "--help"])

        assert result.exit_code == 0
        assert (
            "Inspect control-plane run manifests and ledger history." in result.output
        )

    def test_show_json_outputs_manifest_and_ledger(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "show", "manifest-1", "--format", "json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["manifest"]["manifest_id"] == "manifest-1"
        assert payload["ledger_entries"][0]["event_type"] == "run_finished"
        assert payload["diagnostics"]["latest_status"] == "success"
        assert payload["identity_graph"]["manifest_id"] == "manifest-1"
        assert payload["diagnostics"]["contract_version"] == "1.2.0"
        assert payload["diagnostics"]["dq_rule_ids"] == ["gold.not_null.id"]
        assert payload["diagnostics"]["cross_validation_rule_ids"] == [
            "composite.cross_validation.quarantine"
        ]
        assert "alert_signals" in payload["diagnostics"]

    def test_show_yaml_outputs_manifest_and_diagnostics(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "show", "manifest-1", "--format", "yaml"],
        )

        assert result.exit_code == 0
        assert "manifest:" in result.output
        assert "ledger_entries:" in result.output
        assert "diagnostics:" in result.output
        assert "latest_status: success" in result.output
        assert "cross_validation_signal_present: true" in result.output

    def test_show_defaults_to_human_readable_text(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(cli, ["run-manifest", "show", "manifest-1"])

        assert result.exit_code == 0
        assert "Manifest" in result.output
        assert "manifest_id: manifest-1" in result.output
        assert "Code Provenance" in result.output
        assert "Ledger" in result.output
        assert "Diagnostics" in result.output
        assert "latest_status: success" in result.output
        assert "contract_version: 1.2.0" in result.output
        assert "dq_policy_ref: chembl_activity.gold" in result.output
        assert "event_family_counts" in result.output
        assert "event_type_counts" in result.output
        assert "planned_artifact_count: 1" in result.output
        assert "published_artifact_count: 1" in result.output
        assert "artifact_refs" in result.output
        assert "identity_graph_complete: true" in result.output
        assert "Identity Graph" in result.output
        assert "lineage_fragment_ids" in result.output
        assert "missing_artifact_links: 0" in result.output
        assert "gold.not_null.id" in result.output
        assert "cross_validation_mismatch" in result.output
        assert "composite.cross_validation.quarantine" in result.output
        assert "cross_validation_config_paths" in result.output
        assert "correlation_anchor_gaps" in result.output
        assert "/tmp/reports/gold_dq.json" in result.output
        assert "/tmp/output/gold/chembl/activity" in result.output
        assert "/tmp/output/gold/chembl/activity/_metadata.yaml" in result.output
        assert (
            "Review DQ report artifacts, rule IDs, and contract policy anchors "
            "before retry or escalation." in result.output
        )
        assert (
            "Review cross-validation mismatch outcomes and composite policy anchors "
            "before retry or quarantine changes." in result.output
        )
        assert "run_finished" in result.output

    def test_show_missing_manifest_prints_error(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(cli, ["run-manifest", "show", "missing"])

        assert result.exit_code == 0
        assert "Run manifest not found" in result.stderr

    def test_diff_json_outputs_changed_fields(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            [
                "run-manifest",
                "diff",
                "manifest-1",
                "manifest-2",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["left_manifest_id"] == "manifest-1"
        assert payload["right_manifest_id"] == "manifest-2"
        assert payload["differences"][0]["field"] == "runtime_config"

    def test_diff_defaults_to_human_readable_text(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "diff", "manifest-1", "manifest-2"],
        )

        assert result.exit_code == 0
        assert "Manifest Diff" in result.output
        assert "left_manifest_id: manifest-1" in result.output
        assert "right_manifest_id: manifest-2" in result.output
        assert "field: runtime_config" in result.output

    def test_diff_yaml_outputs_changed_fields(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            [
                "run-manifest",
                "diff",
                "manifest-1",
                "manifest-2",
                "--format",
                "yaml",
            ],
        )

        assert result.exit_code == 0
        assert "left_manifest_id: manifest-1" in result.output
        assert "right_manifest_id: manifest-2" in result.output
        assert "differences:" in result.output
        assert "field: runtime_config" in result.output
