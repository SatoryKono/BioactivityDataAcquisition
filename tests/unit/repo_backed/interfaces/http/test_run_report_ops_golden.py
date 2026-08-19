"""Repository-backed run-report golden fixture contracts."""

import json
from pathlib import Path

import pytest

from bioetl.interfaces.http._health_server_observability_routing import (
    _summary_rows_pipeline_run_report,
)

pytestmark = pytest.mark.repo_backed


def test_summary_rows_pipeline_run_report_projects_funnel_and_coverage() -> None:
    golden = json.loads(
        Path("tests/fixtures/reports/pipeline_run_report_golden.json").read_text(
            encoding="utf-8"
        )
    )
    started_ms = 1784851200000  # 2026-07-24T00:00:00+00:00
    window_from = started_ms + 3_600_000 * 24
    window_to = window_from + 3_600_000
    payload = _summary_rows_pipeline_run_report(
        golden,
        grafana_from=str(window_from),
        grafana_to=str(window_to),
    )
    assert payload["view"] == "summary"
    assert payload["schema_version"] == "pipeline_run_report_v1"
    summary = payload["summary"]
    assert isinstance(summary, list) and len(summary) == 1
    row = summary[0]
    assert row["run_id"] == "00000000-0000-4000-8000-000000000001"
    assert row["status"] == "success"
    assert row["gold_records_out"] == "820"
    assert row["excluded_by_contract"] == "30"
    assert row["covers_selected_run"] == "outside"
    assert row["coverage_chip"] == "OUT OF RANGE"
    assert "before window" in row["coverage_offset"]
    assert row["from_ms"] == str(started_ms - 5 * 60 * 1000)
    assert row["to_ms"] == str(started_ms + 60_000 + 5 * 60 * 1000)
    params = {item["parameter"]: item["value"] for item in payload["rows"]}
    assert params["set_range_to_run"].startswith("Set range to run")
    in_range = _summary_rows_pipeline_run_report(
        golden,
        grafana_from=str(started_ms - 3_600_000),
        grafana_to=str(started_ms + 3_600_000),
    )
    in_row = in_range["summary"][0]
    assert in_row["covers_selected_run"] == "yes"
    assert in_row["coverage_chip"] == "IN RANGE"
