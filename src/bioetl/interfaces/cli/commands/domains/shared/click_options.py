# ruff: noqa: UP049
"""Reusable Click option decorators for orchestration command entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import click

CommandCallback = Callable[..., object]
CommandDecorator = Callable[[CommandCallback], CommandCallback]

__all__ = [
    "CommandCallback",
    "CommandDecorator",
    "typed_click_argument",
    "typed_click_command",
    "typed_click_group",
    "typed_click_option",
    "typed_group_command",
    "typed_pass_context",
    "typed_pass_obj",
    "typed_version_option",
    "with_debug_option",
    "with_dry_run_option",
    "with_health_server_options",
    "with_limit_option",
    "with_observability_backend_options",
    "with_run_type_option",
    "with_yes_option",
]


def _cast_command[**_CommandParams, _CommandReturn](
    func: Callable[_CommandParams, _CommandReturn],
) -> Callable[_CommandParams, _CommandReturn]:
    return func


def typed_click_option(*args: object, **kwargs: object) -> CommandDecorator:
    """Attach one Click option while preserving the wrapped callback type."""

    def decorator(func: CommandCallback) -> CommandCallback:
        return _cast_command(click.option(*args, **kwargs)(func))  # type: ignore[arg-type]

    return decorator


def typed_click_argument(*args: object, **kwargs: object) -> CommandDecorator:
    """Attach one Click argument while preserving the wrapped callback type."""

    def decorator(func: CommandCallback) -> CommandCallback:
        return _cast_command(click.argument(*args, **kwargs)(func))  # type: ignore[arg-type]

    return decorator


def typed_click_command(name: str | None = None, **attrs: object) -> CommandDecorator:
    """Register one standalone Click command while preserving callback types."""

    def decorator(func: CommandCallback) -> CommandCallback:
        return _cast_command(click.command(name, **attrs)(func))  # type: ignore[call-overload]

    return decorator


def typed_click_group(**attrs: object) -> CommandDecorator:
    """Register one Click command group while preserving callback types."""

    def decorator(func: CommandCallback) -> CommandCallback:
        return _cast_command(click.group(**attrs)(func))  # type: ignore[call-overload]

    return decorator


def typed_group_command(
    group: CommandCallback,
    name: str | None = None,
    **attrs: object,
) -> CommandDecorator:
    """Register one subcommand on an existing Click group."""

    def decorator(func: CommandCallback) -> CommandCallback:
        group_obj = cast(click.Group, group)
        return _cast_command(group_obj.command(name, **attrs)(func))

    return decorator


def typed_pass_context(func: CommandCallback) -> CommandCallback:
    """Attach Click pass-context handling while preserving callback types."""
    return _cast_command(click.pass_context(func))


def typed_pass_obj(func: CommandCallback) -> CommandCallback:
    """Attach Click pass-obj handling while preserving callback types."""
    return _cast_command(click.pass_obj(func))


def typed_version_option(**kwargs: object) -> CommandDecorator:
    """Attach Click version metadata while preserving callback types."""

    def decorator(func: CommandCallback) -> CommandCallback:
        return _cast_command(click.version_option(**kwargs)(func))  # type: ignore[arg-type]

    return decorator


def with_run_type_option[**_CommandParams, _CommandReturn](
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


def with_limit_option[**_CommandParams, _CommandReturn](
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


def with_dry_run_option[**_CommandParams, _CommandReturn](
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


def with_yes_option[**_CommandParams, _CommandReturn](
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


def with_debug_option[**_CommandParams, _CommandReturn](
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


def with_health_server_options[**_CommandParams, _CommandReturn](
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


def with_observability_backend_options[**_CommandParams, _CommandReturn](
    default_backend_port: int,
) -> Callable[
    [Callable[_CommandParams, _CommandReturn]],
    Callable[_CommandParams, _CommandReturn],
]:
    """Attach detached observability-backend options to a Click command."""

    def decorator(
        func: Callable[_CommandParams, _CommandReturn],
    ) -> Callable[_CommandParams, _CommandReturn]:
        func = _cast_command(
            click.option(
                "--observability-backend-port",
                type=int,
                default=default_backend_port,
                help=(
                    "Port for the detached Quarantine Explorer backend used by "
                    "Grafana ID/detail panels."
                ),
                show_default=True,
            )(func)
        )
        return _cast_command(
            click.option(
                "--ensure-observability-backend/--no-ensure-observability-backend",
                "ensure_observability_backend",
                default=True,
                help=(
                    "Auto-start a detached Quarantine Explorer backend for "
                    "Grafana ID/detail panels."
                ),
                show_default=True,
            )(func)
        )

    return decorator
