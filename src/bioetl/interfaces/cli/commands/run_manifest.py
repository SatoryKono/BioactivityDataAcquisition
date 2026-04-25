"""Run-manifest inspection commands for BioETL CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands._inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.commands.run_manifest_output import (
    render_text_payload,
)
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )

__all__ = [
    "COMMANDS",
    "diff_command",
    "run_manifest",
    "score_command",
    "show_command",
]


def get_run_manifest_service() -> RunManifestInspectionService:
    """Load the run-manifest inspection service through composition on demand."""
    from bioetl.composition.control_plane_api import (
        get_run_manifest_service as _impl,
    )

    return _impl()


@click.group()
def run_manifest() -> None:
    """Inspect control-plane run manifests and ledger history."""


@run_manifest.command("show")
@click.argument("identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def show_command(identifier: str, output_format: str) -> None:
    """Show one manifest by MANIFEST_ID or RUN_ID."""
    service = get_run_manifest_service()
    try:
        result = service.show(identifier)
    except ValueError as exc:
        echo_error("Run manifest not found", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


@run_manifest.command("score")
@click.argument("identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml", "text"]),
    default="json",
    help="Output format",
)
def score_command(identifier: str, output_format: str) -> None:
    """Emit one machine-readable reproducibility audit score."""
    service = get_run_manifest_service()
    try:
        result = service.show(identifier)
    except ValueError as exc:
        echo_error("Run manifest not found", str(exc))
        return
    payload = {
        "identifier": identifier,
        "manifest_id": result.manifest.manifest_id,
        "run_id": str(result.manifest.run_id),
        "reproducibility_audit_score": result.diagnostics.get(
            "reproducibility_audit_score",
            {},
        ),
    }
    emit_inspection_payload(
        payload,
        output_format,
        text_renderer=render_text_payload,
    )


@run_manifest.command("diff")
@click.argument("left_identifier")
@click.argument("right_identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diff_command(
    left_identifier: str,
    right_identifier: str,
    output_format: str,
) -> None:
    """Diff two manifests resolved by MANIFEST_ID or RUN_ID."""
    service = get_run_manifest_service()
    try:
        result = service.diff(left_identifier, right_identifier)
    except ValueError as exc:
        echo_error("Run manifest diff failed", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


COMMANDS = (
    diff_command,
    score_command,
    show_command,
)
