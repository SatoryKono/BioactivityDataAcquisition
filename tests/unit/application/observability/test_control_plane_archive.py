"""Control-plane archive skip rules and default root."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from bioetl.application.observability.control_plane_archive import (
    DEFAULT_CONTROL_PLANE_ARCHIVE_ROOT,
    archive_successful_run,
    resolve_control_plane_archive_root,
    should_archive_control_plane,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.domain.types import RunID

pytestmark = pytest.mark.unit
RUN_ID = RunID(UUID(int=14))


def _result(**overrides: object) -> RunResult:
    payload: dict[str, object] = {
        "status": PipelineRunResult.SUCCESS,
        "pipeline_name": "chembl_assay",
        "run_id": str(RUN_ID),
        "run_type": "backfill",
        "manifest_id": "manifest-archive",
    }
    payload.update(overrides)
    return RunResult(**payload)  # type: ignore[arg-type]


def test_resolve_archive_root_defaults_and_override(tmp_path: Path) -> None:
    assert (
        resolve_control_plane_archive_root(None) == DEFAULT_CONTROL_PLANE_ARCHIVE_ROOT
    )
    custom = tmp_path / "archive"
    assert resolve_control_plane_archive_root(custom) == custom


def test_should_archive_skips_flag_dry_run_and_failures() -> None:
    success = _result()
    assert should_archive_control_plane(success, None) is True
    assert (
        should_archive_control_plane(success, RunOptions(no_control_plane_archive=True))
        is False
    )
    assert should_archive_control_plane(success, RunOptions(dry_run=True)) is False
    assert (
        should_archive_control_plane(_result(status=PipelineRunResult.FAILED), None)
        is False
    )
    assert should_archive_control_plane(_result(manifest_id=None), None) is False


def test_archive_successful_run_skips_without_creating_pack(tmp_path: Path) -> None:
    data = tmp_path / "data"
    archive = tmp_path / "archive"
    verified, reason = archive_successful_run(
        result=_result(),
        options=RunOptions(no_control_plane_archive=True),
        data_root=data,
        archive_root=archive,
        report_root=None,
    )
    assert (verified, reason) == (None, "archive_skipped")
    assert not archive.exists()


def test_archive_successful_run_missing_manifest_does_not_raise(
    tmp_path: Path,
) -> None:
    verified, reason = archive_successful_run(
        result=_result(),
        options=None,
        data_root=tmp_path / "data",
        archive_root=tmp_path / "archive",
        report_root=None,
    )
    assert (verified, reason) == (None, "archive_manifest_missing")


def test_run_and_workflow_help_expose_archive_opt_out() -> None:
    from click.testing import CliRunner

    from bioetl.interfaces.cli.main import cli

    runner = CliRunner()
    run_help = runner.invoke(cli, ["run", "--help"])
    workflow_help = runner.invoke(cli, ["workflow", "run", "--help"])
    assert run_help.exit_code == 0
    assert workflow_help.exit_code == 0
    assert "--no-control-plane-archive" in run_help.output
    assert "--no-control-plane-archive" in workflow_help.output
