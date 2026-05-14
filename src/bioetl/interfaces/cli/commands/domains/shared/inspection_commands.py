"""Shared Click option packs and execution helpers for inspection commands."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

import click

from bioetl.interfaces.cli.commands.domains.shared.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.formatters import echo_error

__all__ = [
    "InspectionPayloadProvider",
    "add_audit_run_options",
    "add_checkpoint_workflow_options",
    "run_async_inspection_command",
]

_OUTPUT_FORMAT_OPTION = click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)


class InspectionPayloadProvider(Protocol):
    """Protocol for inspection results that can render to payloads."""

    def to_dict(self) -> dict[str, object]:
        """Return a JSON/YAML/text payload representation."""
        ...


def _apply_click_options(
    fn: Callable[..., object],
    *decorators: Callable[[Callable[..., object]], Callable[..., object]],
) -> Callable[..., object]:
    """Apply Click decorators in stack order."""
    decorated = fn
    for decorator in reversed(decorators):
        decorated = decorator(decorated)
    return decorated


def add_audit_run_options(fn: Callable[..., object]) -> Callable[..., object]:
    """Attach the shared run-id/limit/format option pack."""
    return _apply_click_options(
        fn,
        click.option("--run-id", required=True, help="Pipeline RUN_ID to inspect"),
        click.option(
            "--limit",
            default=100,
            show_default=True,
            help="Maximum audit entries",
        ),
        _OUTPUT_FORMAT_OPTION,
    )


def add_checkpoint_workflow_options(
    fn: Callable[..., object],
) -> Callable[..., object]:
    """Attach the shared pipeline/run-id/audit-limit/format option pack."""
    return _apply_click_options(
        fn,
        click.option("--pipeline", required=True, help="Pipeline name"),
        click.option("--run-id", default=None, help="Optional RUN_ID override"),
        click.option(
            "--audit-limit",
            default=100,
            show_default=True,
            help="Maximum audit entries",
        ),
        _OUTPUT_FORMAT_OPTION,
    )


def run_async_inspection_command(
    action: Callable[[], Awaitable[InspectionPayloadProvider]],
    *,
    error_title: str,
    output_format: str,
    text_renderer: Callable[[dict[str, object]], str],
) -> None:
    """Run one async inspection action and emit its payload with shared handling."""

    async def _emit() -> None:
        try:
            result = await action()
        except ValueError as exc:
            echo_error(error_title, str(exc))
            return
        emit_inspection_payload(
            result.to_dict(),
            output_format,
            text_renderer=text_renderer,
        )

    asyncio.run(_emit())
