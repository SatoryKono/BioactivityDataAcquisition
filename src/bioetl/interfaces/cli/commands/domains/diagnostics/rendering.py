"""Rendering helpers for unified diagnostics CLI output."""

from __future__ import annotations

from collections.abc import Iterable

import click

from bioetl.composition.observability_api import MetricsOperatorProfile
from bioetl.interfaces.cli.commands.domains.health.rendering import (
    all_health_results_healthy,
    build_health_result_lines,
    render_health_results_json,
)

_UNAVAILABLE_LINE = "  - unavailable"


def build_diagnostics_guide_lines() -> list[str]:
    """Return the canonical operator diagnostics routing guide."""
    return [
        "BioETL Diagnostics Guide",
        "  start_here: bioetl diagnostics guide",
        "  metrics/admin: bioetl diagnostics metrics [--json]",
        "  health: bioetl diagnostics health [--provider <provider>] [--json]",
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


def echo_health_results(
    results: dict[str, dict[str, str | float | int | None]],
    *,
    output_json: bool,
) -> None:
    """Render provider health results with the canonical health formatting."""
    if output_json:
        click.echo(render_health_results_json(results))
        return
    click.echo("Running health checks...")
    for line in build_health_result_lines(results):
        click.echo(line)
    click.echo(
        "\nAll providers healthy."
        if all_health_results_healthy(results)
        else "\nSome providers unhealthy."
    )


def render_guide_lines(lines: Iterable[str]) -> None:
    """Emit guide text lines in stable order."""
    for line in lines:
        click.echo(line)


def build_metrics_profile_lines(profile: MetricsOperatorProfile) -> list[str]:
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


def render_run_dossier_payload(payload: dict[str, object]) -> str:
    """Render one-run dossier payload in human-readable form."""
    audit = payload.get("audit")
    audit_entries = audit.get("entries", []) if isinstance(audit, dict) else []
    status = payload.get("status")
    lines = [
        "Run Forensic Dossier",
        f"  run_id: {payload.get('run_id')}",
        f"  pipeline_name: {payload.get('pipeline_name')}",
    ]
    if isinstance(status, dict):
        lines.extend(_render_dossier_status_lines(status))
    lines.extend(
        ["", "Run Manifest", *_render_run_manifest_lines(payload.get("run_manifest"))]
    )
    lines.extend(
        ["", "Checkpoint", *_render_checkpoint_lines(payload.get("checkpoint"))]
    )
    lines.extend(
        ["", "Quarantine", *_render_quarantine_lines(payload.get("quarantine_summary"))]
    )
    lines.extend(["", "Lineage", *_render_lineage_lines(payload.get("lineage"))])
    lines.extend(
        ["", "Traceability", *_render_traceability_lines(payload.get("traceability"))]
    )
    lines.extend(
        [
            "",
            "Evidence Status",
            f"  missing: {payload.get('missing_evidence', [])}",
            f"  degraded: {payload.get('degraded_evidence', [])}",
        ]
    )
    lines.extend(["", "Audit Entries", *_render_audit_entry_lines(audit_entries)])
    lines.extend(
        ["", "Next Steps", *_render_next_step_lines(payload.get("next_steps", []))]
    )
    return "\n".join(lines)


def _render_dossier_status_lines(status: dict[str, object]) -> list[str]:
    return [
        f"  forensic_profile: {status.get('forensic_profile')}",
        f"  latest_status: {status.get('latest_status')}",
        f"  latest_event_type: {status.get('latest_event_type')}",
        f"  checkpoint_status: {status.get('checkpoint_status')}",
        f"  lineage_status: {status.get('lineage_status')}",
        f"  quarantine_status: {status.get('quarantine_status')}",
        f"  missing_evidence_count: {status.get('missing_evidence_count')}",
        f"  degraded_evidence_count: {status.get('degraded_evidence_count')}",
    ]


def _render_run_manifest_lines(run_manifest: object) -> list[str]:
    if not isinstance(run_manifest, dict):
        return [_UNAVAILABLE_LINE]
    lines: list[str] = []
    manifest = run_manifest.get("manifest")
    diagnostics = run_manifest.get("diagnostics")
    if isinstance(manifest, dict):
        lines.extend(
            [
                f"  manifest_id: {manifest.get('manifest_id')}",
                f"  provider: {manifest.get('provider')}",
                f"  entity: {manifest.get('entity')}",
                f"  run_type: {manifest.get('run_type')}",
            ]
        )
    if isinstance(diagnostics, dict):
        lines.extend(
            [
                f"  replay_capability: {diagnostics.get('replay_capability')}",
                f"  persistence_profile: {diagnostics.get('persistence_profile')}",
                f"  alert_signals: {diagnostics.get('alert_signals')}",
            ]
        )
    return lines or [_UNAVAILABLE_LINE]


def _render_checkpoint_lines(checkpoint: object) -> list[str]:
    if not isinstance(checkpoint, dict):
        return [_UNAVAILABLE_LINE]
    return [
        f"  checkpoint_run_id: {checkpoint.get('run_id')}",
        f"  checkpoint_metadata: {checkpoint.get('metadata')}",
    ]


def _render_quarantine_lines(quarantine_summary: object) -> list[str]:
    if not isinstance(quarantine_summary, dict):
        return [_UNAVAILABLE_LINE]
    return [
        f"  total: {quarantine_summary.get('total')}",
        f"  silver_filter_rejects: {quarantine_summary.get('silver_filter_rejects')}",
        f"  run_scope: {quarantine_summary.get('run_scope')}",
    ]


def _render_lineage_lines(lineage: object) -> list[str]:
    if not isinstance(lineage, dict):
        return [_UNAVAILABLE_LINE]
    return [
        f"  manifest_id: {lineage.get('manifest_id')}",
        f"  fragment_ids: {lineage.get('fragment_ids')}",
        f"  produced_datasets: {lineage.get('produced_datasets')}",
    ]


def _render_traceability_lines(traceability: object) -> list[str]:
    if not isinstance(traceability, dict):
        return [_UNAVAILABLE_LINE]
    return [
        f"  audit_entries_count: {traceability.get('audit_entries_count')}",
        f"  lineage_fragment_ids: {traceability.get('lineage_fragment_ids')}",
        f"  artifact_refs: {traceability.get('artifact_refs')}",
        f"  trace_ids: {traceability.get('trace_ids')}",
        f"  trace_urls: {traceability.get('trace_urls')}",
        f"  trace_links_available: {traceability.get('trace_links_available')}",
        f"  correlation_anchor_gaps: {traceability.get('correlation_anchor_gaps')}",
    ]


def _render_audit_entry_lines(audit_entries: object) -> list[str]:
    if not isinstance(audit_entries, list) or not audit_entries:
        return ["  - none"]
    lines: list[str] = []
    for entry in audit_entries:
        if not isinstance(entry, dict):
            lines.append(f"  - {entry}")
            continue
        lines.append(
            "  - "
            f"{entry.get('timestamp', '?')} "
            f"{entry.get('layer', '?')}/{entry.get('table_name', '?')} "
            f"{entry.get('operation', '?')} "
            f"records={entry.get('records_count', '?')}"
        )
    return lines


def _render_next_step_lines(next_steps: object) -> list[str]:
    if not isinstance(next_steps, list) or not next_steps:
        return ["  - none"]
    return [f"  - {step}" for step in next_steps]
