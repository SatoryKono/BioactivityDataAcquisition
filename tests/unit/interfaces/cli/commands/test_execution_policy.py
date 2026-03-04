"""Unit tests for shared CLI execution policy."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from bioetl.application.services import PipelineNotFoundError, PipelineRunResult
from bioetl.domain.exceptions import NetworkError
from bioetl.interfaces.cli.commands.execution_policy import (
    build_failure_context,
    handle_cli_failure,
    map_batch_run_result_to_exit_code,
    map_run_status_to_exit_code,
    map_success_flag_to_exit_code,
    render_failure_context,
)
from bioetl.interfaces.cli.exit_codes import ExitCode


@dataclass
class _BatchItem:
    status: PipelineRunResult


@dataclass
class _BatchResult:
    failed: int
    total: int
    results: list[_BatchItem]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "error_type", "expected"),
    [
        (PipelineRunResult.SUCCESS, None, ExitCode.OK),
        (PipelineRunResult.DRY_RUN, None, ExitCode.OK),
        (PipelineRunResult.SHUTDOWN, None, ExitCode.SIGINT),
        (PipelineRunResult.FAILED, "ValueError", ExitCode.CONFIG_ERROR),
        (PipelineRunResult.FAILED, "FileNotFoundError", ExitCode.EX_NOINPUT),
        (PipelineRunResult.FAILED, "DataQualityError", ExitCode.DATA_QUALITY_ERROR),
        (PipelineRunResult.FAILED, "NetworkError", ExitCode.NETWORK_ERROR),
        (PipelineRunResult.FAILED, "UnknownError", ExitCode.PIPELINE_ERROR),
    ],
)
def test_map_run_status_to_exit_code_matrix(
    status: PipelineRunResult,
    error_type: str | None,
    expected: ExitCode,
) -> None:
    assert map_run_status_to_exit_code(status, error_type) == expected


@pytest.mark.unit
def test_map_batch_run_result_to_exit_code_success() -> None:
    batch = _BatchResult(
        failed=0,
        total=2,
        results=[
            _BatchItem(status=PipelineRunResult.SUCCESS),
            _BatchItem(status=PipelineRunResult.DRY_RUN),
        ],
    )
    assert map_batch_run_result_to_exit_code(batch) == ExitCode.OK


@pytest.mark.unit
def test_map_batch_run_result_to_exit_code_failure() -> None:
    batch = _BatchResult(
        failed=1,
        total=2,
        results=[
            _BatchItem(status=PipelineRunResult.SUCCESS),
            _BatchItem(status=PipelineRunResult.FAILED),
        ],
    )
    assert map_batch_run_result_to_exit_code(batch) == ExitCode.PIPELINE_ERROR


@pytest.mark.unit
def test_map_batch_run_result_to_exit_code_shutdown() -> None:
    batch = _BatchResult(
        failed=0,
        total=1,
        results=[_BatchItem(status=PipelineRunResult.SHUTDOWN)],
    )
    assert map_batch_run_result_to_exit_code(batch) == ExitCode.SIGINT


@pytest.mark.unit
def test_map_success_flag_to_exit_code_matrix() -> None:
    assert map_success_flag_to_exit_code(True) == ExitCode.OK
    assert map_success_flag_to_exit_code(False) == ExitCode.PIPELINE_ERROR


@pytest.mark.unit
def test_handle_cli_failure_pipeline_not_found_exits_with_config_error() -> None:
    with pytest.raises(SystemExit) as exc_info:
        handle_cli_failure(
            PipelineNotFoundError("chembl_activity", ["chembl_target"]),
            reason_code="CLI_TEST_CONFIG_ERROR",
            subject_key="pipeline",
            subject_value="chembl_activity",
            domain_error_title="Domain failure",
            unexpected_error_title="Unexpected failure",
            interrupted_message="Interrupted",
        )
    assert exc_info.value.code == ExitCode.CONFIG_ERROR


@pytest.mark.unit
def test_handle_cli_failure_keyboard_interrupt_exits_with_sigint() -> None:
    with pytest.raises(SystemExit) as exc_info:
        handle_cli_failure(
            KeyboardInterrupt(),
            reason_code="CLI_TEST_SIGINT",
            subject_key="pipeline",
            subject_value="chembl_activity",
            domain_error_title="Domain failure",
            unexpected_error_title="Unexpected failure",
            interrupted_message="Interrupted",
        )
    assert exc_info.value.code == ExitCode.SIGINT


@pytest.mark.unit
def test_handle_cli_failure_domain_exception_uses_specific_exit_code() -> None:
    with pytest.raises(SystemExit) as exc_info:
        handle_cli_failure(
            NetworkError("Rate limited"),
            reason_code="CLI_TEST_DOMAIN_ERROR",
            subject_key="pipeline",
            subject_value="chembl_activity",
            domain_error_title="Domain failure",
            unexpected_error_title="Unexpected failure",
            interrupted_message="Interrupted",
        )
    assert exc_info.value.code == ExitCode.NETWORK_ERROR


@pytest.mark.unit
def test_handle_cli_failure_unknown_exception_uses_default_exit_code() -> None:
    with pytest.raises(SystemExit) as exc_info:
        handle_cli_failure(
            RuntimeError("boom"),
            reason_code="CLI_TEST_UNEXPECTED_ERROR",
            subject_key="pipeline",
            subject_value="chembl_activity",
            domain_error_title="Domain failure",
            unexpected_error_title="Unexpected failure",
            interrupted_message="Interrupted",
            default_exit_code=ExitCode.PIPELINE_ERROR,
        )
    assert exc_info.value.code == ExitCode.PIPELINE_ERROR


@pytest.mark.unit
def test_build_failure_context_for_domain_exception_includes_structured_fields() -> (
    None
):
    exc = NetworkError("Rate limited").with_context(provider="chembl")
    context = build_failure_context(
        exc,
        reason_code="CLI_TEST_DOMAIN_ERROR",
        subject_key="pipeline",
        subject_value="chembl_activity",
    )

    assert context["reason_code"] == "CLI_TEST_DOMAIN_ERROR"
    assert context["pipeline"] == "chembl_activity"
    assert context["error_type"] == "NetworkError"
    assert context["error_category"] == "NETWORK_ERROR"
    assert context["provider"] == "chembl"


@pytest.mark.unit
def test_render_failure_context_includes_sorted_metadata() -> None:
    rendered = render_failure_context(
        {
            "message": "boom",
            "reason_code": "CLI_TEST",
            "pipeline": "chembl_activity",
            "error_type": "RuntimeError",
        }
    )

    assert rendered.startswith("boom (")
    assert "error_type=RuntimeError" in rendered
    assert "pipeline=chembl_activity" in rendered
    assert "reason_code=CLI_TEST" in rendered
