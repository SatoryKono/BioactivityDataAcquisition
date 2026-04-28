"""Reusable Click option decorators for orchestration command entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar

import click

_CommandParams = ParamSpec("_CommandParams")
_CommandReturn = TypeVar("_CommandReturn")


def _cast_command[**CommandParams, CommandReturn](
    func: Callable[_CommandParams, _CommandReturn],
) -> Callable[_CommandParams, _CommandReturn]:
    return func


def with_run_type_option(
    help_text: str,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical ``--run-type`` option to a Click command."""
    return lambda func: _cast_command(
        click.option(
            "--run-type",
            type=click.Choice(["incremental", "backfill", "rebuild"]),
            default="incremental",
            help=help_text,
        )(func)
    )


def with_limit_option(
    help_text: str,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical ``--limit`` option to a Click command."""
    return lambda func: _cast_command(
        click.option(
            "--limit",
            type=int,
            help=help_text,
        )(func)
    )


def with_dry_run_option(
    help_text: str,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical ``--dry-run`` option to a Click command."""
    return lambda func: _cast_command(
        click.option(
            "--dry-run",
            is_flag=True,
            help=help_text,
        )(func)
    )


def with_yes_option(
    help_text: str,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical destructive-confirmation bypass option."""
    return lambda func: _cast_command(
        click.option(
            "--yes",
            "-y",
            is_flag=True,
            help=help_text,
        )(func)
    )


def with_debug_option(
    help_text: str = "Enable DEBUG level logging for detailed output",
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical ``--debug`` option to a Click command."""
    return lambda func: _cast_command(
        click.option(
            "--debug",
            is_flag=True,
            help=help_text,
        )(func)
    )


def with_health_server_options(
    default_health_server_port: int,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach the canonical health-server option pair to a Click command."""

    def decorator(
        func: Callable[_CommandParams, _CommandReturn],
    ) -> Callable[_CommandParams, _CommandReturn]:
        func = _cast_command(
            click.option(
                "--health-port",
                type=int,
                default=default_health_server_port,
                help="Port for the HTTP health server.",
                show_default=True,
            )(func)
        )
        return _cast_command(
            click.option(
                "--health-server/--no-health-server",
                "health_server",
                default=True,
                help="Enable/disable HTTP health server during execution.",
                show_default=True,
            )(func)
        )

    return decorator
