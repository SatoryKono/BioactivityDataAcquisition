"""Evaluate shipped alert counts with the Prometheus engine, including absence."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

pytestmark = pytest.mark.unit


def _evaluate(tmp_path, fixture):
    fixture = yaml.safe_dump(fixture)
    executable = os.environ.get("PROMTOOL") or shutil.which("promtool")
    container = os.environ.get("BIOETL_TEST_PROMTOOL_CONTAINER")
    if executable:
        path = tmp_path / "queries.test.yml"
        path.write_text(fixture, encoding="utf-8")
        command, stdin = [executable, "test", "rules", str(path)], None
    elif container:
        command, stdin = (
            [
                "docker",
                "exec",
                "-i",
                container,
                "promtool",
                "test",
                "rules",
                "/dev/stdin",
            ],
            fixture,
        )
    else:
        pytest.skip(
            "promtool unavailable; set PROMTOOL or opt in to an existing BIOETL_TEST_PROMTOOL_CONTAINER"
        )
    result = subprocess.run(
        command, input=stdin, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_signal_drilldown_evaluates_current_operands_not_selected_history(tmp_path):
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-incident-v1.json").read_text()
    )

    def walk(items):
        return [p for item in items for p in [item, *walk(item.get("panels", []))]]

    panel = next(p for p in walk(dashboard["panels"]) if p["id"] == 22011)
    assert "GLOBAL / CURRENT" in panel["description"][:45]
    expr = panel["targets"][0]["expr"]
    # Measurements appear only at the current clock. The same expression at a
    # selected historical end must remain empty, not synthesize evidence.
    _evaluate(
        tmp_path,
        {
            "rule_files": [],
            "evaluation_interval": "1h",
            "tests": [
                {
                    "interval": "1h",
                    "input_series": [
                        {
                            "series": 'bioetl_stage_lag_seconds{pipeline="sample",run_type="incremental",stage="ingestion"}',
                            "values": " ".join(["_"] * 240 + ["407.315231"]),
                        },
                        {
                            "series": 'bioetl_stage_backlog_records{pipeline="sample",run_type="incremental",stage="ingestion"}',
                            "values": " ".join(["_"] * 240 + ["48"]),
                        },
                    ],
                    "promql_expr_test": [
                        {
                            "expr": f"count({expr})",
                            "eval_time": "240h",
                            "exp_samples": [{"labels": "{}", "value": 2}],
                        },
                        {
                            "expr": f"sum({expr})",
                            "eval_time": "240h",
                            "exp_samples": [{"labels": "{}", "value": 455.315231}],
                        },
                        {"expr": expr, "eval_time": "1h", "exp_samples": []},
                    ],
                }
            ],
        },
    )


@pytest.mark.parametrize("observed", [None, 0, -1, 864001, 863600])
def test_stage_clock_does_not_replace_event_time_with_push_or_scrape(
    tmp_path, observed
):
    from scripts.ops.observability.grafana._stage_source_clocks import stage_clock_query

    inputs = [
        {
            "series": 'bioetl_stage_lag_seconds{pipeline="sample",run_type="incremental",stage="ingestion"}',
            "values": "407.315231+0x240",
        },
        {
            "series": 'push_time_seconds{job="bioetl",pipeline="sample",run_type="incremental"}',
            "values": "500000+0x240",
        },
        # A newer backfill publication must not refresh the old incremental.
        {
            "series": 'push_time_seconds{job="bioetl",pipeline="sample",run_type="backfill"}',
            "values": "864000+0x240",
        },
    ]
    if observed is not None:
        inputs.append(
            {
                "series": 'bioetl_stage_snapshot_observed_timestamp_seconds{pipeline="sample",run_type="incremental",stage="ingestion"}',
                "values": f"{observed}+0x240",
            }
        )
    expr = stage_clock_query()
    valid = observed is not None and 0 < observed <= 864000
    tests = [
        {
            "expr": f"count({expr})",
            "eval_time": "240h",
            "exp_samples": [{"labels": "{}", "value": 3}],
        },
        {
            "expr": f"count(({expr}) == ({expr}))",
            "eval_time": "240h",
            "exp_samples": [{"labels": "{}", "value": 2 if valid else 1}],
        },
        {
            "expr": f"count(({expr}) != ({expr}))",
            "eval_time": "240h",
            "exp_samples": [{"labels": "{}", "value": 1 if valid else 2}],
        },
        {
            "expr": f"max(({expr}) == ({expr}))",
            "eval_time": "240h",
            "exp_samples": [
                {"labels": "{}", "value": max(500000, observed if valid else 0) * 1000}
            ],
        },
    ]
    _evaluate(
        tmp_path,
        {
            "rule_files": [],
            "evaluation_interval": "1h",
            "tests": [
                {"interval": "1h", "input_series": inputs, "promql_expr_test": tests}
            ],
        },
    )


def test_stage_clock_without_gateway_or_crossing_remains_unknown_or_absent(tmp_path):
    from scripts.ops.observability.grafana._stage_source_clocks import stage_clock_query

    expr = stage_clock_query()
    _evaluate(
        tmp_path,
        {
            "rule_files": [],
            "evaluation_interval": "1h",
            "tests": [
                {
                    "interval": "1h",
                    "input_series": [
                        {
                            "series": 'bioetl_stage_backlog_records{pipeline="sample",run_type="incremental",stage="output"}',
                            "values": "48+0x240",
                        }
                    ],
                    "promql_expr_test": [
                        {
                            "expr": f"count({expr})",
                            "eval_time": "240h",
                            "exp_samples": [{"labels": "{}", "value": 3}],
                        },
                        {
                            "expr": f"count(({expr}) == ({expr}))",
                            "eval_time": "240h",
                            "exp_samples": [],
                        },
                    ],
                },
                {
                    "interval": "1h",
                    "input_series": [],
                    "promql_expr_test": [
                        {"expr": expr, "eval_time": "240h", "exp_samples": []}
                    ],
                },
            ],
        },
    )


def test_rank_score_does_not_masquerade_as_alert_severity():
    rules = yaml.safe_load(
        Path("grafana/prometheus-rules/bioetl_observability.yml").read_text()
    )
    alert = next(
        r
        for g in rules["groups"]
        for r in g["rules"]
        if r.get("alert") == "BioETLStageLagHigh"
    )
    assert alert["labels"]["severity"] == "warning"
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-incident-v1.json").read_text()
    )
    panel = next(p for p in dashboard["panels"] if p["id"] == 2010)
    override = next(
        o
        for o in panel["fieldConfig"]["overrides"]
        if o["matcher"]["options"] == "Severity"
    )
    props = {p["id"]: p["value"] for p in override["properties"]}
    assert props["displayName"] == "Diagnostic priority"
    assert props["mappings"][0]["options"]["2"]["text"] == "HIGH"
    assert props["mappings"][0]["options"]["1"]["text"] == "ELEVATED"
    assert "Not verified: no event timestamp" in panel["targets"][0]["expr"]
    # The default hides unspecified metadata: a query label alone was not
    # visible in the wide table, even though compact Details could show it.
    freshness = next(
        o
        for o in panel["fieldConfig"]["overrides"]
        if o["matcher"]["options"] == "Event freshness"
    )
    assert (
        next(p["value"] for p in freshness["properties"] if p["id"] == "custom.hidden")
        is False
    )
    order = next(
        t["options"]["indexByName"]
        for t in panel["transformations"]
        if t["id"] == "organize"
    )
    assert order["freshness"] == order["confidence"] + 1


@pytest.mark.parametrize(
    "age", [0, 86399, 86400, 86401, 259199, 259200, 259201, 604800, -1, None, 864000]
)
def test_ingestion_age_obeys_alert_boundary_and_preserves_invalid_or_missing(
    tmp_path, age
):
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-overview-v2.json").read_text()
    )
    panel = next(p for p in dashboard["panels"] if p["id"] == 9606)
    inputs = [
        {
            "series": 'bioetl_data_freshness_seconds{pipeline="other",entity="outside"}',
            "values": "1+0x240",
        }
    ]
    if age is not None:
        inputs.append(
            {
                "series": 'bioetl_data_freshness_seconds{pipeline="chosen",entity="sample"}',
                "values": f"{864000 - age}+0x240",
            }
        )
    state = None
    if age is not None and 0 <= age < 864000:
        state = (
            "STALE >72h (observed)"
            if age > 259200
            else "STALE 24-72h (observed)"
            if age > 86400
            else "Within 24h (observed only)"
        )
    tests = []
    for target in panel["targets"]:
        expected = (
            [{"labels": '{freshness="' + state + '"}', "value": age}]
            if state and state in target["expr"]
            else []
        )
        tests.append(
            {
                "expr": target["expr"].replace("$pipeline", "chosen"),
                "eval_time": "240h",
                "exp_samples": expected,
            }
        )
    _evaluate(
        tmp_path,
        {
            "rule_files": [],
            "evaluation_interval": "1h",
            "tests": [
                {
                    "interval": "1h",
                    "input_series": inputs,
                    "promql_expr_test": tests,
                }
            ],
        },
    )


def test_ingestion_age_deduplicates_sources_before_taking_oldest_entity(tmp_path):
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-overview-v2.json").read_text()
    )
    panel = next(p for p in dashboard["panels"] if p["id"] == 9606)
    inputs = [
        {
            "series": f'bioetl_data_freshness_seconds{{pipeline="chosen",entity="same",job="{job}"}}',
            "values": f"{stamp}+0x240",
        }
        for job, stamp in [("old", 1), ("new", 863900)]
    ] + [
        {
            "series": 'bioetl_data_freshness_seconds{pipeline="chosen",entity="future"}',
            "values": "864001+0x240",
        },
        {
            "series": 'bioetl_data_freshness_seconds{pipeline="chosen",entity="invalid"}',
            "values": "0+0x240",
        },
    ]
    tests = [
        {
            "expr": target["expr"].replace("$pipeline", "chosen"),
            "eval_time": "240h",
            "exp_samples": [
                {"labels": '{freshness="Within 24h (observed only)"}', "value": 100}
            ]
            if index == 0
            else [],
        }
        for index, target in enumerate(panel["targets"])
    ]
    _evaluate(
        tmp_path,
        {
            "rule_files": [],
            "evaluation_interval": "1h",
            "tests": [
                {"interval": "1h", "input_series": inputs, "promql_expr_test": tests}
            ],
        },
    )


@pytest.mark.parametrize("scrape", [1, 0, None])
@pytest.mark.parametrize("events", [True, False])
def test_current_alert_counts_do_not_turn_missing_scrape_into_zero(
    tmp_path, scrape, events
):
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-overview-v2.json").read_text()
    )
    panel = next(p for p in dashboard["panels"] if p["id"] == 9605)
    inputs = (
        []
        if scrape is None
        else [{"series": 'up{job="prometheus"}', "values": str(scrape)}]
    )
    if events:
        inputs.extend(
            {
                "series": f'ALERTS{{alertname="BioETLTest{i}",alertstate="{state}"}}',
                "values": "1",
            }
            for i, state in enumerate(["firing", "firing", "firing", "pending"])
        )
        inputs.append(
            {
                "series": 'ALERTS{alertname="UnrelatedAlert",alertstate="firing"}',
                "values": "1",
            }
        )
    tests = []
    for query, active in zip(panel["targets"], [3, 1], strict=True):
        samples = (
            [] if scrape != 1 else [{"labels": "{}", "value": active if events else 0}]
        )
        tests.append({"expr": query["expr"], "eval_time": "0m", "exp_samples": samples})
    fixture = yaml.safe_dump(
        {
            "rule_files": [],
            "evaluation_interval": "1m",
            "tests": [
                {"interval": "1m", "input_series": inputs, "promql_expr_test": tests}
            ],
        }
    )
    executable = os.environ.get("PROMTOOL") or shutil.which("promtool")
    container = os.environ.get("BIOETL_TEST_PROMTOOL_CONTAINER")
    if executable:
        path = tmp_path / "counts.test.yml"
        path.write_text(fixture, encoding="utf-8")
        command, stdin = [executable, "test", "rules", str(path)], None
    elif container:
        # Explicit opt-in uses an existing container; never starts a service.
        command, stdin = (
            [
                "docker",
                "exec",
                "-i",
                container,
                "promtool",
                "test",
                "rules",
                "/dev/stdin",
            ],
            fixture,
        )
    else:
        pytest.skip(
            "promtool unavailable; set PROMTOOL or opt in to an existing BIOETL_TEST_PROMTOOL_CONTAINER"
        )
    result = subprocess.run(
        command, input=stdin, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr
