"""Unit coverage for CLI report inspection commands."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli.commands.report import report, show_command

pytestmark = pytest.mark.unit


def _as_command(command: object) -> click.Command:
    """typed_click_* wrappers preserve callback types, not click.Command."""
    return cast(click.Command, command)


def test_report_group_help() -> None:
    runner = CliRunner()
    result = runner.invoke(_as_command(report), ["--help"])
    assert result.exit_code == 0
    assert "Inspect and manage local pipeline/workflow run reports" in result.output


def test_show_command_requires_pipeline_or_workflow() -> None:
    runner = CliRunner()
    result = runner.invoke(_as_command(show_command), [])
    assert result.exit_code != 0


def test_show_pipeline_report_json(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "pipeline": "chembl_assay",
        "run_id": "r1",
        "status": "succeeded",
    }
    with (
        patch(
            "bioetl.interfaces.cli.commands.report.configured_report_root",
            return_value=tmp_path,
        ),
        patch(
            "bioetl.interfaces.cli.commands.report.load_pipeline_report",
            return_value=payload,
        ),
    ):
        runner = CliRunner()
        result = runner.invoke(
            _as_command(show_command),
            ["--pipeline", "chembl_assay", "--run-id", "r1", "--json"],
        )
    assert result.exit_code == 0
    assert "chembl_assay" in result.output


def test_show_pipeline_report_missing(tmp_path: Path) -> None:
    with (
        patch(
            "bioetl.interfaces.cli.commands.report.configured_report_root",
            return_value=tmp_path,
        ),
        patch(
            "bioetl.interfaces.cli.commands.report.load_pipeline_report",
            return_value=None,
        ),
    ):
        runner = CliRunner()
        result = runner.invoke(
            _as_command(show_command),
            ["--pipeline", "missing", "--run-id", "r1"],
        )
    assert result.exit_code != 0
