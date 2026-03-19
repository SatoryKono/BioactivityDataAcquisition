"""Thin wrapper re-exporting canonical run-all command policy helpers."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
    RunAllCommandInput,
    build_run_all_command_input,
    exit_with_code,
    handle_run_all_cli_failure,
    prepare_run_all_execution_plan,
    run_all_command_flow,
)

__all__ = [
    "RunAllCommandInput",
    "build_run_all_command_input",
    "exit_with_code",
    "handle_run_all_cli_failure",
    "prepare_run_all_execution_plan",
    "run_all_command_flow",
]
