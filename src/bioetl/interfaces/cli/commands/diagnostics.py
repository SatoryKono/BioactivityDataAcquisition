"""Unified operator-facing diagnostics entrypoint for BioETL CLI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import click

from bioetl.interfaces.cli.commands.domains.diagnostics.contract_checks import (
    render_contract_check_report,
    run_observability_contract_checks,
)
from bioetl.interfaces.cli.commands.domains.diagnostics.operations import (
    emit_checkpoint_diagnostics,
    emit_forensic_run_diff,
    emit_manifest_payload,
    emit_metrics_profile,
    emit_quarantine_stats,
    emit_run_dossier,
    run_health_diagnostics,
)
from bioetl.interfaces.cli.commands.domains.diagnostics.rendering import (
    build_diagnostics_guide_lines,
    render_guide_lines,
)
from bioetl.interfaces.cli.commands.domains.quarantine.support import (
    _QuarantineRuntimeService,
)
from bioetl.interfaces.cli.commands.domains.shared.inspection_commands import (
    add_audit_run_options,
    add_checkpoint_workflow_options,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.forensic_diff_service import (
        ForensicRunDiffService,
    )
    from bioetl.application.services.control_plane.manifest.inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.composition.observability_api import (
        MetricsOperatorProfile,
        ObservabilityDiagnosticsBundle,
    )

__all__ = [
    "COMMANDS",
    "diagnostics",
    "diagnostics_checkpoint",
    "diagnostics_contract_checks",
    "diagnostics_dossier",
    "diagnostics_forensic_diff",
    "diagnostics_guide",
    "diagnostics_health",
    "diagnostics_manifest",
    "diagnostics_metrics",
    "diagnostics_quarantine",
    "diagnostics_run",
    "get_metrics_operator_profile",
    "get_observability_diagnostics_bundle",
    "get_quarantine_runtime_service",
]

SILVER_FILTER_ERROR_CODE = "FILTERED_OUT_SILVER"
SILVER_FILTER_ALIAS_HELP = (
    "Legacy alias for --error-code FILTERED_OUT_SILVER; Silver structural "
    "rejects only, not Gold contract/semantic rejects."
)


def get_observability_diagnostics_bundle() -> ObservabilityDiagnosticsBundle:
    """Load the canonical operator diagnostics bundle on demand."""
    from bioetl.composition.observability_api import (
        get_observability_diagnostics_bundle as _impl,
    )

    return _impl()


def get_metrics_operator_profile() -> MetricsOperatorProfile:
    """Load the canonical operator-facing metrics diagnostics profile."""
    from bioetl.composition.observability_api import (
        get_metrics_operator_profile as _impl,
    )

    return _impl()


def get_quarantine_runtime_service(pipeline: str) -> _QuarantineRuntimeService:
    """Load the quarantine runtime service through composition on demand."""
    from bioetl.interfaces.cli.commands.domains.quarantine.runtime_access import (
        get_quarantine_runtime_service as _impl,
    )

    return cast(_QuarantineRuntimeService, _impl(pipeline))


def get_forensic_run_diff_service() -> ForensicRunDiffService:
    """Load the canonical forensic diff service on demand."""
    from bioetl.composition.control_plane_api import (
        get_forensic_run_diff_service as _impl,
    )

    return _impl()


def _build_diagnostics_guide_lines() -> list[str]:
    """Compatibility seam for diagnostics guide rendering tests."""
    return build_diagnostics_guide_lines()


@click.group()
def diagnostics() -> None:
    """Unified operator diagnostics across health, checkpoints, manifests, and quarantine."""


@diagnostics.command("guide")
def diagnostics_guide() -> None:
    """Show the canonical diagnostics discovery and routing guide."""
    render_guide_lines(build_diagnostics_guide_lines())


@diagnostics.command("health")
@click.option(
    "--provider",
    "-p",
    multiple=True,
    help="Provider name(s) to check; omit to check all configured providers",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def diagnostics_health(provider: tuple[str, ...], output_json: bool) -> None:
    """Run provider health diagnostics from the unified operator entrypoint."""
    run_health_diagnostics(
        get_observability_diagnostics_bundle(),
        provider=provider,
        output_json=output_json,
    )


@diagnostics.command("metrics")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def diagnostics_metrics(output_json: bool) -> None:
    """Show the canonical metrics/admin observability workflow summary."""
    emit_metrics_profile(get_metrics_operator_profile(), output_json=output_json)


def _emit_run_dossier(
    *,
    run_id: str | None,
    manifest_id: str | None,
    limit: int,
    output_format: str,
) -> None:
    """Emit one-run dossier using the canonical workflow service."""
    emit_run_dossier(
        get_observability_diagnostics_bundle(),
        run_id=run_id,
        manifest_id=manifest_id,
        limit=limit,
        output_format=output_format,
    )


@diagnostics.command("run")
@add_audit_run_options
def diagnostics_run(run_id: str, limit: int, output_format: str) -> None:
    """Inspect one pipeline run as a bounded forensic dossier."""
    _emit_run_dossier(
        run_id=run_id,
        manifest_id=None,
        limit=limit,
        output_format=output_format,
    )


@diagnostics.command("dossier")
@click.option("--run-id", default=None, help="Pipeline RUN_ID to inspect")
@click.option("--manifest-id", default=None, help="MANIFEST_ID to inspect")
@click.option(
    "--limit",
    default=100,
    show_default=True,
    help="Maximum audit entries",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diagnostics_dossier(
    run_id: str | None,
    manifest_id: str | None,
    limit: int,
    output_format: str,
) -> None:
    """Inspect one pipeline run through the public dossier entrypoint."""
    _emit_run_dossier(
        run_id=run_id,
        manifest_id=manifest_id,
        limit=limit,
        output_format=output_format,
    )


@diagnostics.command("contract-checks")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def diagnostics_contract_checks(output_json: bool) -> None:
    """Run public observability contract checks."""
    report = run_observability_contract_checks()
    if output_json:
        click.echo(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        click.echo(render_contract_check_report(report))
    if not report.passed:
        raise SystemExit(ExitCode.FAIL)


@diagnostics.command("checkpoint")
@add_checkpoint_workflow_options
def diagnostics_checkpoint(
    pipeline: str,
    run_id: str | None,
    audit_limit: int,
    output_format: str,
) -> None:
    """Inspect checkpoint state with correlated audit and run-manifest context."""
    emit_checkpoint_diagnostics(
        get_observability_diagnostics_bundle(),
        pipeline=pipeline,
        run_id=run_id,
        audit_limit=audit_limit,
        output_format=output_format,
    )


@diagnostics.command("manifest")
@click.argument("identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diagnostics_manifest(identifier: str, output_format: str) -> None:
    """Inspect one run manifest and its ledger diagnostics."""
    bundle = get_observability_diagnostics_bundle()
    emit_manifest_payload(
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
    emit_manifest_payload(service, identifier=identifier, output_format=output_format)


@diagnostics.command("forensic-diff")
@click.argument("left_identifier")
@click.argument("right_identifier")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def diagnostics_forensic_diff(
    left_identifier: str,
    right_identifier: str,
    output_format: str,
) -> None:
    """Compare two runs or manifests across forensic evidence surfaces."""
    emit_forensic_run_diff(
        get_forensic_run_diff_service(),
        left_identifier=left_identifier,
        right_identifier=right_identifier,
        output_format=output_format,
    )


@diagnostics.command("quarantine")
@click.option("--pipeline", required=True, help="Pipeline name")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--error-code", help="Scope stats to one error code")
@click.option("--run-id", help="Scope stats to one pipeline run ID")
@click.option(
    "--silver-filter-only",
    is_flag=True,
    help=SILVER_FILTER_ALIAS_HELP,
)
@click.option(
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
@click.option(
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
    resolved_error_code = SILVER_FILTER_ERROR_CODE if silver_filter_only else error_code
    emit_quarantine_stats(
        bundle,
        get_quarantine_runtime_service(pipeline),
        pipeline=pipeline,
        output_json=output_json,
        error_code=resolved_error_code,
        top=top,
        group_by=group_by,
        run_id=run_id,
    )


COMMANDS = (
    "guide",
    "metrics",
    "health",
    "run",
    "dossier",
    "contract-checks",
    "checkpoint",
    "manifest",
    "forensic-diff",
    "quarantine",
)
