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
