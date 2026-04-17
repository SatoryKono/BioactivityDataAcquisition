"""Unified operator-facing diagnostics entrypoint for BioETL CLI."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from typing import TYPE_CHECKING

import click

from bioetl.interfaces.cli.commands.checkpoint import _render_checkpoint_payload
from bioetl.interfaces.cli.commands.domains.health.rendering import (
    all_health_results_healthy,
    build_health_result_lines,
    render_health_results_json,
)
from bioetl.interfaces.cli.commands.domains.quarantine.support import (
    _show_quarantine_stats,
)
from bioetl.interfaces.cli.commands.inspection_output import (
    emit_inspection_payload,
)
from bioetl.interfaces.cli.commands.run_manifest_output import (
    render_text_payload,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import echo_error

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.composition.observability_api import (
        MetricsOperatorProfile,
        ObservabilityDiagnosticsBundle,
    )
    from bioetl.domain.types import JsonDict

__all__ = [
    "COMMANDS",
    "diagnostics",
    "diagnostics_checkpoint",
    "diagnostics_guide",
    "diagnostics_health",
    "diagnostics_manifest",
    "diagnostics_metrics",
    "diagnostics_quarantine",
    "diagnostics_run",
    "get_metrics_operator_profile",
    "get_observability_diagnostics_bundle",
    "get_quarantine_manager",
]


def get_observability_diagnostics_bundle() -> ObservabilityDiagnosticsBundle:
    """Load the canonical operator diagnostics bundle on demand."""
    from bioetl.interfaces.observability import (
        get_observability_diagnostics_bundle as _impl,
    )

    return _impl()


def get_metrics_operator_profile() -> MetricsOperatorProfile:
    """Load the canonical operator-facing metrics diagnostics profile."""
    from bioetl.interfaces.observability import get_metrics_operator_profile as _impl

    return _impl()


def get_quarantine_manager(pipeline: str) -> object:
    """Load the quarantine manager through composition on demand."""
    from bioetl.composition.resources_api import get_quarantine_manager as _impl

    return _impl(pipeline)


def _build_diagnostics_guide_lines() -> list[str]:
    """Return the canonical operator diagnostics routing guide."""
    return [
        "BioETL Diagnostics Guide",
        "  start_here: bioetl diagnostics guide",
        (
            "  metrics/admin: bioetl diagnostics metrics "
            "[--json]",
        ),
        (
            "  health: bioetl diagnostics health "
            "[--provider <provider>] [--json]"
        ),
        (
            "  run: bioetl diagnostics run --run-id <run-id> "
            "[--limit 100] [--format text|json|yaml]"
        ),
        (
            "  checkpoint: bioetl diagnostics checkpoint --pipeline <pipeline> "
            "[--run-id <run-id>] [--audit-limit 100] [--format text|json|yaml]"
        ),
        (
            "  manifest: bioetl diagnostics manifest <run-id|manifest-id> "
            "[--format text|json|yaml]"
        ),
        (
            "  quarantine: bioetl diagnostics quarantine --pipeline <pipeline> "
            "[--run-id <run-id>] [--group-by reason-signature] [--json]"
        ),
        "",
        "Observability verification workflow:",
        "  1. bioetl diagnostics metrics [--json]",
        "  2. bioetl diagnostics health [--json]",
        "  3. python -m scripts.engineering.qa report-observability-metric-inventory --json",
        (
            "  4. compare inventory output with "
            "grafana/prometheus-rules/bioetl_observability.yml and shipped dashboards"
        ),
        "",
        "Metrics server startup is auto-managed during pipeline runs when metrics are enabled.",
        "Pushgateway publication is best-effort on run completion; inspect current config with diagnostics metrics.",
        "",
        "Legacy command groups remain supported:",
        "  health check",
        "  checkpoint inspect",
        "  checkpoint audit-run",
        "  run-manifest show",
        "  quarantine stats",
    ]


def _echo_health_results(
    results: dict[str, dict[str, str | float | int | None]],
    *,
    output_json: bool,
) -> None:
    """Render provider health results with the canonical health formatting."""
    if output_json:
        click.echo(render_health_results_json(results))
    else:
        click.echo("Running health checks...")
        for line in build_health_result_lines(results):
            click.echo(line)
        if all_health_results_healthy(results):
            click.echo("\nAll providers healthy.")
        else:
            click.echo("\nSome providers unhealthy.")


def _render_guide_lines(lines: Iterable[str]) -> None:
    """Emit guide text lines in stable order."""
    for line in lines:
        click.echo(line)


def _build_metrics_profile_lines(profile: MetricsOperatorProfile) -> list[str]:
    """Render the canonical operator-facing metrics/admin workflow summary."""
    started_at = (
        profile.metrics_started_at.isoformat()
        if profile.metrics_started_at is not None
        else "not_running"
    )
    endpoint = profile.metrics_endpoint or "disabled"
    running = "running" if profile.metrics_server_running else "stopped"
    return [
        "BioETL Metrics Diagnostics",
        f"  metrics_enabled: {str(profile.metrics_enabled).lower()}",
        f"  metrics_server_enabled: {str(profile.metrics_server_enabled).lower()}",
        f"  metrics_server_status: {running}",
        f"  metrics_endpoint: {endpoint}",
        f"  metrics_started_at: {started_at}",
        f"  metrics_server_mode: {profile.metrics_server_mode}",
        f"  pushgateway_mode: {profile.pushgateway_mode}",
        f"  pushgateway_gateway: {profile.pushgateway_gateway}",
        f"  tracing_enabled: {str(profile.tracing_enabled).lower()}",
        f"  audit_enabled: {str(profile.audit_enabled).lower()}",
        "",
        "Operator workflow:",
        "  inspect metrics/admin state: bioetl diagnostics metrics [--json]",
        "  inspect provider health: bioetl diagnostics health [--json]",
        (
            "  reconcile metric inventory: "
            "python -m scripts.engineering.qa report-observability-metric-inventory --json"
        ),
        (
            "  compare rules/dashboards: "
            "grafana/prometheus-rules/bioetl_observability.yml + shipped dashboard JSON"
        ),
        "  inspect one run: bioetl diagnostics run --run-id <run-id>",
        "  inspect checkpoint state: bioetl diagnostics checkpoint --pipeline <pipeline>",
    ]


@click.group()  # type: ignore[untyped-decorator]
def diagnostics() -> None:
    """Unified operator diagnostics across health, checkpoints, manifests, and quarantine."""


@diagnostics.command("guide")  # type: ignore[untyped-decorator]
def diagnostics_guide() -> None:
    """Show the canonical diagnostics discovery and routing guide."""
    _render_guide_lines(_build_diagnostics_guide_lines())


@diagnostics.command("health")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--provider",
    "-p",
    multiple=True,
    help="Provider name(s) to check; omit to check all configured providers",
)
@click.option(  # type: ignore[untyped-decorator]
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def diagnostics_health(provider: tuple[str, ...], output_json: bool) -> None:
    """Run provider health diagnostics from the unified operator entrypoint."""
    bundle = get_observability_diagnostics_bundle()

    async def _run() -> JsonDict:
        providers_list = list(provider) if provider else None
        summary = await bundle.health_service.check_providers(providers=providers_list)
        return summary.to_dict()

    results = asyncio.run(_run())
    _echo_health_results(results, output_json=output_json)
    if output_json:
        return
    if not all_health_results_healthy(results):
        raise SystemExit(ExitCode.FAIL)


@diagnostics.command("metrics")  # type: ignore[untyped-decorator]
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")  # type: ignore[untyped-decorator]
def diagnostics_metrics(output_json: bool) -> None:
    """Show the canonical metrics/admin observability workflow summary."""
    profile = get_metrics_operator_profile()
    if output_json:
        click.echo(json.dumps(profile.to_dict(), indent=2, default=str))
        return
    _render_guide_lines(_build_metrics_profile_lines(profile))


@diagnostics.command("run")  # type: ignore[untyped-decorator]
@click.option("--run-id", required=True, help="Pipeline RUN_ID to inspect")  # type: ignore[untyped-decorator]
@click.option("--limit", default=100, show_default=True, help="Maximum audit entries")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diagnostics_run(run_id: str, limit: int, output_format: str) -> None:
    """Inspect one pipeline run across audit and run-manifest diagnostics surfaces."""
    bundle = get_observability_diagnostics_bundle()

    async def _inspect() -> None:
        try:
            result = await bundle.workflow_service.inspect_audit_run(run_id, limit=limit)
        except ValueError as exc:
            echo_error("Run diagnostics failed", str(exc))
            return
        emit_inspection_payload(
            result.to_dict(),
            output_format,
            text_renderer=_render_checkpoint_payload,
        )

    asyncio.run(_inspect())


@diagnostics.command("checkpoint")  # type: ignore[untyped-decorator]
@click.option("--pipeline", required=True, help="Pipeline name")  # type: ignore[untyped-decorator]
@click.option("--run-id", default=None, help="Optional RUN_ID override")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--audit-limit",
    default=100,
    show_default=True,
    help="Maximum audit entries",
)
@click.option(  # type: ignore[untyped-decorator]
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diagnostics_checkpoint(
    pipeline: str,
    run_id: str | None,
    audit_limit: int,
    output_format: str,
) -> None:
    """Inspect checkpoint state with correlated audit and run-manifest context."""
    bundle = get_observability_diagnostics_bundle()

    async def _inspect() -> None:
        try:
            result = await bundle.workflow_service.inspect_checkpoint_workflow(
                pipeline,
                run_id=run_id,
                audit_limit=audit_limit,
            )
        except ValueError as exc:
            echo_error("Checkpoint diagnostics failed", str(exc))
            return
        emit_inspection_payload(
            result.to_dict(),
            output_format,
            text_renderer=_render_checkpoint_payload,
        )

    asyncio.run(_inspect())


@diagnostics.command("manifest")  # type: ignore[untyped-decorator]
@click.argument("identifier")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text", help="Output format"
)
def diagnostics_manifest(identifier: str, output_format: str) -> None:
    """Inspect one run manifest and its ledger diagnostics."""
    bundle = get_observability_diagnostics_bundle()
    _emit_manifest_payload(
        bundle.run_manifest_service,
        identifier=identifier,
        output_format=output_format,
    )


def _emit_manifest_payload(
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


@diagnostics.command("quarantine")  # type: ignore[untyped-decorator]
@click.option("--pipeline", required=True, help="Pipeline name")  # type: ignore[untyped-decorator]
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")  # type: ignore[untyped-decorator]
@click.option("--error-code", help="Scope stats to one error code")  # type: ignore[untyped-decorator]
@click.option("--run-id", help="Scope stats to one pipeline run ID")  # type: ignore[untyped-decorator]
@click.option(  # type: ignore[untyped-decorator]
    "--silver-filter-only",
    is_flag=True,
    help="Shortcut for --error-code FILTERED_OUT_SILVER",
)
@click.option(  # type: ignore[untyped-decorator]
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
)
@click.option(  # type: ignore[untyped-decorator]
    "--top",
    type=int,
    default=10,
    show_default=True,
    help="Maximum grouping entries to display",
)
def diagnostics_quarantine(
    pipeline: str,
    output_json: bool,
    error_code: str | None,
    run_id: str | None,
    silver_filter_only: bool,
    group_by: str | None,
    top: int,
) -> None:
    """Inspect quarantine statistics from the unified operator entrypoint."""
    bundle = get_observability_diagnostics_bundle()
    resolved_error_code = "FILTERED_OUT_SILVER" if silver_filter_only else error_code
    _show_quarantine_stats(
        get_quarantine_manager(pipeline),
        pipeline=pipeline,
        output_json=output_json,
        error_code=resolved_error_code,
        top=top,
        group_by=group_by,
        run_id=run_id,
        run_manifest_service=bundle.run_manifest_service if run_id else None,
    )


COMMANDS = (
    diagnostics_guide,
    diagnostics_health,
    diagnostics_metrics,
    diagnostics_run,
    diagnostics_checkpoint,
    diagnostics_manifest,
    diagnostics_quarantine,
)
