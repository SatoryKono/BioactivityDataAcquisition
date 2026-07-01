"""Command operations for the diagnostics CLI surface."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.checkpoint import _render_checkpoint_payload
from bioetl.interfaces.cli.commands.domains.diagnostics.rendering import (
    build_metrics_profile_lines,
    echo_health_results,
    render_guide_lines,
    render_run_dossier_payload,
)
from bioetl.interfaces.cli.commands.domains.health.rendering import (
    all_health_results_healthy,
)
from bioetl.interfaces.cli.commands.domains.quarantine.support import (
    _QuarantineRuntimeService,
    _show_quarantine_stats,
)
from bioetl.interfaces.cli.commands.domains.shared.inspection_commands import (
    run_async_inspection_command,
)
from bioetl.interfaces.cli.commands.domains.shared.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.commands.run_manifest import render_text_payload
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.control_plane import (
        ForensicRunDiffService,
    )
    from bioetl.application.services.control_plane.manifest.inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.composition.observability_api import (
        MetricsOperatorProfile,
        ObservabilityDiagnosticsBundle,
    )
    from bioetl.domain.types import JsonDict

__all__ = [
    "emit_checkpoint_diagnostics",
    "emit_forensic_run_diff",
    "emit_manifest_payload",
    "emit_metrics_profile",
    "emit_quarantine_stats",
    "emit_run_dossier",
    "run_health_diagnostics",
]


def run_health_diagnostics(
    bundle: ObservabilityDiagnosticsBundle,
    *,
    provider: tuple[str, ...],
    output_json: bool,
) -> None:
    """Run provider health diagnostics and emit the requested CLI format."""

    async def _run() -> JsonDict:
        providers_list = list(provider) if provider else None
        summary = await bundle.health_service.check_providers(providers=providers_list)
        return summary.to_dict()

    results = asyncio.run(_run())
    echo_health_results(results, output_json=output_json)
    if output_json:
        return
    if not all_health_results_healthy(results):
        raise SystemExit(ExitCode.FAIL)


def emit_metrics_profile(
    profile: MetricsOperatorProfile,
    *,
    output_json: bool,
) -> None:
    """Emit metrics/operator diagnostics in JSON or text format."""
    if output_json:
        click.echo(json.dumps(profile.to_dict(), indent=2, default=str))
        return
    render_guide_lines(build_metrics_profile_lines(profile))


def emit_run_dossier(
    bundle: ObservabilityDiagnosticsBundle,
    *,
    run_id: str | None,
    manifest_id: str | None,
    limit: int,
    output_format: str,
) -> None:
    """Emit one-run dossier using the canonical workflow service."""
    if bool(run_id) == bool(manifest_id):
        raise click.UsageError("Provide exactly one of --run-id or --manifest-id")

    async def _inspect_by_manifest_id() -> object:
        assert manifest_id is not None
        return await bundle.workflow_service.inspect_manifest_dossier(
            manifest_id,
            audit_limit=limit,
        )

    async def _inspect_by_run_id() -> object:
        assert run_id is not None
        return await bundle.workflow_service.inspect_run_dossier(
            run_id,
            audit_limit=limit,
        )

    action = _inspect_by_manifest_id if manifest_id else _inspect_by_run_id
    run_async_inspection_command(
        action,
        error_title="Run diagnostics failed",
        output_format=output_format,
        text_renderer=render_run_dossier_payload,
    )


def emit_checkpoint_diagnostics(
    bundle: ObservabilityDiagnosticsBundle,
    *,
    pipeline: str,
    run_id: str | None,
    audit_limit: int,
    output_format: str,
) -> None:
    """Emit checkpoint workflow diagnostics through the inspection runner."""
    run_async_inspection_command(
        lambda: bundle.workflow_service.inspect_checkpoint_workflow(
            pipeline,
            run_id=run_id,
            audit_limit=audit_limit,
        ),
        error_title="Checkpoint diagnostics failed",
        output_format=output_format,
        text_renderer=_render_checkpoint_payload,
    )


def emit_manifest_payload(
    service: RunManifestInspectionService,
    *,
    identifier: str,
    output_format: str,
) -> None:
    """Resolve one manifest and emit it using the canonical renderer."""
    try:
        result = service.show(identifier)
    except ValueError as exc:
        echo_error("Run-manifest diagnostics failed", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


def emit_forensic_run_diff(
    service: ForensicRunDiffService,
    *,
    left_identifier: str,
    right_identifier: str,
    output_format: str,
) -> None:
    """Compare two runs/manifests and emit the forensic diff report."""
    try:
        result = service.compare(left_identifier, right_identifier)
    except ValueError as exc:
        echo_error("Forensic run diff failed", str(exc))
        return
    emit_inspection_payload(
        result.to_dict(),
        output_format,
        text_renderer=render_text_payload,
    )


def emit_quarantine_stats(
    bundle: ObservabilityDiagnosticsBundle,
    runtime_service: _QuarantineRuntimeService,
    *,
    pipeline: str,
    output_json: bool,
    error_code: str | None,
    top: int,
    group_by: str | None,
    run_id: str | None,
) -> None:
    """Emit quarantine statistics from the diagnostics command family."""
    _show_quarantine_stats(
        runtime_service,
        pipeline=pipeline,
        output_json=output_json,
        error_code=error_code,
        top=top,
        group_by=group_by,
        run_id=run_id,
        run_manifest_service=bundle.run_manifest_service if run_id else None,
    )
