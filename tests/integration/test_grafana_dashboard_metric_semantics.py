"""Grafana dashboard metric semantics and no-data contracts."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    get_panel_expressions,
    load_dashboard,
)


pytestmark = pytest.mark.integration


def test_summary_queries_use_zero_fallbacks() -> None:
    """Runtime/provider summary panels should show zero instead of no-data."""
    expected_panel_snippets = {
        "bioetl-runtime.json": {
            "Runtime Blockers": "or vector(0)",
            "Failed Runs": "or vector(0)",
            "No-Records Runs": "or vector(0)",
            "Records by Stage / Interval": "or vector(0)",
            "Pipeline Alert Conditions": "or vector(0)",
            "DQ Alert Conditions": "or vector(0)",
            "Control-plane Alert Conditions": "or vector(0)",
            "GLOBAL Provider Alert Conditions": "or vector(0)",
            "Freshness Alert Conditions": "or vector(0)",
            "Shutdown Initiated by Reason / Interval": "or vector(0)",
            "Shutdown Completed by Reason / Interval": "or vector(0)",
        },
        "bioetl-provider-health-v2.json": {
            "Monitor Healthy Checks (Selected Range)": "or vector(0)",
            "Monitor Degraded Checks (Selected Range)": "or vector(0)",
            "Track Provider Failure Rate (Selected Range)": "or vector(0)",
            "Track Health Checks Total (Selected Range)": "or vector(0)",
            "HTTP Errors by Method / Error Type": "or vector(0)",
            "Minimum Rate Limiter Tokens Available": "or vector(0)",
            "Circuit Breaker State (max)": "or vector(0)",
            "Circuit Breaker Trips by Provider": 'or label_replace(vector(0), "adapter",',
        },
        "bioetl-dq-v2.json": {
            "Records Quarantined": "or vector(0)",
            "Silver Filter Rejects": "or vector(0)",
            "Soft Threshold Exceeded": "or vector(0)",
            "Silver Validation Failures": "or vector(0)",
            "Gold Strict Validation Failures": "or vector(0)",
        },
        "bioetl-control-plane-v1.json": {
            "Replay / Resume Blockers": "or vector(0)",
            "Manifest Write Failures": "or vector(0)",
            "Ledger Append Failures": "or vector(0)",
            "Checkpoint Incompatibilities": "or vector(0)",
            "GLOBAL Control-Plane Read Failures": "or vector(0)",
            "GLOBAL Control-Plane Read Failure Ratio": "or vector(0)",
            "Checkpoint Load Failures": "or vector(0)",
            "Checkpoint Save Failures": "or vector(0)",
            "GLOBAL Checkpoint Operator Failures": "or vector(0)",
            "Replay Not Reconstructable": "or vector(0)",
            "Replay Drift": "or vector(0)",
            "Replay Lag Seconds": "or vector(0)",
            "Audit Write Outcomes": "or vector(0)",
            "Audit Query Outcomes": "or vector(0)",
            "Lineage Fragment Persistence Failures": "or vector(0)",
            "Lineage Refs Missing": "or vector(0)",
        },
    }

    for dashboard_name, panel_expectations in expected_panel_snippets.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
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
            assert expressions, (
                f"Dashboard {dashboard_name} panel {panel_title!r} has no expressions"
            )
            assert any(expected_snippet in expr for expr in expressions), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must include "
                f"{expected_snippet!r} to render zero instead of no-data"
            )


def test_latency_p95_panels_preserve_no_data_state() -> None:
    """Latency p95 panels must not collapse missing samples into zero."""
    expected_latency_panels = {
        "bioetl-runtime.json": {
            "Pipeline Phase Duration p50/p95/p99",
            "Pipeline Duration p50/p95/p99",
        },
        "bioetl-provider-health-v2.json": {
            "Track Health Check Latency by Provider (p95)",
            "Provider Health Check Latency (p95) - $provider",
            "Adapter Request Latency by Endpoint (p95)",
            "Rate Limiter Wait by Provider (p95)",
        },
        "bioetl-dq-v2.json": {"DQ Check Duration (p95)"},
        "bioetl-control-plane-v1.json": {
            "GLOBAL Control-Plane Read Latency p50/p95/p99",
            "Checkpoint Save Latency p50/p95/p99",
            "GLOBAL Checkpoint Operator Latency p50/p95/p99",
            "Audit Write Latency p50/p95/p99",
            "Audit Query Latency p50/p95/p99",
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
            assert any("histogram_quantile(0.95" in expr for expr in expressions), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must stay histogram-backed"
            )
            assert all("or vector(0)" not in expr for expr in expressions), (
                f"Dashboard {dashboard_name} panel {panel_title!r} must preserve "
                "no-data instead of rendering zero latency"
            )


def test_count_like_summary_panels_use_rounding_or_boolean_conditions() -> None:
    """Count-like summary panels should avoid fractional event semantics."""
    expected_panel_snippets = {
        "bioetl-provider-health-v2.json": {
            "Monitor Healthy Checks (Selected Range)": "round(",
            "Monitor Degraded Checks (Selected Range)": "round(",
            "Track Health Checks Total (Selected Range)": "round(",
        },
        "bioetl-dq-v2.json": {
            "Records Quarantined": "round(",
            "Silver Filter Rejects": "round(",
            "Soft Threshold Exceeded": "round(",
            "Silver Validation Failures": "round(",
            "Lineage Refs Missing": "round(",
        },
        "bioetl-runtime.json": {
            "Pipeline Alert Conditions": "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m",
            "DQ Alert Conditions": "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
            "Control-plane Alert Conditions": "bioetl_runtime_alert_condition_manifest_write_failed_15m",
            "GLOBAL Provider Alert Conditions": "bioetl_runtime_alert_condition_provider_failure_rate_high_15m",
            "Shutdown Initiated by Reason / Interval": "round(",
            "Shutdown Completed by Reason / Interval": "round(",
        },
    }

    for dashboard_name, panel_expectations in expected_panel_snippets.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
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


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-dq-v2.json", "Data Quality Score (Volume-weighted)"),
    ],
)
def test_dq_score_uses_validation_metric(dashboard_file, panel_title):
    """Ensure DQ score panels use the canonical DQ validation metric."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_file)
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == panel_title
        ),
        None,
    )
    assert panel is not None, f"Panel '{panel_title}' not found in {dashboard_file}"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_dq_validation_score" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use bioetl_dq_validation_score"
    )
    assert any("bioetl_dq_validation_record_count" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must use "
        "bioetl_dq_validation_record_count for volume-aware weighting"
    )
    assert all("or vector(0)" not in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must preserve no-data state "
        "instead of coercing missing telemetry to zero"
    )
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == "UNKNOWN", (
        f"Panel '{panel_title}' in {dashboard_file} must render missing score "
        "samples as UNKNOWN"
    )


def test_worst_entity_dq_score_preserves_no_data_state() -> None:
    """Worst-score gauges must not collapse missing DQ samples into score zero."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Worst-Entity DQ Score"
        ),
        None,
    )
    assert panel is not None, "Panel 'Worst-Entity DQ Score' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_dq_validation_score" in expr for expr in expressions)
    assert all("or vector(0)" not in expr for expr in expressions), (
        "Worst-Entity DQ Score must preserve no-data rather than rendering score 0"
    )
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == "UNKNOWN", (
        "Worst-Entity DQ Score must render missing score samples as UNKNOWN"
    )


def test_dq_current_status_panels_preserve_unknown_no_data_state() -> None:
    """Current DQ status panels must not convert missing telemetry to OK."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Monitor DQ Current Status",
        "Monitor DQ Threshold State",
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
            f"{panel_title} must render missing current status as UNKNOWN"
        )


def test_runtime_diagnostic_panels_preserve_unknown_no_data_state() -> None:
    """Runtime diagnostic gauges must not convert missing telemetry to OK."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expected_panels = {
        "Monitor Runtime Current Status",
        "Monitor Runtime Telemetry Gap",
        "Runtime Error Rate",
        "Worst Stage Lag",
        "Memory Pressure Active",
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


def test_dq_blocked_share_panels_use_percentunit_domain_and_policy_thresholds() -> None:
    """Blocked-share panels must share the same 0..1/percentunit DQ policy semantics."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "DQ Impact on Deliverability (Blocked Share)",
        "DQ Impact on Deliverability Trend (Blocked Share %)",
    }
    expected_threshold_steps = [
        {"color": "green", "value": None},
        {"color": "orange", "value": 0.05},
        {"color": "red", "value": 0.2},
    ]

    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == expected_panels, (
        "DQ dashboard must expose both blocked-share summary and trend panels"
    )

    for panel_title, panel in panels.items():
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        assert defaults.get("unit") == "percentunit", (
            f"Panel '{panel_title}' must use percentunit for ratio semantics"
        )
        assert defaults.get("min") == 0, f"Panel '{panel_title}' must use min=0"
        assert defaults.get("max") == 1, f"Panel '{panel_title}' must use max=1"
        assert (
            defaults.get("thresholds", {}).get("steps") == expected_threshold_steps
        ), f"Panel '{panel_title}' must use DQ policy thresholds (warn=0.05, crit=0.20)"


def test_dashboards_do_not_use_prometheus_created_timestamps() -> None:
    """Operator dashboards must not expose Prometheus client bookkeeping timestamps."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        expressions = get_panel_expressions(dashboard)
        assert all("_created" not in expr for expr in expressions), (
            f"Dashboard {dashboard_path.name} must not use Prometheus *_created series"
        )


def test_selected_range_kpis_do_not_use_raw_counters() -> None:
    """Selected-range KPI panels must use windowed counter semantics."""
    allowed_panel_snippets = {
        "bioetl-overview-v2.json": {
            "Historical Failures (range evidence)": ("increase(",),
            "Recent terminal runs (range evidence)": ("increase(",),
        },
        "bioetl-dq-v2.json": {
            "Track Range Evidence: Bronze -> Silver -> Gold": (
                "increase(",
                "last_over_time(",
            ),
            "Source Records in Range (Bronze)": ("increase(", "last_over_time("),
            "Clean Records in Range (Gold)": ("increase(", "last_over_time("),
        },
        "bioetl-runtime.json": {
            "Errors by Stage / Error Code / Range": ("increase(",),
            "Records by Stage / Run Type / Range": ("increase(",),
            "Shutdown Initiated by Reason / Interval": ("increase(",),
            "Shutdown Completed by Reason / Interval": ("increase(",),
        },
    }

    for dashboard_name, panel_expectations in allowed_panel_snippets.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title, allowed_snippets in panel_expectations.items():
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"Dashboard {dashboard_name} missing panel {panel_title!r}"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert any(
                any(snippet in expr for snippet in allowed_snippets)
                for expr in expressions
            ), (
                f"Panel {panel_title!r} in {dashboard_name} must use "
                f"one of {allowed_snippets!r} rather than raw counter values"
            )
            assert all("last_over_time(" not in expr for expr in expressions), (
                f"Panel {panel_title!r} in {dashboard_name} must not use "
                "last_over_time() for counter-range KPIs"
            )
