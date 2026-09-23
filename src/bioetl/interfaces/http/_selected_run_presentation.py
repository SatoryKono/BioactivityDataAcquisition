"""Grafana presentation of exact-run evidence without changing canonical verdicts."""

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
                "action_path": "d/bioetl-run-explorer-v1/0-run-explorer?var-run_id=-",
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
