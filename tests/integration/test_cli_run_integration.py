"""Integration tests for CLI commands (TS-002, TS-003)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from bioetl.infrastructure.clients.chembl.impl import ChemblExtractionServiceImpl
from bioetl.interfaces.cli import app

sys.modules.setdefault("tqdm", MagicMock())

runner = CliRunner()


@pytest.mark.integration
def test_cli_run_dry_run_success(tmp_path, monkeypatch):
    """TS-002: bioetl run executes dry-run without writing outputs."""
    monkeypatch.setenv(
        "BIOETL_CONFIG_DIR",
        str(Path("tests/fixtures/configs").resolve()),
    )
    monkeypatch.setattr(
        ChemblExtractionServiceImpl,
        "get_release_version",
        lambda self: "chembl_cli_integration",
    )
    result = runner.invoke(
        app,
        [
            "run",
            "activity_chembl",
            "--config",
            "chembl_activity_test.yaml",
            "--dry-run",
            "--output",
            str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 0
    assert "Starting pipeline" in result.stdout
    assert "Pipeline finished successfully" in result.stdout
    assert not (tmp_path / "output" / "activity.csv").exists()


@pytest.mark.integration
def test_cli_list_pipelines_contains_chembl_activity():
    """TS-003: bioetl list-pipelines includes activity pipeline."""
    result = runner.invoke(app, ["list-pipelines"])

    assert result.exit_code == 0
    assert "activity_chembl" in result.stdout
