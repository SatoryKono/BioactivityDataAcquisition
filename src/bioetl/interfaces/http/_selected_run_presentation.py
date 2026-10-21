"""Grafana presentation of exact-run evidence without changing canonical verdicts."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlencode

_SELECT_RUN = "SELECT RUN"


def presentation_rows(
    rows: list[dict[str, object]], *, selection: bool = False
) -> list[dict[str, object]]:
    """Keep canonical domain verdicts intact; present one neutral selection action."""
    if selection:
        return [
            {
                **(rows[0] if rows else {}),
                "domain": "Selected run",
                "execution_state": _SELECT_RUN,
                "evidence_completeness": _SELECT_RUN,
                "run_verdict": _SELECT_RUN,
                "verdict": _SELECT_RUN,
                "reason": "Choose a run to inspect saved evidence",
                "action": "Choose a run",
                "action_path": "d/bioetl-run-explorer-v1/run-explorer?var-run_id=-",
            }
        ]
    return [
        {
            **row,
            "action_path": (
                "api/datasources/proxy/uid/bioetl-ops-http/ops/observability/"
                "pipeline-run-report-artifact?"
                + urlencode(
                    {
                        "pipeline": str(row.get("pipeline", "")),
                        "run_id": str(row.get("run_id", "")),
                        "format": "pipeline_run_report_json",
                    }
                )
            ),
        }
        for row in rows
    ]


_UNKNOWN_CHECK_LABELS = {
    "manifest_not_recorded": "manifest for this run was not recorded",
}


def _readiness_fields(projection: Mapping[str, object]) -> dict[str, object]:
    blockers = projection.get("blockers")
    unknown = projection.get("unknown_checks")
    blocker_text = (
        ", ".join(blockers) if isinstance(blockers, list) and blockers else "—"
    )
    unknown_text = (
        ", ".join(_UNKNOWN_CHECK_LABELS.get(str(code), str(code)) for code in unknown)
        if isinstance(unknown, list) and unknown
        else "—"
    )
    row = {
        key: value
        for key, value in projection.items()
        if key not in {"checks", "blockers", "unknown_checks"}
    }
    row["blockers"] = blocker_text
    row["unknown_checks"] = unknown_text
    explanations = []
    if blocker_text != "—":
        explanations.append("Failed checks: " + blocker_text)
    if unknown_text != "—":
        explanations.append("Not verified: " + unknown_text)
    row["explanation"] = "; ".join(explanations) or (
        "Required replay checks passed"
        if projection.get("verdict") == "READY"
        else "Open replay checks for the assessment basis"
    )
    checks = projection.get("checks")
    return {
        "replay_readiness": [row],
        "replay_checks": checks if isinstance(checks, list) else [],
    }
