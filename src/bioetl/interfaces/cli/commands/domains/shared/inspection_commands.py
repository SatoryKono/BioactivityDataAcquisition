"""Shared Click option packs and execution helpers for inspection commands."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol

import click

from bioetl.interfaces.cli.commands.domains.shared.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.commands.domains.shared.option_mapping import (
    option_bool,
    option_int,
    option_optional_str,
    option_str,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

__all__ = [
    "InspectionPayloadProvider",
    "add_audit_run_options",
    "add_checkpoint_workflow_options",
    "add_quarantine_stats_options",
    "run_async_inspection_command",
    "run_quarantine_stats_command",
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
            "--manifest-id",
            default=None,
            help="Optional MANIFEST_ID override for immutable checkpoint lookup",
        ),
        click.option(
            "--audit-limit",
            default=100,
            show_default=True,
            help="Maximum audit entries",
        ),
        _OUTPUT_FORMAT_OPTION,
    )


def add_quarantine_stats_options(
    *,
    silver_filter_alias_help: str,
) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Attach the shared quarantine statistics option pack."""

    def _decorator(fn: Callable[..., object]) -> Callable[..., object]:
        return _apply_click_options(
            fn,
            click.option("--pipeline", required=True, help="Pipeline name"),
            click.option("--json", "output_json", is_flag=True, help="Output as JSON"),
            click.option("--error-code", help="Scope stats to one error code"),
            click.option("--run-id", help="Scope stats to one pipeline run ID"),
            click.option(
                "--silver-filter-only",
                is_flag=True,
                help=silver_filter_alias_help,
            ),
            click.option(
                "--group-by",
                type=click.Choice(
                    [
                        "reason-code",
                        "field",
                        "rule-type",
                        "operator",
                        "reason-code-field",
                        "reason-signature",
                    ],
                    case_sensitive=False,
                ),
                help="Focused Silver reject grouping for operator triage",
            ),
            click.option(
                "--top",
                type=int,
                default=10,
                show_default=True,
                help="Maximum grouping entries to display",
            ),
        )

    return _decorator


def run_quarantine_stats_command(
    command_args: Mapping[str, object],
    *,
    show_stats_for_pipeline: Callable[..., None],
    get_runtime_service: Callable[..., object],
    get_manifest_service: Callable[[], object],
    silver_filter_error_code: str,
) -> None:
    """Run the shared quarantine statistics command body."""
    show_stats_for_pipeline(
        get_runtime_service,
        get_manifest_service,
        pipeline=option_str(command_args, "pipeline"),
        output_json=option_bool(command_args, "output_json"),
        error_code=option_optional_str(command_args, "error_code"),
        silver_filter_only=option_bool(command_args, "silver_filter_only"),
        silver_filter_error_code=silver_filter_error_code,
        top=option_int(command_args, "top"),
        group_by=option_optional_str(command_args, "group_by"),
        run_id=option_optional_str(command_args, "run_id"),
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
            raise SystemExit(ExitCode.FAIL) from exc
        emit_inspection_payload(
            result.to_dict(),
            output_format,
            text_renderer=text_renderer,
        )

    asyncio.run(_emit())
