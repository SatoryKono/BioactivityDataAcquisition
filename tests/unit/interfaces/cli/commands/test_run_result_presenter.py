"""Unit tests for canonical run result presenter helpers.

Tests echo_run_result for all PipelineRunResult statuses,
covering the previously uncovered lines 27, 35-36.
"""

from __future__ import annotations

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.interfaces.cli.commands.domains.run.result_presenter import (
    echo_run_result,
)


def _make_result(**kwargs: object) -> RunResult:
    """Build a RunResult with sensible defaults."""
    defaults: dict[str, object] = {
        "status": PipelineRunResult.SUCCESS,
        "pipeline_name": "chembl_activity",
        "run_id": "abcdef1234567890",
        "run_type": "incremental",
        "records_fetched": 0,
        "records_bronze": 0,
        "records_silver": 0,
        "records_gold": 0,
        "records_quarantined": 0,
        "records_filtered_out": 0,
        "error_message": None,
        "error_type": None,
    }
    defaults.update(kwargs)  # type: ignore[arg-type]
    return RunResult(**defaults)  # type: ignore[arg-type]


class TestEchoRunResultSuccess:
    """Tests for PipelineRunResult.SUCCESS path."""

    def test_success_prints_run_id_prefix(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """run_id is truncated to 8 chars in the success message."""
        result = _make_result(
            run_id="abcdef1234567890", status=PipelineRunResult.SUCCESS
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "abcdef12" in out
        assert "Pipeline completed successfully" in out

    def test_success_short_run_id_not_truncated(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Short run_id (<=8 chars) is used as-is."""
        result = _make_result(run_id="short", status=PipelineRunResult.SUCCESS)
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "short" in out

    def test_success_records_gold_nonzero_is_printed(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Gold record count is printed when records_gold > 0 (line 27)."""
        result = _make_result(
            status=PipelineRunResult.SUCCESS,
            records_fetched=100,
            records_silver=100,
            records_gold=80,
            records_quarantined=0,
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "Gold records:" in out
        assert "80" in out

    def test_success_records_gold_zero_not_printed(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Gold record count is NOT printed when records_gold == 0."""
        result = _make_result(
            status=PipelineRunResult.SUCCESS,
            records_fetched=100,
            records_silver=100,
            records_gold=0,
            records_quarantined=0,
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "Gold records:" not in out

    def test_success_quarantined_nonzero_prints_neutral_summary_line(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Non-zero quarantine count stays neutral in success summary output."""
        result = _make_result(
            status=PipelineRunResult.SUCCESS,
            records_fetched=100,
            records_silver=95,
            records_gold=0,
            records_quarantined=5,
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "Quarantined (DQ):    5" in out
        assert "WARNING" not in out

    def test_success_filtered_out_nonzero_prints_neutral_summary_line(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Filter-rejected count stays neutral in success summary output."""
        result = _make_result(
            status=PipelineRunResult.SUCCESS,
            records_fetched=100,
            records_silver=95,
            records_filtered_out=5,
            records_gold=0,
            records_quarantined=0,
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "Silver filter rejects: 5" in out
        assert "WARNING" not in out

    def test_success_filtered_out_zero_prints_zero_line(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Filter-rejected zero line is shown when there are no filter rejects."""
        result = _make_result(
            status=PipelineRunResult.SUCCESS,
            records_fetched=100,
            records_silver=100,
            records_filtered_out=0,
            records_gold=0,
            records_quarantined=0,
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "Silver filter rejects: 0" in out

    def test_success_quarantined_zero_prints_zero_line(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Quarantined 0 line printed (no WARNING) when records_quarantined == 0."""
        result = _make_result(
            status=PipelineRunResult.SUCCESS,
            records_fetched=100,
            records_silver=100,
            records_gold=0,
            records_quarantined=0,
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "Quarantined (DQ):    0" in out
        assert "WARNING" not in out


class TestEchoRunResultDryRun:
    """Tests for PipelineRunResult.DRY_RUN path — covers lines 34-36."""

    def test_dry_run_prints_completed_message(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Dry-run status prints 'no changes made' message (line 35)."""
        result = _make_result(status=PipelineRunResult.DRY_RUN, run_id="dryrun12345678")
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "Dry-run completed (no changes made)" in out

    def test_dry_run_includes_run_id(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Dry-run message includes truncated run_id."""
        result = _make_result(
            status=PipelineRunResult.DRY_RUN, run_id="abcdef1234567890"
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "abcdef12" in out

    def test_dry_run_returns_after_message(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """No FAILED or SHUTDOWN messages appear after DRY_RUN."""
        result = _make_result(status=PipelineRunResult.DRY_RUN)
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "Pipeline failed" not in out
        assert "shut down" not in out


class TestEchoRunResultShutdown:
    """Tests for PipelineRunResult.SHUTDOWN path."""

    def test_shutdown_prints_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        """SHUTDOWN status prints graceful shutdown warning."""
        result = _make_result(
            status=PipelineRunResult.SHUTDOWN,
            records_fetched=42,
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "gracefully shut down" in out
        assert "WARNING" in out

    def test_shutdown_prints_processed_count(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """SHUTDOWN status prints records_fetched counter."""
        result = _make_result(
            status=PipelineRunResult.SHUTDOWN,
            records_fetched=42,
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "42" in out


class TestEchoRunResultFailed:
    """Tests for PipelineRunResult.FAILED path."""

    def test_failed_prints_error_to_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """FAILED status prints error to stderr."""
        result = _make_result(
            status=PipelineRunResult.FAILED,
            records_fetched=10,
            error_message="Connection timed out",
        )
        echo_run_result(result)
        err = capsys.readouterr().err
        assert "Pipeline failed" in err
        assert "Connection timed out" in err

    def test_failed_uses_unknown_error_when_no_message(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """FAILED with no error_message falls back to 'Unknown error'."""
        result = _make_result(
            status=PipelineRunResult.FAILED,
            records_fetched=5,
            error_message=None,
        )
        echo_run_result(result)
        err = capsys.readouterr().err
        assert "Unknown error" in err

    def test_failed_prints_processed_before_failure(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """FAILED prints records_fetched count."""
        result = _make_result(
            status=PipelineRunResult.FAILED,
            records_fetched=7,
            error_message="boom",
        )
        echo_run_result(result)
        out = capsys.readouterr().out
        assert "7" in out
