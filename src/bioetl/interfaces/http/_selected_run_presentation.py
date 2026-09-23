"""Grafana presentation of exact-run evidence without changing canonical verdicts."""

from urllib.parse import urlencode


def presentation_rows(
    rows: list[dict[str, object]], *, selection: bool = False
) -> list[dict[str, object]]:
    """Keep canonical domain verdicts intact; present one neutral selection action."""
    if selection:
        return [
            {
                **(rows[0] if rows else {}),
                "domain": "Selected run",
                "execution_state": "SELECT RUN",
                "evidence_completeness": "SELECT RUN",
                "run_verdict": "SELECT RUN",
                "verdict": "SELECT RUN",
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
