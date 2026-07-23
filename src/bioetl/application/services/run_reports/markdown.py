"""Human-readable markdown renderers for run reports."""

from __future__ import annotations

from bioetl.domain.run_reports.models import PipelineRunReport, WorkflowRunReport


def render_pipeline_run_report_markdown(report: PipelineRunReport) -> str:
    """Render a compact operator-facing pipeline funnel report."""
    identity = report.identity
    lines: list[str] = [
        f"# Pipeline run report: {identity.get('pipeline_name', '?')}",
        "",
        f"- **run_id:** `{identity.get('run_id', '')}`",
        f"- **status:** {identity.get('status', '')}",
        f"- **run_type:** {identity.get('run_type', '')}",
        f"- **tracking:** {report.tracking_coverage.value}",
        f"- **catalog:** {report.reason_catalog_version}",
        "",
        "## Funnel",
        "",
        "| Stage | In | Out | Removed | Balance | Tracking | Top reasons |",
        "|-------|---:|----:|--------:|---------|----------|-------------|",
    ]
    for row in report.funnel:
        top = ", ".join(
            f"{item.reason_code}={item.count}" for item in row.removals[:3]
        ) or "—"
        lines.append(
            f"| {row.stage_id} | {row.records_in} | {row.records_out} | "
            f"{row.removed_total} | {row.balance_status.value} | "
            f"{row.tracking.value} | {top} |"
        )

    layers = report.layers
    lines.extend(
        [
            "",
            "## Layers",
            "",
            f"- bronze: **{layers.bronze_records}**",
            f"- silver valid: **{layers.silver_valid}** "
            f"(filtered={layers.silver_filtered_out}, "
            f"quarantined={layers.silver_quarantined}, "
            f"skipped={layers.silver_skipped}, "
            f"dedup={layers.silver_deduplicated})",
            f"- gold written: **{layers.gold_written}** "
            f"(excluded={layers.gold_excluded_by_contract}, "
            f"quarantined={layers.gold_quarantined}, "
            f"skipped={layers.gold_skipped}, "
            f"dedup={layers.gold_deduplicated})",
            "",
            "## Top reasons",
            "",
        ]
    )
    if report.reasons_top_n:
        for item in report.reasons_top_n:
            lines.append(
                f"- `{item.get('reason_code')}` "
                f"({item.get('outcome')}): {item.get('count')}"
            )
    else:
        lines.append("- (none)")

    recon = report.reconciliation
    lines.extend(
        [
            "",
            "## Reconciliation",
            "",
            f"- silver vs bronze: **{recon.get('silver_vs_bronze_status')}** "
            f"(delta={recon.get('silver_delta')})",
            f"- gold vs silver: **{recon.get('gold_vs_silver_status')}** "
            f"(delta={recon.get('gold_delta')})",
            "",
        ]
    )
    return "\n".join(lines)


def render_workflow_run_report_markdown(report: WorkflowRunReport) -> str:
    """Render a compact workflow extraction rollup."""
    identity = report.identity
    lines: list[str] = [
        f"# Workflow run report: {identity.get('workflow_name', '?')}",
        "",
        f"- **workflow_run_id:** `{identity.get('workflow_run_id') or ''}`",
        f"- **status:** {identity.get('status', '')}",
        f"- **extracted total:** {report.totals.get('records_extracted_sum', 0)}",
        "",
        "## Steps",
        "",
        "| Step | Pipeline | Status | Extracted | Silver | Gold |",
        "|------|----------|--------|----------:|-------:|-----:|",
    ]
    for row in report.execution:
        silver = "—" if row.records_silver is None else str(row.records_silver)
        gold = "—" if row.records_gold is None else str(row.records_gold)
        lines.append(
            f"| {row.step_id} | {row.pipeline_name or '—'} | {row.status} | "
            f"{row.records_extracted} | {silver} | {gold} |"
        )
    totals = report.totals
    lines.extend(
        [
            "",
            "## Totals",
            "",
            f"- planned: {totals.get('steps_planned')}",
            f"- succeeded: {totals.get('steps_succeeded')}",
            f"- failed: {totals.get('steps_failed')}",
            f"- skipped: {totals.get('steps_skipped')}",
            f"- records_extracted_sum: **{totals.get('records_extracted_sum')}**",
            "",
        ]
    )
    return "\n".join(lines)
