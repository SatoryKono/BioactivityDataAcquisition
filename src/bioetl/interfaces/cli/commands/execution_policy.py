"""Thin wrapper re-exporting canonical CLI execution-policy helpers."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.shared.execution_policy import (
    BatchRunResultProtocol,
    CLI_ENTRYPOINT_TYPED_ERRORS,
    build_failure_context,
    handle_cli_failure,
    map_batch_run_result_to_exit_code,
    map_run_status_to_exit_code,
    map_success_flag_to_exit_code,
    render_failure_context,
)

__all__ = [
    "BatchRunResultProtocol",
    "CLI_ENTRYPOINT_TYPED_ERRORS",
    "build_failure_context",
    "handle_cli_failure",
    "map_batch_run_result_to_exit_code",
    "map_run_status_to_exit_code",
    "map_success_flag_to_exit_code",
    "render_failure_context",
]
