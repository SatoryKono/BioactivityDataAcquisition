"""Copy/assert checks for Silver Reject Explorer dashboard."""

from __future__ import annotations

import json
from pathlib import Path


def test_filtered_records_table_has_explicit_empty_and_failure_copy() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json").read_text(
            encoding="utf-8"
        )
    )

    panel = next(
        p
        for p in dashboard["panels"]
        if p.get("title") == "Inspect Filtered Records Table"
    )

    assert panel["title"] == "Inspect Filtered Records Table"
    assert (
        panel["fieldConfig"]["defaults"]["noValue"]
        == "No rejected records for current filters."
    )
    assert "Backend/query failure copy:" in panel["description"]
