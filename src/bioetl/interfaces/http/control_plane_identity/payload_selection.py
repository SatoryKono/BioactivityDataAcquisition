"""Row selection and gap diagnostics for control-plane identity payloads."""

from __future__ import annotations


from bioetl.interfaces.http.control_plane_identity.specs import OVERVIEW_NAMES

def _is_actionable_identity_gap(row: dict[str, object]) -> bool:
    return row["identity_gap"] is True and row["name"] != "identity_graph_complete"


def _is_graph_completeness_gap(row: dict[str, object]) -> bool:
    if not _is_actionable_identity_gap(row):
        return False
    return row["priority"] == "P0" or row["missing_severity"] == "FAILING"


def identity_graph_gap_rows(
    anchors: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return gaps that make the identity graph incomplete, not optional detail gaps."""
    return [row for row in anchors if _is_graph_completeness_gap(row)]


def identity_evidence_gap_rows(
    anchors: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return actionable evidence gaps without counting the summary row itself."""
    return [row for row in anchors if _is_actionable_identity_gap(row)]


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


def _rows_for_overview(anchors: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in anchors if row["name"] in OVERVIEW_NAMES]


def _rows_for_gaps(anchors: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in anchors if row["identity_gap"] is True]


def _rows_for_copy_values(anchors: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in anchors if row["copy"] is True]


def _checkpoint_rows_as_list(checkpoint_rows: object) -> list[dict[str, object]]:
    if isinstance(checkpoint_rows, list):
        return list(checkpoint_rows)
    return []


def _filter_rows_by_priority(
    rows: list[dict[str, object]],
    priority: str | None,
) -> list[dict[str, object]]:
    if not priority:
        return rows
    needle = priority.upper()
    return [row for row in rows if row["priority"] == needle]


def select_rows(
    *,
    view: str,
    priority: str | None,
    anchors: list[dict[str, object]],
    checkpoint_rows: object,
) -> list[dict[str, object]]:
    normalized_view = view.strip().lower()
    if normalized_view == "checkpoint_compare":
        return _checkpoint_rows_as_list(checkpoint_rows)
    if normalized_view == "overview":
        selected = _rows_for_overview(anchors)
    elif normalized_view == "gaps":
        selected = _rows_for_gaps(anchors)
    elif normalized_view == "copy_values":
        selected = _rows_for_copy_values(anchors)
    else:
        selected = anchors
    return _filter_rows_by_priority(selected, priority)
