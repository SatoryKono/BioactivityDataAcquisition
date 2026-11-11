"""Evaluate generated freshness queries at boundaries with the Prometheus engine."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

pytestmark = pytest.mark.unit
_ROOT = Path(__file__).resolve().parents[5]
_NOW = 8 * 86400


@pytest.mark.parametrize(
    ("ages", "expected"),
    [
        ([0], "Within threshold"),
        ([86399], "Within threshold"),
        ([86400], "Within threshold"),
        ([86401], "STALE"),
        ([7 * 86400], "STALE"),
        ([None], "Not verified"),
        ([-1], "Not verified"),
        ([_NOW], "Not verified"),
        ([1, None], "Not verified"),
        ([86401, None], "STALE"),
        ([1, 86401], "STALE"),
        ([], "Not verified"),
    ],
)
def test_generated_heading_measures_age_and_missing_coverage(tmp_path, ages, expected):
    promtool = os.environ.get("PROMTOOL") or shutil.which("promtool")
    if not promtool:
        pytest.skip("promtool unavailable; set PROMTOOL to evaluate generated PromQL")
    dashboard = json.loads(
        (_ROOT / "grafana/dashboards/bioetl-incident-v1.json").read_text(
            encoding="utf-8"
        )
    )
    variable = next(
        v
        for v in dashboard["templating"]["list"]
        if v["name"] == "workflow_evidence_freshness"
    )
    expr = variable["query"]["query"].removeprefix("query_result(")[:-1]
    for name in ("workflow", "pipeline", "run_type"):
        expr = expr.replace(f"${name}", "chosen" if name == "pipeline" else ".*")
    inputs = []
    for index, age in enumerate(ages):
        inputs.append(
            {
                "series": f'bioetl_workflow_scope_universe{{workflow="w{index}",pipeline="chosen",run_type="regular"}}',
                "values": "1+0x192",
            }
        )
        if age is not None:
            inputs.append(
                {
                    "series": f'bioetl_workflow_scope_published_seconds{{workflow="w{index}"}}',
                    "values": f"{_NOW - age}+0x192",
                }
            )
    # A stale workflow outside the selected pipeline must never affect the title.
    inputs.extend(
        [
            {
                "series": 'bioetl_workflow_scope_universe{workflow="other",pipeline="other",run_type="regular"}',
                "values": "1+0x192",
            },
            {
                "series": 'bioetl_workflow_scope_published_seconds{workflow="other"}',
                "values": "1+0x192",
            },
        ]
    )
    fixture = {
        "rule_files": [],
        "evaluation_interval": "1h",
        "tests": [
            {
                "interval": "1h",
                "input_series": inputs,
                "promql_expr_test": [
                    {
                        "expr": f"({expr}) * 0 + 1",
                        "eval_time": "192h",
                        "exp_samples": [
                            {"labels": f'{{freshness="{expected}"}}', "value": 1}
                        ],
                    }
                ],
            }
        ],
    }
    path = tmp_path / "freshness.test.yml"
    path.write_text(yaml.safe_dump(fixture), encoding="utf-8")
    result = subprocess.run(
        [promtool, "test", "rules", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
