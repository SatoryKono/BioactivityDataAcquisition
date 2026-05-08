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


def test_design_system_documents_missing_data_panel_class_contract() -> None:
    """Design docs must preserve missing-data semantics by panel class."""
    text = Path("docs/03-guides/dashboards/design-system.md").read_text(
        encoding="utf-8"
    )
    required_tokens = {
        "Missing-data semantics by panel class",
        "Current-status / current-cause panels",
        "Zero-valid event counters",
        "Timeseries / latency / histogram evidence",
        "Forensic tables and HTTP-backed explorer surfaces",
        "Telemetry-gap / trust-marker policy",
        "`or vector(0)` запрещён",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, (
        "dashboard design-system must document missing-data semantics; "
        f"missing={missing}"
    )


def test_summary_queries_use_zero_fallbacks() -> None:
    """Count summaries may synthesize zero only where absence means no events."""
    expected_panel_snippets = {
        "bioetl-runtime.json": {
            "Track Records by Stage / Interval": "or vector(0)",
            "Monitor Pipeline Alert Conditions": "or vector(0)",
            "Inspect DQ Alert Conditions": "or vector(0)",
            "Inspect Control-plane Alert Conditions": "or vector(0)",
            "Inspect GLOBAL Provider Alert Conditions": "or vector(0)",
            "Track GLOBAL Shutdown Initiated by Reason / Interval": "or vector(0)",
            "Track GLOBAL Shutdown Completed by Reason / Interval": "or vector(0)",
        },
        "bioetl-provider-health-v2.json": {
            "Monitor Healthy Checks (Selected Range)": "or vector(0)",
            "Monitor Degraded Checks (Selected Range)": "or vector(0)",
            "Track Provider Failure Rate (Selected Range)": "or vector(0)",
            "Track Health Checks Total (Selected Range)": "or vector(0)",
            "Inspect HTTP Errors by Method/Error Type": "or vector(0)",
        },
        "bioetl-dq-v2.json": {
            "Track: Records Quarantined in Range": "or vector(0)",
            "Track: Silver Filter Rejects in Range": "or vector(0)",
            "Track: Soft Threshold Exceeded in Range": "or vector(0)",
            "Monitor: Silver Validation Failures": "or vector(0)",
            "Monitor: Gold Strict Validation Failures": "or vector(0)",
        },
        "bioetl-control-plane-v1.json": {
            "Monitor: Manifest Write Failures": "or vector(0)",
            "Monitor: Ledger Append Failures": "or vector(0)",
            "Monitor: Checkpoint Incompatibilities": "or vector(0)",
            "Monitor: GLOBAL Control-Plane Read Failures": "or vector(0)",
            "Monitor: GLOBAL Control-Plane Read Failure Ratio": "or vector(0)",
            "Monitor: Checkpoint Load Failures": "or vector(0)",
            "Monitor: Checkpoint Save Failures": "or vector(0)",
            "Monitor: GLOBAL Checkpoint Operator Failures": "or vector(0)",
            "Monitor: Replay Not Reconstructable": "or vector(0)",
            "Monitor: Replay Drift": "or vector(0)",
            "Track: Replay / Resume Blockers in Range": "or vector(0)",
            "Track: GLOBAL Audit Write Outcomes": "or vector(0)",
            "Track: GLOBAL Audit Query Outcomes": "or vector(0)",
            "Monitor: Lineage Fragment Persistence Failures": "or vector(0)",
            "Monitor: Lineage Refs Missing": "or vector(0)",
        },
        "bioetl-workflow-overview.json": {
            "Failed Workflow Runs / Range": "or vector(0)",
            "Failed Pipeline Steps / Range": "or vector(0)",
            "Failed Transform Steps / Range": "or vector(0)",
            "Skipped Step Events / Range": "or vector(0)",
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


def test_workflow_selected_range_counters_use_zero_valid_empty_state() -> None:
    """Workflow summary cards intentionally render empty selected ranges as zero events."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-workflow-overview.json"))
    expected_panels = {
        "Failed Workflow Runs / Range",
        "Failed Pipeline Steps / Range",
        "Failed Transform Steps / Range",
        "Skipped Step Events / Range",
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
        ), f"{panel_title} must stay selected-range evidence"
        assert any("or vector(0)" in expr for expr in expressions), (
            f"{panel_title} must keep zero-valid fallback for empty selected ranges"
        )
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        assert defaults.get("noValue") == "0", (
            f"{panel_title} must keep noValue='0' for zero-valid event-count semantics"
        )
        description = str(panel.get("description", "")).lower()
        assert "selected" in description
        assert "`0` means no" in str(
            panel.get("description", "")
        ) or "0` means no" in str(panel.get("description", ""))


def test_runtime_selected_count_zeroes_are_scope_anchored() -> None:
    """Selected runtime count cards must keep UNKNOWN when selected scope is absent."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expected_panels = {
        "Monitor Failed Runs": "bioetl_runtime_pipeline_run_type_universe",
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
            f"{panel_title} must anchor zero fallback to runtime universe telemetry"
        )
        assert all("or vector(0)" not in expr for expr in expressions), (
            f"{panel_title} must not convert missing selected scope into false OK"
        )
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        assert defaults.get("noValue") == "UNKNOWN"


def test_runtime_alert_condition_summaries_are_telemetry_anchored() -> None:
    """Runtime handoff cards must preserve UNKNOWN for missing scope telemetry."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expected_anchor = {
        "Monitor Pipeline Alert Conditions": (
            "bioetl_runtime_pipeline_run_type_universe",
            'run_type=~"$run_type"',
        ),
        "Inspect DQ Alert Conditions": (
            "bioetl_runtime_pipeline_run_type_universe",
            'pipeline=~"$pipeline"',
        ),
        "Inspect Control-plane Alert Conditions": (
            "bioetl_runtime_pipeline_run_type_universe",
            'run_type=~"$run_type"',
        ),
        "Inspect GLOBAL Provider Alert Conditions": (
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
        "bioetl-runtime.json": {
            "Track Pipeline Phase Duration p50/p95/p99",
            "Track Pipeline Duration p50/p95/p99",
        },
        "bioetl-provider-health-v2.json": {
            "Track Health Check Latency by Provider (p95)",
            "Inspect Provider Health Check Latency (p95) - $provider",
            "Inspect Adapter Request Latency by Endpoint (p95)",
            "Track Rate Limiter Wait by Provider (p95)",
        },
        "bioetl-dq-v2.json": {"Track: DQ Check Duration (p95)"},
        "bioetl-control-plane-v1.json": {
            "Track: GLOBAL Control-Plane Read Latency p50/p95/p99",
            "Track: Checkpoint Save Latency p50/p95/p99",
            "Track: GLOBAL Checkpoint Operator Latency p50/p95/p99",
            "Track: GLOBAL Audit Write Latency p50/p95/p99",
            "Track: GLOBAL Audit Query Latency p50/p95/p99",
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


@pytest.mark.parametrize(
    ("dashboard_name", "panel_title", "description_snippet", "expected_no_value"),
    [
        (
            "bioetl-control-plane-v1.json",
            "Track: Replay Drift by Type",
            "No data means no replay drift events were observed in range or replay drift telemetry is absent",
            "No replay drift samples",
        ),
        (
            "bioetl-dq-v2.json",
            "Track: DQ Check Duration (p95)",
            "No data means no DQ duration samples were observed in range or DQ timing telemetry is absent",
            "No DQ duration samples",
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
    assert description_snippet in description
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == expected_no_value


def test_silver_reject_explorer_custom_no_value_copy_is_intentional_http_forensic_behavior() -> (
    None
):
    """Explorer keeps datasource-specific noValue copy because panels distinguish forensic states."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json")
    )
    expected_panels = {
        "Monitor Filtered Records Total": "Verify Quarantine Explorer before treating this as OK.",
        "Track Reject Rate vs Bronze": "Treat as UNKNOWN until Bronze denominator and quarantine API are confirmed.",
        "Inspect Run Scope Summary": "Check pipeline selection and Quarantine Explorer availability.",
        "Inspect Filtered Records Table": "No rejected records for current filters.",
        "Inspect Selected Record Details": "Select a payload_hash from the table",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == set(expected_panels)

    for panel_title, expected_no_value in expected_panels.items():
        panel = panels[panel_title]
        no_value = str(
            panel.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")
        )
        assert expected_no_value in no_value, (
            f"{panel_title} must preserve datasource-specific noValue guidance"
        )
        description = str(panel.get("description", "")).lower()
        assert any(
            token in description
            for token in ("quarantine explorer", "backend", "api", "unknown", "empty")
        ), (
            f"{panel_title} description must explain HTTP-forensic missing-data semantics"
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
            "Track: Records Quarantined in Range": "round(",
            "Track: Silver Filter Rejects in Range": "round(",
            "Track: Soft Threshold Exceeded in Range": "round(",
            "Monitor: Silver Validation Failures": "round(",
            "Monitor: Lineage Refs Missing": "round(",
        },
        "bioetl-runtime.json": {
            "Monitor Pipeline Alert Conditions": "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m",
            "Inspect DQ Alert Conditions": "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
            "Inspect Control-plane Alert Conditions": "bioetl_runtime_alert_condition_manifest_write_failed_15m",
            "Inspect GLOBAL Provider Alert Conditions": "bioetl_runtime_alert_condition_provider_failure_rate_high_15m",
            "Track GLOBAL Shutdown Initiated by Reason / Interval": "round(",
            "Track GLOBAL Shutdown Completed by Reason / Interval": "round(",
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
        ("bioetl-dq-v2.json", "Monitor: Data Quality Score (Volume-weighted)"),
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
            if item.get("title") == "Monitor: Worst-Entity DQ Score"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor: Worst-Entity DQ Score' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_dq_validation_score" in expr for expr in expressions)
    assert all("or vector(0)" not in expr for expr in expressions), (
        "Monitor: Worst-Entity DQ Score must preserve no-data rather than rendering score 0"
    )
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == "UNKNOWN", (
        "Monitor: Worst-Entity DQ Score must render missing score samples as UNKNOWN"
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


def test_dq_current_status_panels_use_explicit_status_value_mappings() -> None:
    """Current DQ status panels must render operator-facing status text, not raw enums."""
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

    expected_mapping = {
        "0": {"text": "OK", "color": "green"},
        "1": {"text": "WARN", "color": "orange"},
        "2": {"text": "CRIT", "color": "red"},
    }
    for panel_title, panel in panels.items():
        mappings = panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
        value_mapping = next(
            (mapping for mapping in mappings if mapping.get("type") == "value"),
            None,
        )
        assert value_mapping is not None, (
            f"{panel_title} must define explicit value mappings for 0/1/2"
        )
        assert value_mapping.get("options") == expected_mapping, (
            f"{panel_title} must map 0/1/2 to OK/WARN/CRIT"
        )


def test_dq_current_status_panels_use_canonical_severity_threshold_steps() -> None:
    """Current DQ status panels must use standard L0 severity threshold steps."""
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

    expected_steps = [
        {"color": "green", "value": None},
        {"color": "orange", "value": 1},
        {"color": "red", "value": 2},
    ]
    for panel_title, panel in panels.items():
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        assert defaults.get("thresholds", {}).get("steps") == expected_steps, (
            f"{panel_title} must use canonical 0/1/2 severity thresholds"
        )


def test_dq_first_screen_panels_expose_actionable_datalinks() -> None:
    """Current DQ operator panels must offer a direct next action."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Monitor DQ Current Status",
        "Monitor DQ Threshold State",
        "Inspect DQ Current Reasons",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == expected_panels

    for panel_title, panel in panels.items():
        data_links = panel.get("options", {}).get("dataLinks", [])
        assert data_links, f"{panel_title} must expose at least one actionable dataLink"
        assert all(link.get("title") for link in data_links), (
            f"{panel_title} dataLinks must have human-readable titles"
        )
        assert all(link.get("url") for link in data_links), (
            f"{panel_title} dataLinks must target a dashboard or runbook URL"
        )


def test_dq_threshold_state_panel_uses_bounded_reason_severity_with_ok_fallback() -> (
    None
):
    """Threshold-state summary must stay in a bounded enum and preserve explicit OK."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor DQ Threshold State"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor DQ Threshold State' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("max(bioetl_dq_current_reason" in expr for expr in expressions), (
        "Threshold state must derive severity from canonical current reasons"
    )
    assert any('severity="crit"' in expr for expr in expressions), (
        "Threshold state must map canonical crit reasons into severity=2"
    )
    assert any('severity="warn"' in expr for expr in expressions), (
        "Threshold state must map canonical warn reasons into severity=1"
    )
    assert any("bioetl_dq_current_status" in expr for expr in expressions), (
        "Threshold state must preserve explicit OK via bioetl_dq_current_status fallback"
    )
    assert all("sum(bioetl_dq_current_reason" not in expr for expr in expressions), (
        "Threshold state must not sum current reasons into an unbounded severity value"
    )


def test_runtime_diagnostic_panels_preserve_unknown_no_data_state() -> None:
    """Runtime diagnostic gauges must not convert missing telemetry to OK."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expected_panels = {
        "Monitor Runtime Current Status",
        "Monitor Runtime Telemetry Gap",
        "Monitor Runtime Blockers",
        "Monitor Runtime Error Rate",
        "Monitor Worst Stage Lag",
        "Monitor Memory Pressure Active",
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
    """Runtime telemetry gap must include Prometheus rule health, not scrape only."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Runtime Telemetry Gap"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor Runtime Telemetry Gap' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any('up{job="bioetl"}' in expr for expr in expressions)
    assert any(
        "prometheus_rule_evaluation_failures_total" in expr for expr in expressions
    )
    assert any(
        "prometheus_rule_group_last_evaluation_timestamp_seconds" in expr
        for expr in expressions
    )
    assert any("absent(" in expr for expr in expressions)
    assert any(
        "bioetl_observability[.]yml;bioetl_runtime_dashboard_recording$" in expr
        for expr in expressions
    )
    assert any("bioetl_runtime_dashboard_recording" in expr for expr in expressions), (
        "Telemetry gap must check the runtime dashboard recording group"
    )


def test_runtime_domain_thresholds_match_alert_rule_policy() -> None:
    """Runtime domain gauges should use real alert units, not generic 1/2 severity steps."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
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
        "Monitor Runtime Blockers": [
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
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Freshness Alert Conditions"
        ),
        None,
    )
    assert panel is not None, "Panel 'Inspect Freshness Alert Conditions' not found"

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


def test_provider_failure_rate_panel_uses_percentunit_domain_and_policy_thresholds() -> (
    None
):
    """Provider failure-rate gauge must use ratio semantics and policy thresholds."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Track Provider Failure Rate (Selected Range)"
        ),
        None,
    )
    assert panel is not None, (
        "Panel 'Track Provider Failure Rate (Selected Range)' not found"
    )

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("unit") == "percentunit"
    assert defaults.get("min") == 0
    assert defaults.get("max") == 1
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "green", "value": None},
        {"color": "orange", "value": 0.05},
        {"color": "red", "value": 0.2},
    ]


def test_provider_severity_matrix_preserves_unknown_and_critical_mapping() -> None:
    """Provider first-screen severity matrix must fail closed and color CRIT correctly."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor GLOBAL Provider Severity Matrix"
        ),
        None,
    )
    assert panel is not None, (
        "Panel 'Monitor GLOBAL Provider Severity Matrix' not found"
    )

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_provider_current_status" in expr for expr in expressions)
    assert all("or vector(0)" not in expr for expr in expressions), (
        "Provider severity matrix must preserve UNKNOWN/NO DATA instead of synthetic OK"
    )

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "green", "value": None},
        {"color": "orange", "value": 1},
        {"color": "red", "value": 2},
    ]
    special_mappings = [
        mapping.get("options", {})
        for mapping in defaults.get("mappings", [])
        if mapping.get("type") == "special"
    ]
    matches = {mapping.get("match") for mapping in special_mappings}
    assert {"null", "nan"} <= matches


def test_provider_critical_table_keeps_severity_only_scope() -> None:
    """Critical providers table must only show active degraded/failing rows."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Critical Providers"
        ),
        None,
    )
    assert panel is not None, "Panel 'Inspect Critical Providers' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert expressions == ["bioetl_provider_current_status >= 1"]

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "green", "value": None},
        {"color": "orange", "value": 1},
        {"color": "red", "value": 2},
    ]

    description = str(panel.get("description", ""))
    assert "DEGRADED or FAILING" in description
    assert "severity matrix" in description


def test_provider_health_status_panel_fails_closed_to_unknown() -> None:
    """Raw provider status panel must preserve UNKNOWN for known providers with no sample."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Current Provider Health Status"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor Current Provider Health Status' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_provider_health_status" in expr for expr in expressions)
    assert any(
        "bioetl_provider_health_check_provider_universe_15m" in expr
        for expr in expressions
    )
    assert all("or vector(0)" not in expr for expr in expressions), (
        "Provider raw status panel must fail closed to UNKNOWN, not synthetic OK"
    )

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    special_mappings = [
        mapping.get("options", {})
        for mapping in defaults.get("mappings", [])
        if mapping.get("type") == "special"
    ]
    matches = {mapping.get("match") for mapping in special_mappings}
    assert {"null", "nan"} <= matches


def test_provider_top_causes_panel_surfaces_projection_gap_instead_of_silent_empty() -> (
    None
):
    """Provider explainability must stay actionable even if cause projection drifts."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Provider Top Causes"
        ),
        None,
    )
    assert panel is not None, "Panel 'Inspect Provider Top Causes' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_provider_current_cause" in expr for expr in expressions)
    assert any("bioetl_provider_current_status >= 1" in expr for expr in expressions), (
        "Provider top causes must fallback to current-status explainability gap rows"
    )
    assert any("status_without_projected_cause" in expr for expr in expressions), (
        "Provider top causes must surface synthetic status_without_projected_cause fallback"
    )
    assert any("unless on (provider)" in expr for expr in expressions), (
        "Provider top causes fallback must trigger only when provider status has no cause projection"
    )

    combined = " ".join(
        (
            str(panel.get("description", "")),
            str(panel.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")),
        )
    )
    assert "status_without_projected_cause" in combined
    assert "cause-projection gap" in combined or "telemetry/rule gap" in combined


def test_provider_diagnostic_panels_preserve_no_data_for_tokens_and_circuit_breakers() -> (
    None
):
    """Token/circuit-breaker diagnostics must not synthesize healthy or fake adapter rows."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    expectations = {
        "Monitor Minimum Rate Limiter Tokens Available": (
            "bioetl_rate_limiter_tokens_available",
            "or vector(0)",
        ),
        "Monitor Cross-Scope Adapter Circuit Breaker State (max)": (
            "bioetl_circuit_breaker_state",
            "or vector(0)",
        ),
        "Track Cross-Scope Adapter Circuit Breaker Trips": (
            "bioetl_circuit_breaker_trips_total",
            'label_replace(vector(0), "adapter",',
        ),
    }

    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expectations
    }
    assert set(panels) == set(expectations)

    for panel_title, (required_snippet, forbidden_snippet) in expectations.items():
        expressions = [
            target.get("expr", "")
            for target in panels[panel_title].get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert any(required_snippet in expr for expr in expressions)
        assert all(forbidden_snippet not in expr for expr in expressions), (
            f"Panel '{panel_title}' must preserve diagnostic no-data instead of synthetic fallback"
        )


def test_provider_optional_telemetry_panels_explain_empty_samples_do_not_refute_status() -> (
    None
):
    """Optional provider telemetry must disclose no-sample semantics explicitly."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    expectations = {
        "Track Rate Limiter Wait by Provider (p95)": "optional telemetry can stay empty",
        "Monitor Minimum Rate Limiter Tokens Available": "optional telemetry can stay empty",
        "Monitor Cross-Scope Adapter Circuit Breaker State (max)": "adapter-scoped telemetry can stay empty",
        "Track Cross-Scope Adapter Circuit Breaker Trips": "does not refute current provider severity",
    }

    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expectations
    }
    assert panels.keys() == expectations.keys()

    for title, token in expectations.items():
        combined = " ".join(
            (
                str(panels[title].get("description", "")),
                str(
                    panels[title]
                    .get("fieldConfig", {})
                    .get("defaults", {})
                    .get("noValue", "")
                ),
            )
        ).lower()
        assert token in combined, (
            f"{title} must explain its empty optional-telemetry semantics"
        )


def test_provider_degraded_checks_panel_uses_neutral_evidence_thresholds() -> None:
    """Selected-range degraded-count evidence must not reuse current-severity thresholds."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Degraded Checks (Selected Range)"
        ),
        None,
    )
    assert panel is not None, (
        "Panel 'Monitor Degraded Checks (Selected Range)' not found"
    )

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "green", "value": None}
    ]


def test_dq_selected_range_evidence_panels_use_neutral_thresholds() -> None:
    """Selected-range DQ evidence cards must not reuse live severity thresholds."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Track: Source Records in Range (Bronze)",
        "Track: Clean Records in Range (Gold)",
        "Track: Records Quarantined in Range",
        "Track: Soft Threshold Exceeded in Range",
        "Track: Silver Filter Rejects in Range",
    }

    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == expected_panels

    for panel_title, panel in panels.items():
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        assert defaults.get("thresholds", {}).get("steps") == [
            {"color": "gray", "value": None}
        ], f"{panel_title} must use neutral evidence thresholds"


def test_dq_blocked_share_panels_use_percentunit_domain_and_policy_thresholds() -> None:
    """Blocked-share panels must share the same 0..1/percentunit DQ policy semantics."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Monitor: DQ Impact on Deliverability (Blocked Share)",
        "Track: DQ Impact on Deliverability Trend (Blocked Share %)",
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
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        assert any(
            'stage="bronze"' in expr and "bioetl_records_processed_total" in expr
            for expr in expressions
        ), (
            f"Panel '{panel_title}' must use Bronze input as the blocked-share denominator"
        )
        assert any(
            "bioetl_dq_records_quarantined_total" in expr for expr in expressions
        ), (
            f"Panel '{panel_title}' must include quarantined records in blocked-share impact"
        )
        assert all(
            'stage=~"raw|validated|enriched|filtered_out|deduplicated|final"'
            not in expr
            for expr in expressions
        ), (
            f"Panel '{panel_title}' must not use legacy/unconfirmed stage regex in the denominator"
        )


def test_dq_freshness_lag_panel_uses_time_domain_thresholds() -> None:
    """Freshness lag must use the same 24h/72h thresholds as the DQ alert policy."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor: Worst Data Freshness Lag (seconds)"
        ),
        None,
    )
    assert panel is not None, "Freshness lag panel not found in bioetl-dq-v2.json"

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "green", "value": None},
        {"color": "orange", "value": 86400},
        {"color": "red", "value": 259200},
    ]


def test_dq_problem_panels_expose_actionable_datalinks() -> None:
    """Key DQ incident panels must offer direct operator handoff."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Monitor: Worst-Entity DQ Score",
        "Monitor: Worst Data Freshness Lag (seconds)",
        "Track: Silver Filter Rejects in Range",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == expected_panels

    for panel_title, panel in panels.items():
        data_links = panel.get("options", {}).get("dataLinks", [])
        assert data_links, f"{panel_title} must expose at least one actionable dataLink"
        assert all(
            str(link.get("title", "")).startswith("Open ") for link in data_links
        ), f"{panel_title} must use canonical Open ... dataLink titles"

    assert not panels["Track: Silver Filter Rejects in Range"].get("links"), (
        "Track: Silver Filter Rejects in Range should use options.dataLinks, not legacy panel links"
    )


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
            "Historical Failures": ("increase(",),
            "Recent Terminal Runs": ("increase(",),
        },
        "bioetl-dq-v2.json": {
            "Track Range Evidence: Bronze -> Silver -> Gold": (
                "increase(",
                "last_over_time(",
            ),
            "Track: Source Records in Range (Bronze)": ("increase(", "last_over_time("),
            "Track: Clean Records in Range (Gold)": ("increase(", "last_over_time("),
        },
        "bioetl-runtime.json": {
            "Inspect Errors by Stage / Error Code / Range": ("increase(",),
            "Track Records by Stage / Run Type / Range": ("increase(",),
            "Track GLOBAL Shutdown Initiated by Reason / Interval": ("increase(",),
            "Track GLOBAL Shutdown Completed by Reason / Interval": ("increase(",),
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


def test_exact_duplicate_promql_groups_are_only_explicitly_justified_reuse() -> None:
    """Exact duplicate PromQL must stay limited to audited, role-justified reuse."""
    observed_uses_by_expr: dict[str, set[tuple[str, str]]] = {}

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title")
            if not isinstance(title, str):
                continue
            for target in panel.get("targets", []):
                expr = target.get("expr")
                if not isinstance(expr, str) or not expr.strip():
                    continue
                normalized_expr = " ".join(expr.split())
                observed_uses_by_expr.setdefault(normalized_expr, set()).add(
                    (dashboard_path.name, title)
                )

    duplicate_uses_by_expr = {
        expr: uses for expr, uses in observed_uses_by_expr.items() if len(uses) > 1
    }
    expected_duplicate_uses = {
        '((sum((bioetl_dq_validation_score{pipeline=~"$pipeline"} * '
        'bioetl_dq_validation_record_count{pipeline=~"$pipeline"}))) / '
        'clamp_min(sum(bioetl_dq_validation_record_count{pipeline=~"$pipeline"}), '
        "1))": {
            (
                "bioetl-dq-v2.json",
                "Monitor: Data Quality Score (Volume-weighted)",
            ),
            (
                "bioetl-dq-v2.json",
                "Track: Data Quality Score Trend (Volume-weighted)",
            ),
        },
        'round(sum(increase(bioetl_lineage_refs_missing_total{pipeline=~"$pipeline"}'
        "[$__range])) or vector(0))": {
            ("bioetl-control-plane-v1.json", "Monitor: Lineage Refs Missing"),
            ("bioetl-dq-v2.json", "Monitor: Lineage Refs Missing"),
        },
    }
    assert duplicate_uses_by_expr == expected_duplicate_uses, (
        "Dashboard exact PromQL duplication drifted outside the audited allowlist: "
        f"{duplicate_uses_by_expr}"
    )

    dq_dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    dq_panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dq_dashboard)
        if panel.get("title")
    }
    score_gauge = dq_panels["Monitor: Data Quality Score (Volume-weighted)"]
    score_trend = dq_panels["Track: Data Quality Score Trend (Volume-weighted)"]
    assert score_gauge.get("type") == "gauge"
    assert score_gauge.get("options", {}).get("showThresholdMarkers") is True
    assert score_trend.get("type") == "timeseries"
    assert score_trend.get("options", {}).get("tooltip", {}).get("mode") == "single"
    assert "review trend" in str(score_gauge.get("description", "")).lower()
    assert (
        "trend over selected time range"
        in str(score_trend.get("description", "")).lower()
    )

    control_plane_dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-control-plane-v1.json")
    )
    control_plane_panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(control_plane_dashboard)
        if panel.get("title")
    }
    dq_lineage = dq_panels["Monitor: Lineage Refs Missing"]
    control_plane_lineage = control_plane_panels["Monitor: Lineage Refs Missing"]
    assert dq_lineage.get("options", {}).get("graphMode") == "none"
    assert control_plane_lineage.get("options", {}).get("graphMode") == "area"
    assert (
        "does not replace control plane diagnostics"
        in str(dq_lineage.get("description", "")).lower()
    )
    assert (
        "missing lineage can make replay evidence incomplete"
        in str(control_plane_lineage.get("description", "")).lower()
    )
