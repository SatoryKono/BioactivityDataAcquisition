"""Regression guards for scope migration and misleading exact-run telemetry copy."""

import json
from pathlib import Path

import pytest

from scripts.engineering.qa.generate_dashboard_content_contract import (
    _merge_panel_contract,
    _scope,
)

from scripts.ops.observability.grafana.repair_legacy_prometheus_dashboard import (
    repair_dashboard,
)

pytestmark = pytest.mark.unit


def test_prometheus_cannot_claim_exact_run_from_description():
    panel = {
        "type": "stat",
        "description": "SELECTED RUN · exact identity",
        "targets": [{"expr": "bioetl_records_total"}],
        "datasource": {"type": "prometheus", "uid": "prometheus"},
    }
    assert _scope("Review Run Status", panel) == "time_range"


def test_scope_migration_preserves_human_column_contract():
    generated = {
        "title": "Review Saved Evidence",
        "evidence_source": "ops_http",
        "scope": "selected_run",
        "scope_class": "selected_run",
        "role": "evidence_table",
        "empty_state_class": "select_run",
    }
    previous = {
        **generated,
        "scope": "current",
        "scope_class": "current",
        "required_columns": ["Result", "Trust"],
        "role": "identity_table",
    }
    merged = _merge_panel_contract(generated=generated, previous=previous)
    assert merged["scope"] == merged["scope_class"] == "selected_run"
    assert merged["required_columns"] == ["Result", "Trust"]
    assert merged["role"] == "identity_table"


def test_previous_exact_run_scope_cannot_override_prometheus_source():
    generated = {
        "title": "Monitor Fleet",
        "evidence_source": "prometheus",
        "scope": "time_range",
        "scope_class": "time_range",
        "role": "status",
        "empty_state_class": "telemetry_missing",
    }
    previous = {**generated, "scope": "selected_run", "scope_class": "selected_run"}
    merged = _merge_panel_contract(generated=generated, previous=previous)
    assert merged["scope"] == merged["scope_class"] == "time_range"


def test_legacy_migration_preserves_queries_and_explains_absence():
    source = {
        "uid": "rpfmFFz7z",
        "title": "Prometheus Stats",
        "panels": [
            {"id": 6, "targets": [{"expr": "prometheus_local_storage_memory_series"}]},
            {
                "id": 14,
                "title": "Scrape Duration",
                "targets": [{"expr": "prometheus_target_interval_length_seconds"}],
            },
        ],
    }
    result = repair_dashboard(source)
    assert result["uid"] == source["uid"]
    assert result["panels"][1]["targets"] == source["panels"][1]["targets"]
    assert result["panels"][1]["title"] == "Scrape Interval"
    assert result["panels"][1]["fieldConfig"]["defaults"]["unit"] == "s"
    assert result["panels"][0]["fieldConfig"]["defaults"]["noValue"].startswith(
        "UNSUPPORTED"
    )
    assert source["title"] == "Prometheus Stats"
    assert repair_dashboard(result) == result


def test_migration_rejects_an_unrelated_dashboard():
    with pytest.raises(ValueError):
        repair_dashboard({"uid": "bioetl-overview-v2"})


def test_migration_preserves_scope_and_explains_legacy_signals():
    source = {
        "uid": "rpfmFFz7z",
        "panels": [
            {"id": 8, "type": "text", "options": {"content": "old ingestion help"}},
            {"id": 11, "type": "text", "options": {"content": "old scrape help"}},
            {
                "id": 12,
                "targets": [
                    {
                        "expr": 'prometheus_evaluator_duration_seconds{instance=~"$node",quantile="0.99"}'
                    }
                ],
            },
            {"id": 99, "targets": [{"expr": "unrelated_metric"}]},
        ],
    }
    result = repair_dashboard(source)
    assert "unavailable" in result["panels"][0]["options"]["content"]
    assert "scrape_duration_seconds" in result["panels"][1]["options"]["content"]
    assert result["panels"][2]["targets"][0]["expr"] == (
        'prometheus_rule_group_duration_seconds{instance=~"$node",quantile="0.99"}'
    )
    assert result["panels"][2]["fieldConfig"]["defaults"]["unit"] == "s"
    assert result["panels"][3] == source["panels"][3]
    assert source["panels"][0]["options"]["content"] == "old ingestion help"
    assert repair_dashboard(result) == result


def test_shipped_prometheus_rule_duration_uses_seconds():
    path = (
        Path(__file__).resolve().parents[3]
        / "grafana/service-dashboards/prometheus-stats.json"
    )
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    panel = next(item for item in dashboard["panels"] if item["id"] == 12)
    assert panel["fieldConfig"]["defaults"]["unit"] == "s"
    assert any(
        "prometheus_rule_group_duration_seconds" in target["expr"]
        for target in panel["targets"]
    )
