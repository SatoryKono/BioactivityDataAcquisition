"""Compact FK scope evidence, independent of Saved Evidence and replay verdicts."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.run_reports.selected_status import (
    parent_binding_gap,
    resolve_child_workflow_binding,
)
from bioetl.interfaces.http.run_report_ops import load_workflow_run_report_payload

_BINDING_CAPTIONS = {
    "binding_not_recorded": "Parent workflow binding not recorded",
    "identity_not_recorded": "Parent workflow identity not recorded",
    "identity_mismatch": "Parent workflow identity mismatch",
    "child_binding_mismatch": "Parent workflow child binding mismatch",
}


def unavailable_reconciliation(reason: str) -> list[dict[str, str]]:
    """Never manufacture complete-reference semantics from missing evidence."""
    return [
        {
            "step_id": "—",
            "mode": "Not recorded",
            "scope": "UNKNOWN",
            "pins": "UNKNOWN",
            "limit": "UNKNOWN",
            "result": "UNKNOWN",
            "meaning": reason,
        }
    ]


def _count(value: object) -> str:
    return str(value) if type(value) is int and value >= 0 else "UNKNOWN"


def _pin(recon: dict[str, object], side: str) -> tuple[str, str]:
    table = str(recon.get(f"{side}_table") or "UNKNOWN")
    layer = str(recon.get(f"{side}_layer") or "UNKNOWN")
    snapshots = recon.get("input_snapshots")
    entry = snapshots.get(f"{layer}:{table}") if isinstance(snapshots, dict) else None
    if not isinstance(entry, dict):
        return f"{layer}:{table}@UNKNOWN", "UNKNOWN"
    return f"{layer}:{table}@{_count(entry.get('version'))}", _count(entry.get("limit"))


def _display_row(step: dict[str, object], recon: dict[str, object]) -> dict[str, str]:
    mode = recon.get("reconciliation_mode")
    source, source_limit = _pin(recon, "source")
    reference, reference_limit = _pin(recon, "reference")
    action = (
        "expired" if recon.get("mutation_mode") == "gold_scd2_expiry" else "deleted"
    )
    if recon.get("dry_run") is True:
        action = "dry run; removed"
    deleted, scanned, retained = (
        _count(recon.get(key))
        for key in ("orphan_rows_deleted", "scanned_rows", "retained_rows")
    )
    if mode == "selected-snapshot":
        meaning = "Orphan = no match in selected reference; completeness: "
        meaning += str(recon.get("reference_completeness") or "UNKNOWN")
    else:
        meaning = "Reference completeness: " + str(
            recon.get("reference_completeness") or "UNKNOWN"
        )
    return {
        "step_id": str(step.get("step_id") or "—"),
        "mode": str(mode),
        "scope": f"{recon.get('source_scope') or 'UNKNOWN'} → {recon.get('reference_scope') or 'UNKNOWN'}",
        "pins": f"{source} → {reference}",
        "limit": f"source {source_limit}; reference {reference_limit}",
        "result": f"{action} {deleted}/{scanned}; retained {retained}",
        "meaning": meaning,
    }


def reconciliation_display(payload: dict[str, object]) -> list[dict[str, str]]:
    """Project persisted parent transforms without exposing row membership maps."""
    execution = payload.get("execution")
    if not isinstance(execution, list):
        return unavailable_reconciliation("FK reconciliation evidence not recorded")
    rows = []
    for step in execution:
        if not isinstance(step, dict):
            continue
        recon = step.get("reconciliation")
        if not isinstance(recon, dict):
            continue
        mode = recon.get("reconciliation_mode")
        if not isinstance(mode, str) or mode not in {
            "selected-snapshot",
            "complete-reference",
        }:
            unknown = unavailable_reconciliation(
                "FK reconciliation mode absent or unsupported"
            )[0]
            unknown["step_id"] = str(step.get("step_id") or "—")
            rows.append(unknown)
        else:
            rows.append(_display_row(step, recon))
    return rows or unavailable_reconciliation("FK reconciliation evidence not recorded")


def _workflow_binding(report: dict[str, object]) -> dict[str, object]:
    observations = report.get("observations")
    workflow = observations.get("Workflow") if isinstance(observations, dict) else None
    facts = workflow.get("facts") if isinstance(workflow, dict) else None
    return facts if isinstance(facts, dict) else {}


def linked_reconciliation_display(
    report: dict[str, object], root: Path | None
) -> list[dict[str, str]]:
    """Read the exact parent after the child's frozen assessment was verified.

    This separate display is parent persisted evidence, never a promotion of the
    child's independently verified Saved Evidence or replay assessment.
    """
    facts = _workflow_binding(report)
    resolved = resolve_child_workflow_binding(
        facts.get("identity"),
        report.get("identity"),
        facts.get("step_id"),
    )
    if isinstance(resolved, str):
        return unavailable_reconciliation(_BINDING_CAPTIONS[resolved])
    name, run_id, step_id, child_run_id, child_pipeline_name = resolved
    try:
        parent = load_workflow_run_report_payload(
            workflow_name=name, workflow_run_id=run_id, root=root
        )
    except (ValueError, OSError):
        return unavailable_reconciliation(
            "Parent workflow evidence corrupt or unreadable"
        )
    if parent is None:
        return unavailable_reconciliation("Parent workflow report missing")
    gap = parent_binding_gap(
        workflow_name=name,
        workflow_run_id=run_id,
        parent_identity=parent.get("identity"),
        parent_execution=parent.get("execution"),
        step_id=step_id,
        child_run_id=child_run_id,
        child_pipeline_name=child_pipeline_name,
    )
    if gap is not None:
        return unavailable_reconciliation(_BINDING_CAPTIONS[gap])
    return reconciliation_display(parent)
