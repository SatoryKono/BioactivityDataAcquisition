"""Health-command failure handling at the shared CLI boundary."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    build_target_cli_boundary_policy,
    handle_boundary_cli_failure,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

_HEALTH_REASON_SUFFIXES = ("DOMAIN_ERROR", "UNEXPECTED_ERROR", "SIGINT")


def handle_health_failure(
    exc: BaseException,
    *,
    reason_code: str,
    target: str,
    domain_error_title: str,
    unexpected_error_title: str,
    interrupted_message: str,
) -> None:
    """Handle health command failures with the shared CLI execution policy."""
    for suffix in _HEALTH_REASON_SUFFIXES:
        token = f"_{suffix}"
        if reason_code.endswith(token):
            reason_prefix = reason_code.removesuffix(token)
            reason_suffix = suffix
            break
    else:
        reason_prefix = reason_code
        reason_suffix = "UNEXPECTED_ERROR"

    handle_boundary_cli_failure(
        exc,
        policy=build_target_cli_boundary_policy(
            reason_prefix=reason_prefix,
            target=target,
            domain_error_title=domain_error_title,
            unexpected_error_title=unexpected_error_title,
            interrupted_message=interrupted_message,
            default_exit_code=ExitCode.FAIL,
        ),
        reason_suffix=reason_suffix,
    )


__all__ = ["handle_health_failure"]
