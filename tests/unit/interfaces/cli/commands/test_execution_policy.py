# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for shared CLI execution policy."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineNotFoundError,
    PipelineRunResult,
)
from bioetl.domain.exceptions import NetworkError
from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    ExecutionFailureReasonCodes,
    build_failure_context,
    execute_with_cli_failure_policy,
    finalize_cli_execution,
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
def test_map_empty_batch_run_result_to_ok() -> None:
    batch = _BatchResult(failed=0, total=0, results=[])

    assert map_batch_run_result_to_exit_code(batch) == ExitCode.OK


@pytest.mark.unit
def test_map_success_flag_to_exit_code_matrix() -> None:
    assert map_success_flag_to_exit_code(True) == ExitCode.OK
    assert map_success_flag_to_exit_code(False) == ExitCode.PIPELINE_ERROR


@pytest.mark.unit
def test_execute_with_cli_failure_policy_returns_action_result() -> None:
    def _raise_if_called(exc: BaseException, subject: str, reason_code: str) -> None:
        del subject, reason_code
        raise exc

    result = execute_with_cli_failure_policy(
        lambda: "ok",
        subject="chembl_activity",
        reason_codes=ExecutionFailureReasonCodes(
            config="CFG",
            domain="DOM",
            interrupted="INT",
            unexpected="UNX",
        ),
        failure_handler=_raise_if_called,
    )

    assert result == "ok"


@pytest.mark.unit
def test_execute_with_cli_failure_policy_delegates_failure_and_returns_none() -> None:
    seen: list[tuple[str, str, str]] = []

    def _raise_runtime_error() -> str:
        raise RuntimeError("boom")

    result = execute_with_cli_failure_policy(
        _raise_runtime_error,
        subject="chembl_activity",
        reason_codes=ExecutionFailureReasonCodes(
            config="CFG",
            domain="DOM",
            interrupted="INT",
            unexpected="UNX",
        ),
        failure_handler=lambda exc, subject, reason_code: seen.append(
            (type(exc).__name__, subject, reason_code)
        ),
    )

    assert result is None
    assert seen == [("RuntimeError", "chembl_activity", "UNX")]


@pytest.mark.unit
def test_finalize_cli_execution_runs_health_execute_and_finalizer_in_order() -> None:
    calls: list[str] = []

    def _health() -> None:
        calls.append("health")

    def _execute() -> str:
        calls.append("execute")
        return "done"

    def _finalize(result: str) -> None:
        calls.append(f"finalize:{result}")

    finalize_cli_execution(
        health_info_presenter=_health,
        execute=_execute,
        result_finalizer=_finalize,
    )

    assert calls == ["health", "execute", "finalize:done"]


@pytest.mark.unit
def test_finalize_cli_execution_skips_finalizer_when_execution_is_handled() -> None:
    calls: list[str] = []

    def _health() -> None:
        calls.append("health")

    def _execute() -> None:
        calls.append("execute")
        return None

    def _finalize(result: object) -> None:
        calls.append(f"finalize:{result}")

    finalize_cli_execution(
        health_info_presenter=_health,
        execute=_execute,
        result_finalizer=_finalize,
    )

    assert calls == ["health", "execute"]


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
