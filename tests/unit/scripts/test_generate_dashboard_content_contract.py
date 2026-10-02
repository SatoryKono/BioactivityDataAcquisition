"""Regression guards for scope migration and misleading exact-run telemetry copy."""

import pytest

from scripts.engineering.qa.generate_dashboard_content_contract import (
    _merge_panel_contract,
    _scope,
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
