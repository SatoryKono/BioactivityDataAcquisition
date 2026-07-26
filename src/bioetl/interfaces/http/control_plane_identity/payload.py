"""Control Plane identity evidence payload builder.

Legacy HTTP contract compatibility layer - sunset date: 2026-12-31
This module validates minimal legacy identity payload fields.
"""

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
from bioetl.interfaces.http.control_plane_identity.payload_selection import (
    build_identity_diagnostics,
    gap_count_from_mapping,
    identity_evidence_gap_rows,
    identity_graph_gap_rows,
    select_rows,
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


def validate_identity_payload(payload: dict[str, object]) -> tuple[bool, list[str]]:
    """Validate minimal legacy identity payload fields for HTTP callers."""
    required_fields = ("run_id", "manifest_id", "pipeline_name")
    errors = [
        f"missing required identity field: {field}"
        for field in required_fields
        if not is_present(payload.get(field))
    ]
    return not errors, errors


def ledger_entries_for(
    manifest: RunManifest | None,
    ledger_port: LedgerEntryProvider | None,
) -> tuple[RunLedgerEntry, ...]:
    if manifest is None or ledger_port is None:
        return ()
    return tuple(ledger_port.list_entries(manifest.manifest_id))


def _identity_graph_status_text(
    graph_gap_rows: list[dict[str, object]],
    diagnostic_gap_count: int,
    diagnostic_complete: object | None,
) -> str:
    gap_count = len(graph_gap_rows) + diagnostic_gap_count
    if gap_count == 0 and diagnostic_complete is not False:
        return "complete"
    gap_names = ", ".join(str(row["name"]) for row in graph_gap_rows[:6])
    if gap_names:
        return f"incomplete ({gap_count} gaps: {gap_names})"
    return f"incomplete ({gap_count} gaps)"


def _replace_identity_graph_complete_row(
    rows: list[dict[str, object]],
    graph_status_row: dict[str, object],
) -> list[dict[str, object]]:
    return [
        graph_status_row if row["name"] == "identity_graph_complete" else row
        for row in rows
    ]


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
    graph_status = _identity_graph_status_text(
        identity_graph_gap_rows(rows),
        gap_count_from_mapping(values.get("correlation_anchor_gaps")),
        values.get("identity_graph_complete"),
    )
    graph_status_row = build_anchor_row(
        SPEC_BY_NAME["identity_graph_complete"],
        value=graph_status,
        manifest=manifest,
        ledger_entries=ledger_entries,
        checkpoint_status=checkpoint_status,
    )
    return _replace_identity_graph_complete_row(rows, graph_status_row)


def _missing_anchor_text(*, applicable: bool, anchor_applicability: str) -> str:
    if applicable:
        return "missing"
    return anchor_applicability


def _rendered_value_pair(
    value: object | None,
    *,
    present: bool,
    missing_text: str,
    absent_short: str,
) -> tuple[str, str]:
    if present:
        return short_value(value), format_full_value(value)
    return absent_short, missing_text


def _copy_fields(
    *,
    copy_flag: bool,
    present: bool,
    applicable: bool,
    value_full: str,
) -> tuple[bool, str, str]:
    if not (copy_flag and present and applicable):
        return False, "none", ""
    return True, "full_value", value_full


def _anchor_value_fields(
    *,
    value: object | None,
    present: bool,
    applicable: bool,
    anchor_applicability: str,
    copy_flag: bool,
) -> tuple[str, str, bool, str, str]:
    missing_text = _missing_anchor_text(
        applicable=applicable,
        anchor_applicability=anchor_applicability,
    )
    value_short, value_full = _rendered_value_pair(
        value,
        present=present,
        missing_text=missing_text,
        absent_short=anchor_applicability,
    )
    copy_enabled, copy_mode, copy_value = _copy_fields(
        copy_flag=copy_flag,
        present=present,
        applicable=applicable,
        value_full=value_full,
    )
    return value_short, value_full, copy_enabled, copy_mode, copy_value


def _anchor_identity_gap(spec_name: str, domain_status: str) -> bool:
    if spec_name == "identity_graph_complete":
        return False
    return is_identity_gap(domain_status)


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
    value_short, value_full, copy_enabled, copy_mode, copy_value = _anchor_value_fields(
        value=value,
        present=present,
        applicable=applicable,
        anchor_applicability=anchor_applicability,
        copy_flag=spec.copy,
    )
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
        "value_short": value_short,
        "value_full": value_full,
        "copy": copy_enabled,
        "copy_mode": copy_mode,
        "copy_value": copy_value,
        "drilldown": spec.drilldown,
        "drilldown_type": drilldown_target.target_type,
        "drilldown_target": drilldown_target.target_template,
        "drilldown_label": drilldown_target.label,
        "missing_severity": domain_status,
        "ui_status": rendered_ui_status,
        "identity_gap": _anchor_identity_gap(spec.name, domain_status),
        "present": present,
        "status": rendered_ui_status,
    }


def _summary_overall_status(
    gap_rows: list[dict[str, object]],
    *,
    manifest: RunManifest | None,
) -> str:
    if manifest is None:
        return "UNKNOWN"
    if any(row["ui_status"] == "CRIT" for row in gap_rows):
        return "CRIT"
    if any(row["ui_status"] == "WARN" for row in gap_rows):
        return "WARN"
    return "OK"


def _summary_identity_graph_complete(
    graph_gap_rows: list[dict[str, object]],
    diagnostic_gap_count: int,
    values: dict[str, object | None],
    manifest: RunManifest | None,
) -> bool:
    return (
        not graph_gap_rows
        and diagnostic_gap_count == 0
        and values.get("identity_graph_complete") is not False
        and manifest is not None
    )


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
    return {
        "overall_status": _summary_overall_status(gap_rows, manifest=manifest),
        "identity_graph_complete": _summary_identity_graph_complete(
            graph_gap_rows,
            diagnostic_gap_count,
            values,
            manifest,
        ),
        "identity_gap_count": len(graph_gap_rows) + diagnostic_gap_count,
        "evidence_gap_count": len(gap_rows) + diagnostic_gap_count,
        "correlation_anchor_gaps": values.get("correlation_anchor_gaps") or {},
        "exact_replay_blockers": values.get("exact_replay_blockers") or [],
        "checkpoint_anchor_status": checkpoint_status,
        "replay_mode": None if manifest is None else replay_mode(manifest),
        "resolved_via": resolved_via,
    }
