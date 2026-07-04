"""Failure-context rendering and exit handling for CLI execution policy."""

from __future__ import annotations

import sys
from collections.abc import Mapping

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineNotFoundError,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.exit_codes import ExitCode, get_exit_code_for_exception
from bioetl.interfaces.cli.formatters import echo_error, echo_warning

__all__ = [
    "build_failure_context",
    "handle_cli_failure",
    "render_failure_context",
]


def build_failure_context(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str,
    subject_value: str,
) -> dict[str, object]:
    """Build structured context for CLI failure diagnostics."""
    if isinstance(exc, BioETLError):
        structured_context: dict[str, object] = exc.to_structured_context(
            reason_code=reason_code,
            **{subject_key: subject_value},
        )
        return structured_context

    return {
        "message": str(exc),
        "reason_code": reason_code,
        subject_key: subject_value,
        "error_type": type(exc).__name__,
    }


def render_failure_context(context: Mapping[str, object]) -> str:
    """Render a structured failure context as stable human-readable text."""
    message = str(context.get("message", ""))
    keys = sorted(key for key in context if key != "message")
    metadata = ", ".join(f"{key}={context[key]}" for key in keys)
    if not metadata:
        return message
    if not message:
        return metadata
    return f"{message} ({metadata})"


def handle_cli_failure(
    exc: BaseException,
    *,
    reason_code: str,
    subject_key: str,
    subject_value: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
    default_exit_code: ExitCode = ExitCode.FAIL,
) -> None:
    """Handle command-level exceptions with a consistent policy."""
    if isinstance(exc, PipelineNotFoundError):
        echo_error("Pipeline not found", str(exc))
        sys.exit(ExitCode.CONFIG_ERROR)

    if isinstance(exc, KeyboardInterrupt):
        echo_warning(interrupted_message)
        sys.exit(ExitCode.SIGINT)

    detail = render_failure_context(
        build_failure_context(
            exc,
            reason_code=reason_code,
            subject_key=subject_key,
            subject_value=subject_value,
        )
    )

    if isinstance(exc, BioETLError):
        domain_exit = get_exit_code_for_exception(exc)
        if domain_exit == ExitCode.FAIL:
            domain_exit = default_exit_code
        echo_error(domain_error_title, detail)
        sys.exit(domain_exit)

    exit_code = get_exit_code_for_exception(exc)
    if exit_code == ExitCode.FAIL:
        exit_code = default_exit_code
    echo_error(unexpected_error_title, detail)
    sys.exit(exit_code)
