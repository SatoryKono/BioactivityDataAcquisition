"""Human-readable markdown renderers for run reports."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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
    ]
    _append_identity_details(lines, identity)

    lines.extend(
        [
            "",
            "## Funnel",
            "",
            "| Stage | In | Out | Removed | Balance | Tracking | Top reasons |",
            "|-------|---:|----:|--------:|---------|----------|-------------|",
        ]
    )
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

    _append_samples_section(lines, report)
    _append_optional_mapping_section(lines, "Failure", report.failure)
    _append_optional_mapping_section(lines, "IO", report.io)
    _append_optional_mapping_section(lines, "Quarantine", report.quarantine)
    _append_optional_mapping_section(lines, "DQ summary", report.dq_summary)
    _append_optional_mapping_section(lines, "Contract summary", report.contract_summary)
    _append_optional_mapping_section(lines, "Schema versions", report.schema_versions)
    _append_optional_mapping_section(lines, "Stage timings", report.stage_timings)
    _append_optional_mapping_section(lines, "HTTP summary", report.http_summary)
    _append_optional_mapping_section(lines, "Performance", report.performance)

    if report.artifacts:
        lines.extend(["", "## Artifacts", ""])
        for item in report.artifacts:
            kind = item.get("kind", "artifact")
            ref = item.get("ref", "")
            digest = item.get("hash")
            suffix = f" (hash={digest})" if digest else ""
            lines.append(f"- `{kind}`: `{ref}`{suffix}")

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
    ]
    if identity.get("resumed") is not None:
        lines.append(f"- **resumed:** {identity.get('resumed')}")
    if identity.get("execution_fingerprint"):
        lines.append(f"- **fingerprint:** `{identity.get('execution_fingerprint')}`")
    if identity.get("duration_seconds") is not None:
        lines.append(f"- **duration_seconds:** {identity.get('duration_seconds')}")

    lines.extend(
        [
            "",
            "## Steps",
            "",
            "| Step | Pipeline | Status | Extracted | Silver | Gold | Report |",
            "|------|----------|--------|----------:|-------:|-----:|--------|",
        ]
    )
    for row in report.execution:
        silver = "—" if row.records_silver is None else str(row.records_silver)
        gold = "—" if row.records_gold is None else str(row.records_gold)
        ref = "—" if not row.pipeline_report_ref else "`…`"
        lines.append(
            f"| {row.step_id} | {row.pipeline_name or '—'} | {row.status} | "
            f"{row.records_extracted} | {silver} | {gold} | {ref} |"
        )
        if row.pipeline_report_ref:
            lines.append(f"  - report: `{row.pipeline_report_ref}`")
        if row.top_reasons:
            reasons = ", ".join(
                f"{item.get('reason_code')}={item.get('count')}"
                for item in row.top_reasons[:3]
            )
            lines.append(f"  - top reasons: {reasons}")
        if row.skip_reason:
            lines.append(f"  - skip_reason: `{row.skip_reason}`")

    if report.plan_steps:
        lines.extend(["", "## Plan / DAG", ""])
        for step in report.plan_steps:
            deps = step.get("depends_on") or []
            dep_text = ", ".join(f"`{dep}`" for dep in deps) if deps else "—"
            lines.append(
                f"- `{step.get('step_id')}` ({step.get('kind')}) depends_on: {dep_text}"
            )
        lines.extend(["", "```mermaid", "flowchart TD"])
        for step in report.plan_steps:
            step_id = str(step.get("step_id") or "step")
            safe = _mermaid_id(step_id)
            lines.append(f'  {safe}["{step_id}"]')
        for step in report.plan_steps:
            step_id = str(step.get("step_id") or "step")
            safe = _mermaid_id(step_id)
            for dep in step.get("depends_on") or []:
                lines.append(f"  {_mermaid_id(str(dep))} --> {safe}")
        lines.append("```")

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
        ]
    )
    if totals.get("records_silver_sum") is not None:
        lines.append(f"- records_silver_sum: **{totals.get('records_silver_sum')}**")
    if totals.get("records_gold_sum") is not None:
        lines.append(f"- records_gold_sum: **{totals.get('records_gold_sum')}**")

    if report.reasons_rollup:
        lines.extend(["", "## Reasons rollup", ""])
        for item in report.reasons_rollup:
            lines.append(
                f"- `{item.get('reason_code')}` "
                f"({item.get('outcome')}): {item.get('count')}"
            )

    lines.append("")
    return "\n".join(lines)


def _append_identity_details(lines: list[str], identity: Mapping[str, Any]) -> None:
    if identity.get("manifest_id"):
        lines.append(f"- **manifest_id:** `{identity.get('manifest_id')}`")
    if identity.get("provider") or identity.get("entity"):
        lines.append(
            f"- **provider/entity:** {identity.get('provider') or '—'} / "
            f"{identity.get('entity') or '—'}"
        )
    if identity.get("started_at"):
        lines.append(f"- **started_at:** {identity.get('started_at')}")
    if identity.get("completed_at"):
        lines.append(f"- **completed_at:** {identity.get('completed_at')}")
    if identity.get("duration_seconds") is not None:
        lines.append(f"- **duration_seconds:** {identity.get('duration_seconds')}")
    if identity.get("workflow_run_id"):
        lines.append(
            f"- **workflow:** `{identity.get('workflow_id') or '—'}` / "
            f"`{identity.get('workflow_run_id')}` / "
            f"`{identity.get('workflow_step_id') or '—'}`"
        )


def _append_samples_section(lines: list[str], report: PipelineRunReport) -> None:
    samples: list[str] = []
    for row in report.funnel:
        for removal in row.removals:
            if not removal.sample_refs:
                continue
            joined = ", ".join(f"`{ref}`" for ref in removal.sample_refs[:5])
            samples.append(
                f"- `{row.stage_id}` / `{removal.reason_code}`: {joined}"
            )
    if not samples:
        return
    lines.extend(["", "## Top samples", ""])
    lines.extend(samples[:20])


def _append_optional_mapping_section(
    lines: list[str],
    title: str,
    payload: Mapping[str, Any] | None,
) -> None:
    if not payload:
        return
    lines.extend(["", f"## {title}", ""])
    for key, value in payload.items():
        if isinstance(value, (list, tuple)):
            lines.append(f"- **{key}:**")
            for item in value[:10]:
                lines.append(f"  - `{item}`")
        else:
            lines.append(f"- **{key}:** `{value}`")


def _mermaid_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value)
    return cleaned or "step"
