"""Control Plane identity evidence payload builder."""

from __future__ import annotations

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.interfaces.http.control_plane_identity.checkpoint import (
    build_checkpoint_compare,
)
from bioetl.interfaces.http.control_plane_identity.extractors import (
    build_anchor_values,
    replay_mode,
)
from bioetl.interfaces.http.control_plane_identity.formatting import (
    format_full_value,
    is_present,
    short_value,
)
from bioetl.interfaces.http.control_plane_identity.severity import (
    applicability,
    domain_severity,
    is_identity_gap,
    ui_status,
)
from bioetl.interfaces.http.control_plane_identity.source_model import (
    drilldown_target_for,
    source_model_for,
)
from bioetl.interfaces.http.control_plane_identity.specs import (
    ALLOWED_LOW_CARDINALITY_LABELS,
    ANCHOR_SPECS,
    OVERVIEW_NAMES,
    SPEC_BY_NAME,
)
from bioetl.interfaces.http.control_plane_identity.types import (
    IDENTITY_EVIDENCE_CONTRACT,
    AnchorSpec,
    LedgerEntryProvider,
)


def build_control_plane_identity_evidence_payload(
    *,
    requested_pipeline: str,
    resolved_manifest: RunManifest | None,
    selected_pipelines: tuple[str, ...],
    selected_run_id: str | None,
    selected_run_types: tuple[str, ...],
    resolved_via: str,
    ledger_port: LedgerEntryProvider | None,
    checkpoint_metadata: dict[str, object] | None = None,
    view: str = "anchors",
    priority: str | None = None,
) -> dict[str, object]:
    """Build the dedicated Control Plane identity evidence payload."""
    ledger_entries = ledger_entries_for(resolved_manifest, ledger_port)
    checkpoint_compare = build_checkpoint_compare(
        resolved_manifest,
        checkpoint_metadata=checkpoint_metadata,
    )
    values = build_anchor_values(
        resolved_manifest,
        ledger_entries=ledger_entries,
        checkpoint_status=str(checkpoint_compare["status"]),
    )
    anchors = build_anchor_rows(
        manifest=resolved_manifest,
        ledger_entries=ledger_entries,
        values=values,
        checkpoint_status=str(checkpoint_compare["status"]),
    )
    summary = build_summary(
        manifest=resolved_manifest,
        anchors=anchors,
        values=values,
        checkpoint_status=str(checkpoint_compare["status"]),
        resolved_via=resolved_via,
    )
    rows = select_rows(
        view=view,
        priority=priority,
        anchors=anchors,
        checkpoint_rows=checkpoint_compare["rows"],
    )
    return {
        "contract": IDENTITY_EVIDENCE_CONTRACT,
        "pipeline": requested_pipeline,
        "run_type": list(selected_run_types),
        "selected_run_id": selected_run_id,
        "resolved_via": resolved_via,
        "summary": summary,
        "anchors": anchors,
        "checkpoint_compare": checkpoint_compare,
        "identity_diagnostics": build_identity_diagnostics(
            anchors=anchors,
            values=values,
            checkpoint_status=str(checkpoint_compare["status"]),
        ),
        "rows": rows,
        "forbidden_prometheus_label_policy": {
            "high_cardinality_ids_must_not_be_labels": True,
            "allowed_low_cardinality_labels": ALLOWED_LOW_CARDINALITY_LABELS,
        },
        "scope": {
            "selected_pipelines": list(selected_pipelines),
            "aggregate_scope_requires_exact_run_id": (
                resolved_via == "aggregate_scope_requires_exact_run_id"
            ),
        },
    }


def ledger_entries_for(
    manifest: RunManifest | None,
    ledger_port: LedgerEntryProvider | None,
) -> tuple[RunLedgerEntry, ...]:
    if manifest is None or ledger_port is None:
        return ()
    return tuple(ledger_port.list_entries(manifest.manifest_id))


def build_anchor_rows(
    *,
    manifest: RunManifest | None,
    ledger_entries: tuple[RunLedgerEntry, ...],
    values: dict[str, object | None],
    checkpoint_status: str,
) -> list[dict[str, object]]:
    rows = [
        build_anchor_row(
            spec,
            value=values.get(spec.name),
            manifest=manifest,
            ledger_entries=ledger_entries,
            checkpoint_status=checkpoint_status,
        )
        for spec in ANCHOR_SPECS
    ]
    graph_gap_rows = identity_graph_gap_rows(rows)
    graph_gap_count = len(graph_gap_rows)
    graph_gap_names = [str(row["name"]) for row in graph_gap_rows]
    diagnostic_gap_count = gap_count_from_mapping(values.get("correlation_anchor_gaps"))
    diagnostic_complete = values.get("identity_graph_complete")
    gap_count = graph_gap_count + diagnostic_gap_count
    graph_complete = gap_count == 0 and diagnostic_complete is not False
    graph_status = "complete"
    if not graph_complete:
        gap_names = ", ".join(graph_gap_names[:6])
        graph_status = f"incomplete ({gap_count} gaps"
        if gap_names:
            graph_status = f"{graph_status}: {gap_names}"
        graph_status = f"{graph_status})"
    return [
        graph_status_row if row["name"] == "identity_graph_complete" else row
        for row in rows
        for graph_status_row in (
            build_anchor_row(
                SPEC_BY_NAME["identity_graph_complete"],
                value=graph_status,
                manifest=manifest,
                ledger_entries=ledger_entries,
                checkpoint_status=checkpoint_status,
            ),
        )
    ]


def build_anchor_row(
    spec: AnchorSpec,
    *,
    value: object | None,
    manifest: RunManifest | None,
    ledger_entries: tuple[RunLedgerEntry, ...],
    checkpoint_status: str,
) -> dict[str, object]:
    anchor_applicability = applicability(spec.name, manifest)
    applicable = anchor_applicability == "APPLICABLE"
    present = is_present(value)
    domain_status = domain_severity(
        spec,
        value=value,
        present=present,
        manifest=manifest,
        ledger_entries=ledger_entries,
        checkpoint_status=checkpoint_status,
        applicable=applicable,
    )
    rendered_ui_status = ui_status(domain_status)
    missing_text = "missing" if applicable else anchor_applicability
    value_full = format_full_value(value) if present else missing_text
    copy_enabled = bool(spec.copy and present and applicable)
    source_model = source_model_for(spec.name)
    drilldown_target = drilldown_target_for(spec.name, value_full)
    return {
        "priority": spec.priority,
        "name": spec.name,
        "label": spec.label,
        "source": spec.source,
        "source_type": source_model.source_type,
        "source_quality": source_model.source_quality,
        "format": spec.value_format,
        "why": spec.why,
        "rendering": spec.rendering,
        "value_short": short_value(value) if present else anchor_applicability,
        "value_full": value_full,
        "copy": copy_enabled,
        "copy_mode": "full_value" if copy_enabled else "none",
        "copy_value": value_full if copy_enabled else "",
        "drilldown": spec.drilldown,
        "drilldown_type": drilldown_target.target_type,
        "drilldown_target": drilldown_target.target_template,
        "drilldown_label": drilldown_target.label,
        "missing_severity": domain_status,
        "ui_status": rendered_ui_status,
        "identity_gap": (
            False
            if spec.name == "identity_graph_complete"
            else is_identity_gap(domain_status)
        ),
        "present": present,
        "status": rendered_ui_status,
    }


def build_summary(
    *,
    manifest: RunManifest | None,
    anchors: list[dict[str, object]],
    values: dict[str, object | None],
    checkpoint_status: str,
    resolved_via: str,
) -> dict[str, object]:
    gap_rows = identity_evidence_gap_rows(anchors)
    graph_gap_rows = identity_graph_gap_rows(anchors)
    diagnostic_gap_count = gap_count_from_mapping(values.get("correlation_anchor_gaps"))
    critical = any(row["ui_status"] == "CRIT" for row in gap_rows)
    warning = any(row["ui_status"] == "WARN" for row in gap_rows)
    overall = "CRIT" if critical else "WARN" if warning else "OK"
    if manifest is None:
        overall = "UNKNOWN"
    return {
        "overall_status": overall,
        "identity_graph_complete": (
            not graph_gap_rows
            and diagnostic_gap_count == 0
            and values.get("identity_graph_complete") is not False
            and manifest is not None
        ),
        "identity_gap_count": len(graph_gap_rows) + diagnostic_gap_count,
        "evidence_gap_count": len(gap_rows) + diagnostic_gap_count,
        "correlation_anchor_gaps": values.get("correlation_anchor_gaps") or {},
        "exact_replay_blockers": values.get("exact_replay_blockers") or [],
        "checkpoint_anchor_status": checkpoint_status,
        "replay_mode": None if manifest is None else replay_mode(manifest),
        "resolved_via": resolved_via,
    }


def identity_graph_gap_rows(
    anchors: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return gaps that make the identity graph incomplete, not optional detail gaps."""
    return [
        row
        for row in anchors
        if row["identity_gap"] is True
        and row["name"] != "identity_graph_complete"
        and (row["priority"] == "P0" or row["missing_severity"] == "FAILING")
    ]


def identity_evidence_gap_rows(
    anchors: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return actionable evidence gaps without counting the summary row itself."""
    return [
        row
        for row in anchors
        if row["identity_gap"] is True and row["name"] != "identity_graph_complete"
    ]


def build_identity_diagnostics(
    *,
    anchors: list[dict[str, object]],
    values: dict[str, object | None],
    checkpoint_status: str,
) -> dict[str, object]:
    """Return top-level diagnostics for dashboard and runbook consumers."""
    gap_rows = identity_evidence_gap_rows(anchors)
    return {
        "identity_gap_names": [str(row["name"]) for row in gap_rows],
        "identity_gap_count": len(gap_rows)
        + gap_count_from_mapping(values.get("correlation_anchor_gaps")),
        "correlation_anchor_gaps": values.get("correlation_anchor_gaps") or {},
        "exact_replay_blockers": values.get("exact_replay_blockers") or [],
        "checkpoint_anchor_status": checkpoint_status,
    }


def gap_count_from_mapping(value: object | None) -> int:
    if not isinstance(value, dict):
        return 0
    count = 0
    for item in value.values():
        if isinstance(item, int | float):
            count += int(item)
        elif item:
            count += 1
    return count


def select_rows(
    *,
    view: str,
    priority: str | None,
    anchors: list[dict[str, object]],
    checkpoint_rows: object,
) -> list[dict[str, object]]:
    normalized_view = view.strip().lower()
    selected = anchors
    if normalized_view == "overview":
        selected = [row for row in anchors if row["name"] in OVERVIEW_NAMES]
    elif normalized_view == "gaps":
        selected = [row for row in anchors if row["identity_gap"] is True]
    elif normalized_view == "copy_values":
        selected = [row for row in anchors if row["copy"] is True]
    elif normalized_view == "checkpoint_compare":
        return list(checkpoint_rows) if isinstance(checkpoint_rows, list) else []
    if priority:
        selected = [row for row in selected if row["priority"] == priority.upper()]
    return selected
