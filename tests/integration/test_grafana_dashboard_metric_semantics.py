# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Grafana dashboard metric semantics and no-data contracts."""

import json
from pathlib import Path
import re

import pytest
import yaml

from bioetl.infrastructure.observability.prometheus_metric_registries import COUNTERS

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    get_panel_expressions,
    load_dashboard,
)


def _require_dashboard(name: str) -> Path:
    path = Path("grafana/dashboards") / name
    if not path.exists():
        pytest.skip(f"{name} retired in grafana simplification epic #6570/#6576")
    return path


from tests.integration.grafana_contract_specs import (
    SUMMARY_NO_VECTOR_ZERO_FALLBACK_PANELS,
)

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("dashboard_file", get_dashboard_files(), ids=lambda p: p.name)
def test_rolling_counter_legends_do_not_sum_overlapping_windows(dashboard_file):
    dashboard = load_dashboard(dashboard_file)
    for panel in get_dashboard_panels(dashboard):
        if panel.get("type") != "timeseries":
            continue
        if any(
            re.search(r"\b(?:rate|increase)\(", t.get("expr", ""))
            for t in panel.get("targets", [])
        ):
            assert "sum" not in panel.get("options", {}).get("legend", {}).get(
                "calcs", []
            ), (dashboard_file.name, panel["id"])


RULES_PATH = Path("grafana/prometheus-rules/bioetl_observability.yml")
MAX_OVER_TIME_COUNTER_POLICY_PATH = Path(
    "configs/quality/promql_max_over_time_counter_policy.yaml"
)
_MAX_OVER_TIME_METRIC_RE = re.compile(
    r"max_over_time\(\s*(?:\(\s*sum\s+by\s*\([^)]*\)\s*\(\s*)?"
    r"([a-zA-Z_:][a-zA-Z0-9_:]*)"
)
_PROCESSED_RECORDS_DASHBOARDS = ("bioetl-dq-v2.json",)

_PROCESSED_RECORDS_PARAMETER_LABELS = (
    "01 bronze_records",
    "02 silver_valid_records",
    "03 silver_filtered_out_records",
    "04 silver_quarantined_records",
    "05 silver_skipped_records",
    "06 silver_deduplicated_records",
    "07 gold_written_records",
    "08 gold_excluded_by_contract_records",
    "09 gold_quarantined_records",
    "10 gold_skipped_records",
    "11 gold_deduplicated_records",
)

_PROCESSED_RECORDS_MAPPING_LABELS = _PROCESSED_RECORDS_PARAMETER_LABELS

_PROCESSED_RECORDS_REMOVED_PARAMETER_LABELS = (
    "00 reconciliation_status",
    "07 silver_accounted_records",
    "08 silver_delta_vs_bronze",
    "14 gold_accounted_records",
    "15 gold_delta_vs_valid_silver",
)

_PROCESSED_RECORDS_DISPLAY_LABELS = (
    "bronze [total]",
    "silver [valid]",
    "silver [filtered out]",
    "silver [quarantined]",
    "silver [skipped]",
    "silver [deduplicated]",
    "gold [valid]",
    "gold [excluded]",
    "gold [quarantined]",
    "gold [skipped]",
    "gold [deduplicated]",
)

_PROCESSED_RECORDS_PRIMARY_COLORS = {
    "01 bronze_records": "#cd7f32",
    "02 silver_valid_records": "#c0c0c0",
    "07 gold_written_records": "#d4af37",
}

_PROCESSED_RECORDS_SECONDARY_LABELS = {
    label
    for label in _PROCESSED_RECORDS_PARAMETER_LABELS
    if label not in _PROCESSED_RECORDS_PRIMARY_COLORS
}


def _expected_processed_records_display_token_mappings() -> list[dict[str, object]]:
    return []


def _expected_processed_records_row_status_mappings() -> list[dict[str, object]]:
    return [
        {
            "type": "value",
            "options": {
                "": {"text": "", "color": "rgba(0,0,0,0)"},
                "silver_deficit": {"text": "", "color": "red"},
                "gold_deficit": {"text": "", "color": "red"},
            },
        }
    ]


def _assert_processed_records_target_contract(processed: dict[str, object]) -> None:
    """Assert the HTTP target and absence semantics for Processed Records."""
    targets = processed.get("targets")
    assert isinstance(targets, list)
    assert len(targets) == 2
    assert targets[1]["refId"] == "StageInput"
    assert targets[1]["parser"] == "backend"
    assert "$exists(quality_evidence.funnel)" in targets[1]["root_selector"]
    assert targets[1]["root_selector"] == targets[1]["uql"].removeprefix(
        'parse-json | jsonata "'
    ).removesuffix('"')
    assert (
        targets[1]["url"]
        == "/ops/observability/selected-run-status?pipeline=${selected_pipeline}&run_id=${selected_run_id}"
    )
    assert "quality_evidence.funnel" in targets[1]["uql"]
    assert "records_in" in targets[1]["uql"]
    assert targets[0] == {
        "datasource": {
            "type": "yesoreyeram-infinity-datasource",
            "uid": "bioetl-ops-http",
        },
        "format": "table",
        "parser": "backend",
        "refId": "A",
        "root_selector": "rows",
        "source": "url",
        "type": "json",
        "url": (
            "/ops/observability/processed-records?"
            "pipeline=${selected_pipeline}&run_type=${run_type:csv}&run_id=${selected_run_id}"
        ),
        "url_options": {"data": "", "method": "GET"},
    }

    processed_json = json.dumps(processed, sort_keys=True)
    assert 'run_id="' not in processed_json
    assert "run_id=~" not in processed_json
    assert "$__range" not in processed_json
    assert "or vector(0)" not in processed_json
    assert "__zero" not in processed_json
    for removed_label in _PROCESSED_RECORDS_REMOVED_PARAMETER_LABELS:
        assert removed_label not in processed_json


def test_summary_queries_do_not_mask_absence_with_vector_zero() -> None:
    """Count summaries must not hide missing telemetry behind PromQL `or vector(0)`."""
    for dashboard_name, panel_titles in SUMMARY_NO_VECTOR_ZERO_FALLBACK_PANELS.items():
        dashboard = load_dashboard(_require_dashboard(dashboard_name))
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title in panel_titles:
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Dashboard {dashboard_name} missing panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert expressions, (
                f"Dashboard {dashboard_name} panel {panel_title!r} has no expressions"
            )
            assert all("or vector(0)" not in expr for expr in expressions), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must not mask "
                "absence with 'or vector(0)' (preserve No data)"
            )


def test_workflow_selected_range_counters_use_zero_valid_empty_state() -> None:
    """Workflow cards use selected-range deltas; display zero via noValue, not PromQL."""
    dashboard = load_dashboard(_require_dashboard("bioetl-incident-v1.json"))
    expected_panels = {
        "Track Failed Workflow Runs",
        "Track Failed Workflow Steps",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == expected_panels

    for panel_title, panel in panels.items():
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert expressions
        assert any(
            "increase(" in expr and "[$__range]" in expr for expr in expressions
        ), f"{panel_title} must stay selected range event-delta evidence"
        assert all("max_over_time(" not in expr for expr in expressions), (
            f"{panel_title} counts counter events and must not use max_over_time()"
        )
        assert all("or vector(0)" not in expr for expr in expressions), (
            f"{panel_title} must not mask absence with PromQL 'or vector(0)'"
        )
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        assert defaults.get("noValue") == "0", (
            f"{panel_title} must keep noValue='0' for zero-valid event-count semantics"
        )
        description = str(panel.get("description", "")).lower()
        assert "selected" in description
        assert "zero means no" in description or "`0` means no" in description


def test_overview_compact_evidence_panels_do_not_claim_l0_current_verdict() -> None:
    """Historical evidence must stay behind disclosure below the L0 answer path."""
    first_answer_titles = {
        "Review Selected Run Status",
        "Review Run Domains",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(
            load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
        )
    }
    for title in (
        "Monitor Scope Health",
        "Review First Action",
        "Track Runtime Blockers",
        "Review Failed Runs",
    ):
        assert title not in panels
    return


@pytest.mark.parametrize(
    "dashboard_name",
    [
        "bioetl-dq-v2.json",
    ],
)
def test_operator_context_shell_panels_preserve_canonical_semantics(
    dashboard_name: str,
) -> None:
    dashboard = load_dashboard(_require_dashboard(dashboard_name))
    panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
    assert 9401 not in panels
    assert {9400, 9406, 9402, 9403}.issubset(panels)
    assert "SELECTED RUN" in panels[9400]["description"]
    assert (
        "CURRENT pipeline status and TIME RANGE scores are not on this page"
        in panels[9400]["options"]["content"]
    )
    identity = panels[9402]
    assert identity["type"] == "text"
    assert "Open Review Run Identity on Overview" in identity["options"]["content"]
    assert identity.get("targets", []) == []
    processed = panels[9403]
    _assert_processed_records_target_contract(processed)
    description = processed["description"]
    for token in (
        "SELECTED RUN",
        "accounting",
        "count in",
        "count out",
        "UNKNOWN",
        "Source unavailable",
    ):
        assert token in description
    assert "Skipped outcomes are hidden" in description
    expressions = "\n".join(get_panel_expressions(dashboard))
    assert "$run_id" not in expressions and "${run_id}" not in expressions


def test_control_plane_identity_evidence_uses_http_not_prometheus_labels() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
    for pid in (9406, 9408):
        panel = panels[pid]
        assert panel["datasource"] == {
            "type": "yesoreyeram-infinity-datasource",
            "uid": "bioetl-ops-http",
        }
        assert get_panel_expressions({"panels": [panel]}) == []
        assert all("run_id=${run_id}" in t["url"] for t in panel["targets"])
    identity = panels[9423]
    assert identity["datasource"] == {
        "type": "datasource",
        "uid": "-- Dashboard --",
    }
    assert identity["targets"][0]["panelId"] == 9418
    source = panels[9418]
    assert source["datasource"]["uid"] == "bioetl-ops-http"
    assert all("run_id=${run_id}" in t["url"] for t in source["targets"])
    for path in Path("grafana/dashboards").glob("*.json"):
        expressions = "\n".join(get_panel_expressions(load_dashboard(path)))
        for forbidden in (
            "run_id=~",
            "manifest_id=~",
            "execution_fingerprint=~",
            "effective_config_hash=~",
            "input_snapshot_identity_fingerprint=~",
            "composite_run_identity=~",
        ):
            assert forbidden not in expressions


def test_control_plane_identity_evidence_documents_short_full_split() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panel = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 9408)
    assert "value_full" in json.dumps(panel["transformations"])
    assert panel["fieldConfig"]["defaults"]["custom"]["inspect"] is True
    assert "Inspect a value to copy it" in panel["description"]
    assert panel["options"]["footer"]["enablePagination"] is True


def test_runtime_selected_count_zeroes_are_scope_anchored() -> None:
    """Selected runtime count cards must keep UNKNOWN when selected scope is absent."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    expected_panels = {
        "Monitor Failed Runs": "bioetl_pipeline_runs_total",
        "Monitor No-Records Runs": "bioetl_runtime_pipeline_run_type_universe",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == set(expected_panels)

    for panel_title, anchor_metric in expected_panels.items():
        panel = panels[panel_title]
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert expressions
        assert any(anchor_metric in expr for expr in expressions), (
            f"{panel_title} must require its documented telemetry anchor"
        )
        assert all("or vector(0)" not in expr for expr in expressions), (
            f"{panel_title} must not convert missing selected scope into false OK"
        )
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        assert defaults.get("noValue") == "UNKNOWN"


def test_runtime_alert_condition_summaries_are_telemetry_anchored() -> None:
    """Runtime handoff cards must preserve UNKNOWN for missing scope telemetry."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    expected_anchor = {
        "Monitor Pipeline Alerts": (
            "bioetl_runtime_pipeline_run_type_universe",
            'run_type=~"$run_type"',
        ),
        "Inspect DQ Alert Conditions": (
            "bioetl_runtime_pipeline_run_type_universe",
            'pipeline=~"$pipeline"',
        ),
        "Inspect Control Plane Alerts": (
            "bioetl_runtime_pipeline_run_type_universe",
            'run_type=~"$run_type"',
        ),
        "Inspect Provider Alerts": (
            "bioetl_provider_current_status",
            'provider=~"$provider"',
        ),
        "Inspect Global Provider Alert Conditions": (
            "bioetl_provider_current_status",
            "count(bioetl_provider_current_status)",
        ),
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_anchor
    }
    assert set(panels) == set(expected_anchor)

    for panel_title, (anchor_metric, anchor_scope) in expected_anchor.items():
        panel = panels[panel_title]
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert expressions
        assert any("and on()" in expr for expr in expressions), (
            f"{panel_title} must join condition totals to a telemetry anchor"
        )
        assert any(
            anchor_metric in expr and anchor_scope in expr for expr in expressions
        )
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        assert defaults.get("noValue") == "UNKNOWN"


def test_latency_p95_panels_preserve_no_data_state() -> None:
    """Latency p95 panels must not collapse missing samples into zero."""
    expected_latency_panels = {
        "bioetl-incident-v1.json": {
            "Track Phase Duration",
            "Track Pipeline Duration",
            "Track Global Read Latency",
            "Track Checkpoint Save Latency",
            "Track Global Checkpoint Admin Latency",
            "Track Global Audit Write Latency",
            "Track Global Audit Query Latency",
        },
    }

    for dashboard_name, panel_titles in expected_latency_panels.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title in panel_titles:
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Dashboard {dashboard_name} missing panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert expressions, (
                f"Dashboard {dashboard_name} panel {panel_title!r} has no expressions"
            )
            assert any(
                "histogram_quantile(0.95" in expr
                or "histogram_quantile($read_latency_quantile" in expr
                for expr in expressions
            ), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must stay histogram-backed"
            )
            assert all("or vector(0)" not in expr for expr in expressions), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must preserve "
                "no-data instead of rendering zero latency"
            )


@pytest.mark.parametrize(
    ("dashboard_name", "panel_title", "description_snippet", "expected_no_value"),
    [
        (
            "bioetl-incident-v1.json",
            "Track Replay Drift by Type",
            "No data means no replay drift events were observed in range or replay drift telemetry is absent",
            "No replay drift samples",
        ),
        (
            "bioetl-incident-v1.json",
            "Track Global Checkpoint Admin Latency",
            "Expected Empty classification: No data is valid when no checkpoint "
            "operator/admin duration samples were emitted",
            "No GLOBAL checkpoint operator latency samples in range. This is optional "
            "admin/operator telemetry, not pipeline success evidence.",
        ),
        (
            "bioetl-incident-v1.json",
            "Review Missing Lineage by Layer",
            "Use as lineage risk triage only; it does not prove complete artifact "
            "identity graph or exact artifact refs.",
            "No missing-lineage reference samples in range. Empty means no sampled "
            "lineage-missing events or absent telemetry, not proof of full lineage "
            "closure.",
        ),
        (
            "bioetl-incident-v1.json",
            "Track Global Audit Write Latency",
            "No data means no latency samples, not zero latency.",
            "No GLOBAL audit write latency samples in range. Empty means no audit "
            "writes were timed or audit telemetry is absent, not zero latency.",
        ),
        (
            "bioetl-incident-v1.json",
            "Track Global Audit Query Latency",
            "No data means no latency samples, not zero latency.",
            "No GLOBAL audit query latency samples in range. Empty means no audit "
            "queries were timed or audit telemetry is absent, not zero latency.",
        ),
    ],
)
def test_review_panels_explain_empty_state_explicitly(
    dashboard_name: str,
    panel_title: str,
    description_snippet: str,
    expected_no_value: str,
) -> None:
    """Panels with ambiguous empty-state semantics should explain no-data behavior explicitly."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in {dashboard_name}"
    description = panel.get("description", "")
    assert description
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == expected_no_value


def test_count_like_summary_panels_use_rounding_or_boolean_conditions() -> None:
    """Count-like summary panels should avoid fractional event semantics."""
    expected_panel_snippets = {
        "bioetl-incident-v1.json": {
            "Monitor Pipeline Alerts": "bioetl_runtime_pipeline_alert_count",
            "Inspect DQ Alert Conditions": "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
            "Inspect Control Plane Alerts": "bioetl_runtime_control_plane_alert_count",
            "Inspect Provider Alerts": "bioetl_runtime_provider_alert_count",
            "Inspect Global Provider Alert Conditions": (
                "bioetl_runtime_alert_condition_provider_adapter_latency_high_30m"
            ),
            "Track Global Shutdown Starts": "round(",
            "Track Global Shutdown Completions": "round(",
        },
    }

    for dashboard_name, panel_expectations in expected_panel_snippets.items():
        dashboard = load_dashboard(_require_dashboard(dashboard_name))
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title, expected_snippet in panel_expectations.items():
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Dashboard {dashboard_name} missing panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert any(expected_snippet in expr for expr in expressions), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must include "
                f"{expected_snippet!r} for stable count semantics"
            )


def test_dq_score_uses_validation_metric() -> None:
    """Volume-weighted 7d score is TIME RANGE and is not on this page."""
    _assert_retired_from_dq("Monitor Weighted DQ")


def _dq_titles() -> set[str]:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    return {
        str(panel.get("title"))
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }


def _assert_retired_from_dq(*titles: str) -> None:
    present = _dq_titles()
    retired = set(titles)
    overlap = sorted(retired & present)
    assert not overlap, f"retired DQ panels still shipped: {overlap}"
    assert "Review Selected Run Status" in present


def test_worst_entity_dq_score_preserves_no_data_state() -> None:
    """Worst-score gauges are TIME RANGE and are not on the selected-run page."""
    _assert_retired_from_dq("Monitor Worst DQ")


def test_dq_current_status_panels_preserve_unknown_no_data_state() -> None:
    """CURRENT DQ status is not an assessment of the selected Run ID."""
    _assert_retired_from_dq(
        "Monitor Current DQ Status",
        "Monitor DQ Threshold State",
    )


def test_dq_current_status_panels_use_explicit_status_value_mappings() -> None:
    """CURRENT status vocabulary stays off 5. Data Quality."""
    _assert_retired_from_dq(
        "Monitor Current DQ Status",
        "Monitor DQ Threshold State",
    )


def test_dq_current_status_panels_use_canonical_severity_threshold_steps() -> None:
    """CURRENT severity cards stay off 5. Data Quality."""
    _assert_retired_from_dq(
        "Monitor Current DQ Status",
        "Monitor DQ Threshold State",
    )


def test_dq_first_screen_panels_expose_actionable_datalinks() -> None:
    """Selected-run status replaces the CURRENT first-screen action cards."""
    _assert_retired_from_dq(
        "Monitor Current DQ Status",
        "Monitor DQ Threshold State",
        "Inspect Current DQ Reasons",
    )
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    status = next(
        panel for panel in get_dashboard_panels(dashboard) if panel.get("id") == 9406
    )
    links = (status.get("fieldConfig") or {}).get("defaults", {}).get("links") or []
    assert any(link.get("title") == "Open Run Explorer" for link in links)


def test_dq_threshold_state_panel_uses_bounded_reason_severity_with_ok_fallback() -> (
    None
):
    """Threshold-state PromQL is not on the selected-run page."""
    _assert_retired_from_dq("Monitor DQ Threshold State")


def test_dq_current_status_and_reasons_share_one_instant_snapshot() -> None:
    """CURRENT instant panels 9401/9101/9102 are not on 5. Data Quality."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    ids = {
        panel.get("id")
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    assert {9401, 9101, 9102}.isdisjoint(ids)
    assert 9406 in ids


def test_runtime_diagnostic_panels_preserve_unknown_no_data_state() -> None:
    """Runtime diagnostic gauges must not convert missing telemetry to OK."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    expected_panels = {
        "Monitor Coverage",
        "Monitor Active Blocker Count",
        "Monitor Runtime Error Rate",
        "Monitor Worst Stage Lag",
        "Monitor Memory Pressure",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == expected_panels

    for panel_title, panel in panels.items():
        expressions = [target.get("expr", "") for target in panel.get("targets", [])]
        assert all("or vector(0)" not in expr for expr in expressions), (
            f"{panel_title} must preserve UNKNOWN/NO DATA instead of synthetic OK"
        )
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        assert defaults.get("noValue") == "UNKNOWN", (
            f"{panel_title} must render missing runtime telemetry as UNKNOWN"
        )


def test_runtime_telemetry_gap_checks_scrape_and_rule_health() -> None:
    """Runtime telemetry gap must include Prometheus rule health and actual metrics presence
    (Pushgateway-compatible)."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Coverage"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor Coverage' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any(
        "bioetl_rt_stage_ratio" in expr or "stage_evidence_present_ratio" in expr
        for expr in expressions
    )
    assert 'max(up{job="bioetl"})' in expressions
    assert any(
        "bioetl_runtime_required_rule_age_seconds" in expr for expr in expressions
    )

    rules = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    rule_expr = next(
        rule.get("expr", "")
        for group in rules.get("groups", [])
        for rule in group.get("rules", [])
        if rule.get("record") == "bioetl_runtime_trust_gap_status_10m"
    )
    # Pushgateway compatibility: check for actual BioETL metrics presence instead of scrape status
    assert "absent_over_time(bioetl_pipeline_runs_total[10m])" in rule_expr
    assert "prometheus_rule_evaluation_failures_total" in rule_expr
    assert "prometheus_rule_group_last_evaluation_timestamp_seconds" in rule_expr
    assert "absent(" in rule_expr
    assert "bioetl_observability[.]yml;bioetl_runtime_dashboard_recording$" in rule_expr
    assert "bioetl_runtime_dashboard_recording" in rule_expr, (
        "Telemetry gap must check the runtime dashboard recording group"
    )


def test_runtime_domain_thresholds_match_alert_rule_policy() -> None:
    """Runtime domain gauges should use real alert units, not generic 1/2 severity steps."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    expected_steps = {
        "Monitor Runtime Error Rate": [
            {"color": "green", "value": None},
            {"color": "orange", "value": 0.05},
            {"color": "red", "value": 0.2},
        ],
        "Monitor Worst Stage Lag": [
            {"color": "green", "value": None},
            {"color": "orange", "value": 300},
            {"color": "red", "value": 900},
        ],
        "Monitor Active Blocker Count": [
            {"color": "green", "value": None},
            {"color": "red", "value": 1},
        ],
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_steps
    }
    assert set(panels) == set(expected_steps)
    for panel_title, steps in expected_steps.items():
        defaults = panels[panel_title].get("fieldConfig", {}).get("defaults", {})
        assert defaults.get("thresholds", {}).get("steps") == steps

    error_defaults = (
        panels["Monitor Runtime Error Rate"].get("fieldConfig", {}).get("defaults", {})
    )
    assert error_defaults.get("min") == 0
    assert error_defaults.get("max") == 1


def test_runtime_freshness_handoff_preserves_missing_telemetry() -> None:
    """Freshness handoff must not turn missing freshness telemetry into OK."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-incident-v1.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Entities Stale Over 24h"
        ),
        None,
    )
    assert panel is not None, "Panel 'Inspect Entities Stale Over 24h' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert expressions
    assert all("or vector(0)" not in expr for expr in expressions), (
        "Freshness handoff must preserve UNKNOWN/NO DATA instead of synthetic OK"
    )
    assert any("count(bioetl_data_freshness_seconds" in expr for expr in expressions), (
        "Freshness handoff must anchor zero only to existing freshness telemetry"
    )
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == "UNKNOWN"


def test_provider_failure_rate_panel_uses_neutral_zero_and_policy_thresholds() -> None:
    """Provider failure rate must keep neutral zero plus explicit WARN/CRIT policy."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Track Failure Rate"
        ),
        None,
    )
    assert panel is None
    return


def test_provider_severity_matrix_preserves_unknown_and_critical_mapping() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Fleet Status"
        ),
        None,
    )
    assert panel is None
    return


def test_provider_telemetry_freshness_fails_closed_when_status_is_missing() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Telemetry Presence"
        ),
        None,
    )
    assert panel is None
    return


def test_provider_critical_table_keeps_severity_only_scope() -> None:
    """Critical providers table must only show active degraded/failing rows."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Non-OK Providers"
        ),
        None,
    )
    assert panel is None
    return


def test_provider_health_status_panel_fails_closed_to_unknown() -> None:
    """Raw provider status panel must preserve UNKNOWN for known providers with no sample."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Raw Health Status"
        ),
        None,
    )
    assert panel is None
    return


def test_provider_top_causes_panel_preserves_canonical_cause_only_semantics() -> None:
    """Provider top causes must not fabricate synthetic rows when canonical causes are absent."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Top Provider Causes"
        ),
        None,
    )
    assert panel is None
    return


def test_provider_diagnostic_panels_preserve_no_data_for_tokens_and_circuit_breakers() -> (
    None
):
    """Token/circuit-breaker diagnostics must not synthesize healthy or fake adapter rows."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    expectations = {
        "Monitor Available Rate-Limit Tokens": (
            "bioetl_rate_limiter_tokens_available",
            "or vector(0)",
        ),
        "Monitor Global Circuit-Breaker State": (
            "bioetl_circuit_breaker_state",
            "or vector(0)",
        ),
        "Track Global Circuit-Breaker Trips": (
            "bioetl_circuit_breaker_trips_total",
            'label_replace(vector(0), "adapter",',
        ),
    }
    present = {panel.get("title") for panel in get_dashboard_panels(dashboard)}
    assert set(expectations).isdisjoint(present)
    return


def test_provider_optional_telemetry_panels_explain_empty_samples_do_not_refute_status() -> (
    None
):
    """Optional provider telemetry must disclose no-sample semantics explicitly."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    expectations = {
        "Track Rate-Limiter Wait p95": "optional telemetry can stay empty",
        "Monitor Available Rate-Limit Tokens": "optional telemetry can stay empty",
        "Monitor Global Circuit-Breaker State": "adapter-scoped telemetry can stay empty",
        "Track Global Circuit-Breaker Trips": "does not refute current provider severity",
    }
    present = {panel.get("title") for panel in get_dashboard_panels(dashboard)}
    assert set(expectations).isdisjoint(present)
    return


def test_provider_degraded_checks_panel_uses_neutral_evidence_thresholds() -> None:
    """Selected-range degraded-count evidence must not reuse current-severity thresholds."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Degraded Checks"
        ),
        None,
    )
    assert panel is None
    return


def test_dq_selected_range_evidence_panels_use_neutral_thresholds() -> None:
    """TIME RANGE evidence cards are not on the selected-run page."""
    _assert_retired_from_dq(
        "Monitor Bronze Records",
        "Monitor Gold Records",
        "Monitor Quarantined Records",
    )


def test_dq_blocked_record_evidence_panels_use_neutral_thresholds() -> None:
    """Blocked-record range panels are not on the selected-run page."""
    _assert_retired_from_dq(
        "Monitor Blocked Records",
        "Track DQ Threshold Events",
    )


def test_dq_freshness_lag_panel_uses_time_domain_thresholds() -> None:
    """Freshness age is TIME RANGE and is not on the selected-run page."""
    _assert_retired_from_dq("Monitor Worst Freshness Age")


def test_dq_problem_panels_expose_actionable_datalinks() -> None:
    """Range problem cards are not on the selected-run page."""
    _assert_retired_from_dq(
        "Monitor Worst DQ",
        "Monitor Worst Freshness Age",
        "Monitor Silver Filter Rejects",
    )


def test_dashboards_do_not_use_prometheus_created_timestamps() -> None:
    """Operator dashboards must not expose Prometheus client bookkeeping timestamps."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        expressions = get_panel_expressions(dashboard)
        for expr in expressions:
            if "_created" not in expr:
                continue
            # A creation marker may suppress a mixed-generation histogram,
            # but must never be displayed as run time, freshness or latency.
            assert "histogram_quantile(" in expr and " unless on (" in expr
            without_guards = re.sub(
                r"changes\(bioetl_\w+_created(?:\{.*?\})?\[[^]]+\]\)",
                "GENERATION_GUARD",
                expr,
            )
            assert "_created" not in without_guards, dashboard_path.name


def test_selected_range_kpis_follow_declared_counter_window_intent() -> None:
    """Selected-range KPI panels must match their declared counter-window intent."""
    panel_expectations = {
        "bioetl-incident-v1.json": {
            "Review Errors by Stage & Code": {
                "intent": "event_delta",
                "required": ("increase(",),
                "forbidden": ("max_over_time(", "last_over_time("),
            },
            "Compare Records by Stage & Run Type": {
                "intent": "event_delta",
                "required": ("increase(",),
                "forbidden": ("max_over_time(", "last_over_time("),
            },
            "Track Global Shutdown Starts": {
                "intent": "event_delta",
                "required": ("increase(",),
                "forbidden": ("max_over_time(", "last_over_time("),
            },
            "Track Global Shutdown Completions": {
                "intent": "event_delta",
                "required": ("increase(",),
                "forbidden": ("max_over_time(", "last_over_time("),
            },
        },
    }

    for dashboard_name, dashboard_expectations in panel_expectations.items():
        dashboard = load_dashboard(_require_dashboard(dashboard_name))
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title, expectation in dashboard_expectations.items():
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Dashboard {dashboard_name} missing panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert expressions
            assert any(
                any(snippet in expr for snippet in expectation["required"])
                for expr in expressions
            ), (
                f"Panel {panel_title!r} in {dashboard_name} must use "
                f"{expectation['required']!r} for {expectation['intent']} "
                "rather than raw counter values"
            )
            for forbidden in expectation["forbidden"]:
                assert all(forbidden not in expr for expr in expressions), (
                    f"Panel {panel_title!r} in {dashboard_name} has intent "
                    f"{expectation['intent']} and must not use {forbidden}"
                )


def test_all_max_over_time_counter_expressions_are_reviewed() -> None:
    policy = yaml.safe_load(MAX_OVER_TIME_COUNTER_POLICY_PATH.read_text("utf-8"))
    allowed_metrics = set(policy["allowed_counter_metrics"])
    counter_metrics = set(COUNTERS)
    reviewed: list[tuple[str, set[str], str]] = []

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            for target in panel.get("targets", []):
                expression = target.get("expr", "")
                if not isinstance(expression, str):
                    continue
                matched = set(_MAX_OVER_TIME_METRIC_RE.findall(expression))
                matched &= counter_metrics
                if matched:
                    source = (
                        f"{dashboard_path.name}:panel={panel.get('id')}:"
                        f"target={target.get('refId')}"
                    )
                    reviewed.append((source, matched, expression))

    rules = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    for group in rules.get("groups", []):
        for rule_index, rule in enumerate(group.get("rules", [])):
            expression = str(rule.get("expr", ""))
            matched = set(_MAX_OVER_TIME_METRIC_RE.findall(expression))
            matched &= counter_metrics
            if matched:
                rule_name = rule.get("record") or rule.get("alert")
                source = f"{group.get('name')}:{rule_name}:rule_index={rule_index}"
                reviewed.append((source, matched, expression))

    registry = policy["reviewed_expressions"]
    assert isinstance(registry, list)
    assert policy["reviewed_expression_count"] == len(registry)
    registry_ids = [str(row["id"]) for row in registry]
    live_ids = [source for source, _matched, _expression in reviewed]
    assert live_ids == registry_ids

    unexpected = {
        metric
        for _source, matched, _expression in reviewed
        for metric in matched - allowed_metrics
    }
    assert not unexpected
    assert policy["event_delta_function"] == "increase"
    assert policy["exact_multi_run_total_source"] == "RunLedger"

    for source, matched, expression in reviewed:
        if "bioetl_silver_filter_rejections_total" in matched:
            assert source.endswith(
                "bioetl_silver_filter_rejections_breakdown_total_15m:rule_index=151"
            ), source
            assert expression.startswith(
                "max_over_time((sum by (pipeline, run_type)"
            ), source


@pytest.mark.parametrize("dashboard_name", _PROCESSED_RECORDS_DASHBOARDS)
def test_processed_records_parameter_rows_sort_and_display_cleanly(
    dashboard_name: str,
) -> None:
    dashboard = load_dashboard(_require_dashboard(dashboard_name))
    panels = {p["id"]: p for p in get_dashboard_panels(dashboard)}
    identity, processed = panels[9402], panels[9403]
    assert identity["gridPos"]["w"] == processed["gridPos"]["w"] == 24
    assert identity["gridPos"]["y"] == 18
    assert processed["gridPos"]["y"] == 10
    assert processed["gridPos"]["h"] == 8
    assert processed["options"]["footer"]["enablePagination"] is True
    assert processed["options"]["cellHeight"] == "sm"
    assert not any(t["id"] == "limit" for t in processed["transformations"])
    _assert_processed_records_target_contract(processed)
    assert "Source unavailable" in processed["description"]
    assert processed["fieldConfig"]["defaults"]["custom"]["inspect"] is True
    organize = next(
        t["options"] for t in processed["transformations"] if t["id"] == "organize"
    )
    assert organize["renameByName"]["value"] == "count out"
    assert organize["indexByName"]["parameter"] == 0
    assert organize["excludeByName"]["row_status"] is True
    assert organize["excludeByName"]["Time"] is True
    assert "value A" not in organize["excludeByName"]
    assert "percentage A" not in organize["excludeByName"]
    assert "percintage" not in organize["excludeByName"]
    assert organize["excludeByName"].get("percentage") is not True
    parameter = next(
        o
        for o in processed["fieldConfig"]["overrides"]
        if o["matcher"].get("options") == "parameter"
    )
    props = {prop["id"]: prop["value"] for prop in parameter["properties"]}
    mappings = props["mappings"][0]["options"]
    assert tuple(mappings) == _PROCESSED_RECORDS_MAPPING_LABELS
    for label, display in zip(
        _PROCESSED_RECORDS_PARAMETER_LABELS,
        _PROCESSED_RECORDS_DISPLAY_LABELS,
        strict=True,
    ):
        assert mappings[label]["text"] == display
        if label in _PROCESSED_RECORDS_PRIMARY_COLORS:
            assert mappings[label]["color"] == _PROCESSED_RECORDS_PRIMARY_COLORS[label]
    assert "silver [filtered out]" != mappings["04 silver_quarantined_records"]["text"]
    assert props["custom.cellOptions"]["type"] == "color-text"
    assert props["custom.align"] == "left"
    # Other saved-run owners retain identity without duplicating this accounting table.
    assert not any(
        p["id"] == 9301
        for p in get_dashboard_panels(
            load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
        )
    )
    assert not any(
        p["id"] == 9403
        for p in get_dashboard_panels(
            load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
        )
    )
