"""Unit coverage for CLI report inspection commands."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli.commands.report import (
    _emit_report,
    diff_command,
    list_command,
    prune_command,
    report,
    show_command,
)

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


def test_show_workflow_report_json(tmp_path: Path) -> None:
    payload = {"identity": {"workflow_name": "refresh", "workflow_run_id": "w1"}}
    with (
        patch(
            "bioetl.interfaces.cli.commands.report.configured_report_root",
            return_value=tmp_path,
        ),
        patch(
            "bioetl.interfaces.cli.commands.report.load_workflow_report",
            return_value=payload,
        ) as loader,
    ):
        result = CliRunner().invoke(
            _as_command(show_command),
            ["--workflow", "refresh", "--workflow-run-id", "w1", "--json"],
        )

    assert result.exit_code == 0
    assert '"workflow_name": "refresh"' in result.output
    assert loader.call_args.kwargs["latest"] is False


def test_show_workflow_report_missing(tmp_path: Path) -> None:
    with (
        patch(
            "bioetl.interfaces.cli.commands.report.configured_report_root",
            return_value=tmp_path,
        ),
        patch(
            "bioetl.interfaces.cli.commands.report.load_workflow_report",
            return_value=None,
        ),
    ):
        result = CliRunner().invoke(
            _as_command(show_command), ["--workflow", "missing"]
        )

    assert result.exit_code != 0
    assert "workflow run report not found" in result.output


def test_list_workflow_reports_emits_entries(tmp_path: Path) -> None:
    entry = SimpleNamespace(
        owner="refresh", run_id="w1", status=None, json_path="w1.json"
    )
    with (
        patch(
            "bioetl.interfaces.cli.commands.report.configured_report_root",
            return_value=tmp_path,
        ),
        patch(
            "bioetl.interfaces.cli.commands.report.list_workflow_reports",
            return_value=[entry],
        ) as loader,
    ):
        result = CliRunner().invoke(
            _as_command(list_command), ["--workflow", "refresh", "--limit", "3"]
        )

    assert result.exit_code == 0
    assert "refresh\tw1\t-\tw1.json" in result.output
    assert loader.call_args.kwargs["limit"] == 3


def test_list_pipeline_reports_emits_entries(tmp_path: Path) -> None:
    entry = SimpleNamespace(
        owner="chembl_assay", run_id="r1", status="failed", json_path="r1.json"
    )
    with (
        patch(
            "bioetl.interfaces.cli.commands.report.configured_report_root",
            return_value=tmp_path,
        ),
        patch(
            "bioetl.interfaces.cli.commands.report.list_pipeline_reports",
            return_value=[entry],
        ) as loader,
    ):
        result = CliRunner().invoke(
            _as_command(list_command), ["--pipeline", "chembl_assay"]
        )

    assert result.exit_code == 0
    assert "chembl_assay\tr1\tfailed\tr1.json" in result.output
    assert loader.call_args.kwargs["pipeline_name"] == "chembl_assay"


def test_diff_reports_emits_structured_delta(tmp_path: Path) -> None:
    reports = [{"run_id": "a"}, {"run_id": "b"}]
    with (
        patch(
            "bioetl.interfaces.cli.commands.report.configured_report_root",
            return_value=tmp_path,
        ),
        patch(
            "bioetl.interfaces.cli.commands.report.load_pipeline_report",
            side_effect=reports,
        ),
        patch(
            "bioetl.interfaces.cli.commands.report.diff_pipeline_reports",
            return_value={"changed": 2},
        ),
    ):
        result = CliRunner().invoke(
            _as_command(diff_command),
            ["--pipeline", "chembl", "--run-id-a", "a", "--run-id-b", "b"],
        )

    assert result.exit_code == 0
    assert '"changed": 2' in result.output


@pytest.mark.parametrize("reports", [(None, {"run_id": "b"}), ({"run_id": "a"}, None)])
def test_diff_reports_requires_both_inputs(
    tmp_path: Path, reports: tuple[dict[str, str] | None, dict[str, str] | None]
) -> None:
    with (
        patch(
            "bioetl.interfaces.cli.commands.report.configured_report_root",
            return_value=tmp_path,
        ),
        patch(
            "bioetl.interfaces.cli.commands.report.load_pipeline_report",
            side_effect=reports,
        ),
    ):
        result = CliRunner().invoke(
            _as_command(diff_command),
            ["--pipeline", "chembl", "--run-id-a", "a", "--run-id-b", "b"],
        )

    assert result.exit_code != 0
    assert "one or both run reports were not found" in result.output


@pytest.mark.parametrize(
    ("apply", "expected"),
    [(False, "would delete"), (True, "deleted")],
)
def test_prune_reports_describes_dry_run_and_apply_modes(
    tmp_path: Path, apply: bool, expected: str
) -> None:
    args = ["--kind", "pipeline", "--owner", "chembl", "--max-count", "2"]
    if apply:
        args.append("--apply")
    with (
        patch(
            "bioetl.interfaces.cli.commands.report.configured_report_root",
            return_value=tmp_path,
        ),
        patch(
            "bioetl.interfaces.cli.commands.report.prune_reports",
            return_value=[tmp_path / "old-a", tmp_path / "old-b"],
        ) as prune,
    ):
        result = CliRunner().invoke(_as_command(prune_command), args)

    assert result.exit_code == 0
    assert f"{expected}: 2 directories" in result.output
    assert prune.call_args.kwargs["dry_run"] is (not apply)


def test_emit_report_prefers_existing_markdown_artifact(tmp_path: Path) -> None:
    markdown = tmp_path / "pipeline-run-report.md"
    markdown.write_text("# persisted report\n", encoding="utf-8")

    with patch("bioetl.interfaces.cli.commands.report.click.echo") as echo:
        _emit_report(
            {
                "artifacts": [
                    "invalid",
                    {"ref": None},
                    {"ref": "report.json"},
                    {"ref": str(markdown)},
                ]
            },
            as_json=False,
            markdown_hint="pipeline-run-report.md",
        )

    echo.assert_called_once_with("# persisted report\n")


def test_emit_report_falls_back_to_identity_json() -> None:
    with patch("bioetl.interfaces.cli.commands.report.click.echo") as echo:
        _emit_report(
            {"identity": {"pipeline_name": "chembl_assay"}},
            as_json=False,
            markdown_hint="pipeline-run-report.md",
        )

    messages = [str(call.args[0]) for call in echo.call_args_list]
    assert messages[0] == "# report chembl_assay"
    assert '"pipeline_name": "chembl_assay"' in messages[1]
    assert "markdown sibling" in messages[2]
