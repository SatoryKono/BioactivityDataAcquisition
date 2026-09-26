"""Keep durable gateway storage and tested dashboard coverage in sync."""

import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


def test_gateway_persistence_file_is_on_a_named_volume() -> None:
    config = yaml.safe_load((ROOT / "docker-compose.monitoring.yml").read_text())
    gateway = config["services"]["pushgateway"]
    persistence = next(
        flag.split("=", 1)[1]
        for flag in gateway["command"]
        if flag.startswith("--persistence.file=")
    )
    assert any(
        source in config["volumes"] and persistence.startswith(target + "/")
        for source, target in (mount.split(":") for mount in gateway["volumes"])
    )


def test_promtool_scenarios_cover_the_shipped_panel_queries() -> None:
    dashboard = json.loads(
        (ROOT / "grafana/dashboards/bioetl-control-plane-v1.json").read_text(
            encoding="utf-8"
        )
    )
    panel = next(
        panel
        for row in dashboard["panels"]
        for panel in row.get("panels", [])
        if panel["id"] == 9491
    )
    expressions = {
        target["expr"].replace("$pipeline", "uniprot_protein").replace(
            "$run_type", "incremental"
        )
        for target in panel["targets"]
    }
    fixture = yaml.safe_load(
        (ROOT / "grafana/prometheus-rules/tests/telemetry_coverage_panel.test.yml")
        .read_text(encoding="utf-8")
    )
    for scenario in fixture["tests"]:
        tested = {item["expr"] for item in scenario["promql_expr_test"]}
        assert tested <= expressions
        if not scenario["name"].startswith("invalid_timestamp"):
            assert tested == expressions
