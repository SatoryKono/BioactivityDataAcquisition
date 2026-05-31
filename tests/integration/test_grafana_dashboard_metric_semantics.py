"""Grafana dashboard metric semantics and no-data contracts."""

import json
from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    get_panel_expressions,
    load_dashboard,
)
from tests.integration.grafana_contract_specs import (
    SUMMARY_ZERO_FALLBACK_EXPECTATIONS,
)


pytestmark = pytest.mark.integration
_PROCESSED_RECORDS_DASHBOARDS = (
    "bioetl-control-plane-v1.json",
    "bioetl-dq-v2.json",
    "bioetl-overview-v2.json",
    "bioetl-provider-health-v2.json",
    "bioetl-runtime.json",
    "bioetl-workflow-overview.json",
)

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
    mappings: list[dict[str, object]] = []
    for label in _PROCESSED_RECORDS_PARAMETER_LABELS:
        result = {"text": "$1"}
        if label in _PROCESSED_RECORDS_PRIMARY_COLORS:
            result["color"] = _PROCESSED_RECORDS_PRIMARY_COLORS[label]
        mappings.append(
            {
                "type": "regex",
                "options": {
                    "pattern": f"^{label}\\|(.*)$",
                    "result": result,
                },
            }
        )
    return mappings


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


def _expected_duplicate_uses() -> dict[str, set[tuple[str, str]]]:
    return {
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
        'max((bioetl_replay_safety_blockers_15m{run_type=~"$run_type"}) and '
        'on(pipeline) label_replace(label_replace(vector(1), "pipeline_raw", "$pipeline", "", ""), '
        '"pipeline", "$1", "pipeline_raw", "^(?:workflow_)?(.*)$"))': {
            ("bioetl-control-plane-v1.json", "Monitor: Replay Safety State"),
            ("bioetl-control-plane-v1.json", "Status"),
        },
        'max(bioetl_dq_current_status{pipeline=~"$pipeline"})': {
            ("bioetl-dq-v2.json", "Monitor DQ Current Status"),
            ("bioetl-dq-v2.json", "Status"),
        },
        'max(bioetl_runtime_current_status{pipeline=~"$pipeline",run_type=~"$run_type"} '
        'or ((bioetl_runtime_current_status{run_type=~"$run_type"}) and on(pipeline) '
        'label_replace(label_replace(vector(1), "pipeline_raw", "$pipeline", "", ""), '
        '"pipeline", "$1", "pipeline_raw", "^(?:workflow_)?(.*)$")))': {
            ("bioetl-runtime.json", "Runtime Status"),
            ("bioetl-runtime.json", "Status"),
        },
    }


def _assert_dq_duplicate_reuse_semantics() -> None:
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


def _assert_lineage_control_plane_ownership_handoff() -> None:
    dq_dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    control_plane_dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-control-plane-v1.json")
    )
    dq_panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dq_dashboard)
        if panel.get("title")
    }
    control_plane_panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(control_plane_dashboard)
        if panel.get("title")
    }
    dq_handoff = dq_panels["Review: Lineage Handoff to Control Plane"]
    control_plane_lineage = control_plane_panels["Monitor: Lineage Refs Missing"]
    assert dq_handoff.get("type") == "text"
    dq_content = str(dq_handoff.get("options", {}).get("content", "")).lower()
    assert "control plane" in dq_content
    assert "canonical" in dq_content
    dq_links = list(dq_handoff.get("links") or [])
    assert any(
        "bioetl-control-plane-v1" in str(link.get("url", ""))
        and "viewPanel=904" in str(link.get("url", ""))
        for link in dq_links
    )
    assert control_plane_lineage.get("options", {}).get("graphMode") == "area"
    assert (
        "missing lineage can make replay evidence incomplete"
        in str(control_plane_lineage.get("description", "")).lower()
    )


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
    expected_panel_snippets = SUMMARY_ZERO_FALLBACK_EXPECTATIONS

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
            ("increase(" in expr or "max_over_time(" in expr) and "[$__range]" in expr
            for expr in expressions
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


def test_overview_compact_evidence_panels_do_not_claim_l0_current_verdict() -> None:
    """Overview compact evidence panels must stay below the current L0 verdict path."""
    current_verdict_titles = {
        "Status",
        "First Action",
        "Inputs",
        "Control Plane",
        "Runtime",
        "Data Quality",
        "Provider",
        "Data Validation",
        "Workflow",
    }
    compact_evidence = {
        "Runtime Blockers Trend": (9018, "bioetl_l1_runtime_blocker_status"),
        "DQ Status Trend": (9019, "bioetl_l1_dq_status"),
        "Gold Lifecycle Trend": (9020, "bioetl_l1_gold_lifecycle_status"),
        "Historical Failures": (9010, "bioetl_pipeline_runs_total"),
        "Recent Terminal Runs": (9011, "bioetl_pipeline_runs_total"),
    }

    for dashboard_path in (Path("grafana/dashboards/bioetl-overview-v2.json"),):
        dashboard = load_dashboard(dashboard_path)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        max_current_y = max(
            panels[title].get("gridPos", {}).get("y", 0)
            for title in current_verdict_titles
        )

        for panel_title, (panel_id, expected_metric) in compact_evidence.items():
            panel = panels[panel_title]
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            description = str(panel.get("description", "")).lower()
            data_links = panel.get("options", {}).get("dataLinks", [])

            assert panel.get("id") == panel_id, dashboard_path
            assert panel.get("gridPos", {}).get("y", 0) > max_current_y
            assert any(expected_metric in expr for expr in expressions), dashboard_path
            assert all(
                forbidden not in "\n".join(expressions)
                for forbidden in (
                    "run_id",
                    "quarantine_run_id",
                    "payload_hash",
                    "error_message",
                )
            )
            assert "selected-range" in description
            assert "evidence" in description
            assert "does not determine l0 status or first action" in description
            assert data_links
            assert all(
                str(link.get("title", "")).startswith("Open ") for link in data_links
            )

        for panel_title in ("Status", "First Action"):
            assert "$__range" not in "\n".join(
                get_panel_expressions(panels[panel_title])
            )


@pytest.mark.parametrize(
    "dashboard_name",
    [
        "bioetl-control-plane-v1.json",
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
        "bioetl-workflow-overview.json",
    ],
)
def test_operator_context_shell_panels_preserve_canonical_semantics(
    dashboard_name: str,
) -> None:
    """Shared context shell panels must preserve Overview-derived semantics."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    expected_ids = {
        "Provenance": 9400,
        "Status": 9401,
        "ID": 9402,
        "Processed Records": 9403,
    }
    assert expected_ids.keys() <= panels.keys()

    for panel_title, expected_id in expected_ids.items():
        assert panels[panel_title].get("id") == expected_id

    provenance = panels["Provenance"]
    provenance_description = str(provenance.get("description", "")).lower()
    provenance_content = str(provenance.get("options", {}).get("content", "")).lower()
    assert "scope:" in provenance_description
    assert "workflow" in provenance_description
    assert "pipeline" in provenance_description
    assert "run_type" in provenance_description
    assert "run_id" in provenance_description
    assert "local control-plane identity context only" in provenance_description
    if dashboard_name == "bioetl-workflow-overview.json":
        assert "run id only fills the local id card" in provenance_content
        assert "selected-range workflow scope" in provenance_content
        assert "exact run: id card only" in provenance_content
        assert "never exact-run proof" in provenance_content
    assert "context shell:" not in provenance_content
    assert "workflow=" not in provenance_content
    assert "pipeline=" not in provenance_content
    assert "run id=" not in provenance_content
    assert "run_id is http identity context" not in provenance_content

    status = panels["Status"]
    status_expressions = get_panel_expressions({"panels": [status]})
    status_description = str(status.get("description", "")).lower()
    assert status_expressions
    assert all("run_id" not in expr for expr in status_expressions)
    assert all("payload_hash" not in expr for expr in status_expressions)
    if dashboard_name == "bioetl-workflow-overview.json":
        assert any("$__range" in expr for expr in status_expressions)
        assert "selected-range workflow evidence status" in status_description
        assert "not current live run state" in status_description
        assert "not exact-run evidence" in status_description
        assert "run_id remains local id-only identity context" in status_description
    elif dashboard_name == "bioetl-provider-health-v2.json":
        assert any("${__range_s}" in expr for expr in status_expressions)
        assert any(
            "bioetl_provider_current_status" in expr for expr in status_expressions
        )
        assert any(
            "bioetl_provider_range_operational_ok" in expr
            for expr in status_expressions
        )
        assert "selected-range" in status_description
        assert "fail-closed" in status_description
        assert "monitor provider telemetry freshness" in status_description
        assert "review raw provider health enum" in status_description
        assert "secondary context only" in status_description
        assert not any("), max_over_time" in expr for expr in status_expressions)
    else:
        assert all("$__range" not in expr for expr in status_expressions)
        assert "current" in status_description
    assert "0=ok" in status_description
    assert "null=unknown" in status_description

    identity = panels["ID"]
    identity_description = str(identity.get("description", "")).lower()
    assert identity.get("datasource") == "Quarantine Explorer"
    identity_target = identity.get("targets", [])[0]
    assert identity_target.get("format") == "table"
    assert identity_target.get("parser") == "backend"
    assert identity_target.get("root_selector") == "rows"
    assert identity_target.get("source") == "url"
    assert identity_target.get("url_options", {}).get("method") == "GET"
    assert identity_target.get("url") == (
        "/ops/control-plane/identity-table?"
        "pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}"
    )
    if dashboard_name == "bioetl-provider-health-v2.json":
        assert "pipeline/run context evidence only" in identity_description
        assert "does not prove current provider health" in identity_description

    processed = panels["Processed Records"]
    processed_expressions = get_panel_expressions({"panels": [processed]})
    processed_description = str(processed.get("description", "")).lower()
    assert processed.get("datasource") == "Quarantine Explorer"
    assert processed_expressions == []
    processed_target = processed.get("targets", [])[0]
    assert processed_target.get("format") == "table"
    assert processed_target.get("parser") == "backend"
    assert processed_target.get("root_selector") == "rows"
    assert processed_target.get("source") == "url"
    assert processed_target.get("url_options", {}).get("method") == "GET"
    assert processed_target.get("url") == (
        "/ops/observability/processed-records?"
        "pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}"
    )
    assert "accounting" in processed_description
    assert "evidence" in processed_description
    assert "missing" in processed_description
    assert "not ok" in processed_description
    assert "not displayed" in processed_description
    if dashboard_name == "bioetl-provider-health-v2.json":
        assert "does not prove current provider health" in processed_description
        assert "monitor provider telemetry freshness" in processed_description

    dashboard_promql = "\n".join(get_panel_expressions(dashboard))
    assert "$run_id" not in dashboard_promql
    assert "${run_id}" not in dashboard_promql


def test_control_plane_identity_evidence_uses_http_not_prometheus_labels() -> None:
    """Full identity anchors must stay on HTTP-backed tables, not Prometheus labels."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    identity_panels = [
        panels["Inspect: Overview Identity Anchors"],
        panels["Inspect: Identity Gaps"],
        panels["Inspect: Checkpoint Anchor Compare"],
        panels["Inspect: Copyable Identity Handoffs"],
        panels["Inspect: P1 Replay and Evidence Anchors"],
        panels["Inspect: P2 Forensic Anchors"],
    ]

    for panel in identity_panels:
        assert panel.get("datasource") == "Quarantine Explorer"
        assert get_panel_expressions({"panels": [panel]}) == []
        target = panel.get("targets", [])[0]
        assert "/ops/control-plane/identity-evidence?" in target.get("url", "")
        assert target.get("root_selector") == "rows"

    prometheus_expressions = "\n".join(get_panel_expressions(dashboard))
    forbidden_label_tokens = (
        "run_id=~",
        "manifest_id=~",
        "execution_fingerprint=~",
        "effective_config_hash=~",
        "input_snapshot_identity_fingerprint=~",
        "composite_run_identity=~",
    )
    assert all(token not in prometheus_expressions for token in forbidden_label_tokens)


def test_control_plane_identity_evidence_documents_short_full_split() -> None:
    """The dashboard must keep short overview values and full detail values distinct."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    panel = next(
        panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") == "Inspect: Overview Identity Anchors"
    )
    description = str(panel.get("description", "")).lower()
    assert "shortened in value_short" in description
    assert "full in value_full" in description
    transformation_payload = json.dumps(panel.get("transformations", []))
    assert "value_short" in transformation_payload
    assert "value_full" in transformation_payload
    assert "source_type" in transformation_payload
    assert "drilldown_target" in transformation_payload


def test_runtime_selected_count_zeroes_are_scope_anchored() -> None:
    """Selected runtime count cards must keep UNKNOWN when selected scope is absent."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expected_panels = {
        "Failed Runs": "bioetl_runtime_pipeline_run_type_universe",
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
        "Inspect Provider Alert Conditions": (
            "bioetl_provider_current_status",
            'provider=~"$provider_hint"',
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
            "Track: Silver Validation Failures in Range": "round(",
            "Monitor: Silver Validation Failures": "round(",
        },
        "bioetl-runtime.json": {
            "Monitor Pipeline Alert Conditions": "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m",
            "Inspect DQ Alert Conditions": "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
            "Inspect Control-plane Alert Conditions": "bioetl_runtime_alert_condition_manifest_write_failed_15m",
            "Inspect Provider Alert Conditions": "bioetl_runtime_alert_condition_provider_failure_rate_high_15m",
            "Inspect GLOBAL Provider Alert Conditions": (
                "bioetl_runtime_alert_condition_provider_adapter_latency_high_30m"
            ),
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
        "Runtime Status",
        "Runtime Telemetry Gap",
        "Monitor Runtime Blockers",
        "Runtime Error Rate",
        "Worst Stage Lag",
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
            if item.get("title") == "Runtime Telemetry Gap"
        ),
        None,
    )
    assert panel is not None, "Panel 'Runtime Telemetry Gap' not found"

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
        "Runtime Error Rate": [
            {"color": "green", "value": None},
            {"color": "orange", "value": 0.05},
            {"color": "red", "value": 0.2},
        ],
        "Worst Stage Lag": [
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
        panels["Runtime Error Rate"].get("fieldConfig", {}).get("defaults", {})
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
            if item.get("title") == "Inspect Freshness Lagged Entities >24h"
        ),
        None,
    )
    assert panel is not None, "Panel 'Inspect Freshness Lagged Entities >24h' not found"

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


def test_provider_telemetry_freshness_marks_missing_current_status_as_warn() -> None:
    """Provider first screen must expose telemetry freshness separately from health."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Provider Telemetry Freshness"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor Provider Telemetry Freshness' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert len(expressions) == 1
    expression = expressions[0]
    assert (
        "count_over_time(bioetl_provider_current_status{provider=~\"$provider\"}"
        in expression
    )
    assert "bioetl_provider_range_operational_ok{provider=~\"$provider\"}" in expression
    assert (
        "absent(count_over_time(bioetl_provider_current_status{provider=~\"$provider\"}"
        in expression
    )
    assert (
        "absent(count_over_time(bioetl_provider_range_operational_ok{provider=~\"$provider\"}"
        in expression
    )
    assert "or vector(0)" not in expression
    assert "${__range_s}s" in expression

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("unit") == "none"
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "green", "value": None},
        {"color": "orange", "value": 1},
        {"color": "red", "value": 2},
    ]
    value_mapping = next(
        mapping
        for mapping in defaults.get("mappings", [])
        if mapping.get("type") == "value"
    )
    assert value_mapping["options"]["0"]["text"] == "OK"
    assert value_mapping["options"]["1"]["text"] == "WARN"
    special_mapping = next(
        mapping
        for mapping in defaults.get("mappings", [])
        if mapping.get("type") == "special"
    )
    assert special_mapping["options"]["match"] == "null"
    assert special_mapping["options"]["result"]["text"] == "UNKNOWN"
    assert panel.get("options", {}).get("colorMode") == "background"

    description = str(panel.get("description", "")).lower()
    assert "telemetry gap" in description
    assert "not proof that providers are healthy" in description


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
    assert expressions == [
        "max_over_time(bioetl_provider_current_status[${__range_s}s]) >= 1"
    ]

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
            if item.get("title") == "Review Raw Provider Health Enum"
        ),
        None,
    )
    assert panel is not None, "Panel 'Review Raw Provider Health Enum' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_provider_health_status" in expr for expr in expressions)
    assert any(
        "bioetl_provider_health_check_provider_universe_15m" in expr
        for expr in expressions
    )
    assert any("${__range_s}s" in expr for expr in expressions)
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
    description = str(panel.get("description", "")).lower()
    assert "raw provider health enum evidence" in description
    assert "status is unknown" in description
    assert "not the canonical first-screen verdict" in description


def test_provider_top_causes_panel_preserves_canonical_cause_only_semantics() -> None:
    """Provider top causes must not fabricate synthetic rows when canonical causes are absent."""
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
    assert all(
        "bioetl_provider_current_status >= 1" not in expr for expr in expressions
    )
    assert any("${__range_s}s" in expr for expr in expressions)
    assert all("status_without_projected_cause" not in expr for expr in expressions)
    assert all("unless on (provider)" not in expr for expr in expressions)

    combined = " ".join(
        (
            str(panel.get("description", "")),
            str(panel.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")),
        )
    )
    combined_lower = combined.lower()
    assert "canonical provider cause" in combined_lower
    assert "explainability gap" in combined_lower


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
        "Track: Silver Validation Failures in Range",
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

    gold_description = str(
        panels["Track: Clean Records in Range (Gold)"].get("description", "")
    ).lower()
    assert "selected-range gold output count" in gold_description
    assert "does not prove the current dq verdict" in gold_description


def test_dq_blocked_record_evidence_panels_use_neutral_thresholds() -> None:
    """Blocked-record evidence panels must not reapply entity YAML ratio thresholds in Grafana."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Track: DQ Blocked Records in Range (Evidence)",
        "Track: DQ Threshold Events in Range Trend",
    }

    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == expected_panels, (
        "DQ dashboard must expose blocked-record evidence and threshold-event trend panels"
    )

    for panel_title, panel in panels.items():
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        steps = defaults.get("thresholds", {}).get("steps", [])
        assert all(step.get("value") not in {0.05, 0.2} for step in steps), (
            f"Panel '{panel_title}' must not hardcode entity soft/hard fail thresholds"
        )
        if panel_title.startswith("Track: DQ Blocked Records"):
            assert defaults.get("unit") == "short", (
                f"Panel '{panel_title}' must use absolute record counts"
            )
        expressions = [
            target.get("expr", "")
            for target in panel.get("targets", [])
            if isinstance(target.get("expr"), str)
        ]
        if panel_title.startswith("Track: DQ Blocked Records"):
            assert any(
                "bioetl_dq_records_quarantined_total" in expr for expr in expressions
            ), f"Panel '{panel_title}' must include quarantined records"
            assert "/ clamp_min(" not in "".join(expressions), (
                f"Panel '{panel_title}' must not compute blocked-share ratios in PromQL"
            )
        if panel_title.startswith("Track: DQ Threshold Events"):
            assert any(
                "bioetl_dq_soft_threshold_exceeded" in expr for expr in expressions
            ), f"Panel '{panel_title}' must use domain threshold counters"


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
            "Historical Failures": ("increase(", "max_over_time("),
            "Recent Terminal Runs": ("increase(", "max_over_time("),
        },
        "bioetl-dq-v2.json": {
            "Track Range Evidence: Bronze -> Silver -> Gold": (
                "increase(",
                "max_over_time(",
                "last_over_time(",
            ),
            "Track: Source Records in Range (Bronze)": (
                "increase(",
                "max_over_time(",
                "last_over_time(",
            ),
            "Track: Clean Records in Range (Gold)": (
                "increase(",
                "max_over_time(",
                "last_over_time(",
            ),
        },
        "bioetl-runtime.json": {
            "Inspect Errors by Stage / Error Code / Range": (
                "increase(",
                "max_over_time(",
            ),
            "Track Records by Stage / Run Type / Range": (
                "increase(",
                "max_over_time(",
            ),
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


@pytest.mark.parametrize("dashboard_name", _PROCESSED_RECORDS_DASHBOARDS)
def test_processed_records_parameter_rows_sort_and_display_cleanly(
    dashboard_name: str,
) -> None:
    """Processed Records rows must sort numerically without leaking sort prefixes."""
    dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title")
    }
    processed = panels["Processed Records"]
    targets = processed.get("targets", [])
    assert processed.get("datasource") == "Quarantine Explorer"
    assert len(targets) == 1
    assert targets[0] == {
        "format": "table",
        "parser": "backend",
        "refId": "A",
        "root_selector": "rows",
        "source": "url",
        "type": "json",
        "url": (
            "/ops/observability/processed-records?"
            "pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}"
        ),
        "url_options": {"data": "", "method": "GET"},
        "expr": "",
    }

    processed_json = json.dumps(processed, sort_keys=True)
    assert 'run_id="' not in processed_json
    assert "run_id=~" not in processed_json
    assert "$__range" not in processed_json
    assert "or vector(0)" not in processed_json
    assert "__zero" not in processed_json
    for removed_label in _PROCESSED_RECORDS_REMOVED_PARAMETER_LABELS:
        assert removed_label not in processed_json

    for stale_label in (
        "0 reconciliation_status",
        "1 bronze_records",
        "2 silver_valid_records",
        "3 silver_quarantined_records",
        "4 silver_skipped_records",
        "5 silver_filtered_out_records",
        "6 silver_deduplicated_records",
        "7 silver_accounted_records",
        "8 silver_delta_vs_bronze",
        "9 gold_written_records",
        "14 gold_accounted_records",
        "15 gold_delta_vs_valid_silver",
    ):
        assert f'"{stale_label}"' not in processed_json

    sort_by = processed.get("options", {}).get("sortBy", [])
    assert sort_by == [{"desc": False, "displayName": "parameter"}]
    assert processed.get("options", {}).get("cellHeight") == "sm"

    transformations = processed.get("transformations", [])
    assert [transformation.get("id") for transformation in transformations] == [
        "organize",
    ]
    organize_options = transformations[0].get("options", {})
    assert organize_options.get("renameByName", {}).get("parameter") == "parameter"
    assert organize_options.get("renameByName", {}).get("value") == "value"
    assert organize_options.get("renameByName", {}).get("percintage") == "percintage"
    assert organize_options.get("renameByName", {}).get("row_status") == ""
    assert organize_options.get("indexByName", {}).get("parameter") == 0
    assert organize_options.get("indexByName", {}).get("value") == 1
    assert organize_options.get("indexByName", {}).get("percintage") == 2
    assert organize_options.get("indexByName", {}).get("row_status") == 3
    assert not organize_options.get("excludeByName", {}).get("row_status", False)

    parameter_overrides = [
        override
        for override in processed.get("fieldConfig", {}).get("overrides", [])
        if override.get("matcher", {}).get("options") == "parameter"
    ]
    assert len(parameter_overrides) == 1
    mappings = parameter_overrides[0].get("properties", [])[0].get("value", [])[0]
    mapping_options = mappings.get("options", {})

    assert tuple(mapping_options) == _PROCESSED_RECORDS_MAPPING_LABELS
    for label, display_label in zip(
        _PROCESSED_RECORDS_PARAMETER_LABELS,
        _PROCESSED_RECORDS_DISPLAY_LABELS,
        strict=True,
    ):
        assert mapping_options[label]["text"] == display_label
        if label in _PROCESSED_RECORDS_PRIMARY_COLORS:
            assert (
                mapping_options[label]["color"]
                == (_PROCESSED_RECORDS_PRIMARY_COLORS[label])
            )
        else:
            assert "color" not in mapping_options[label]

    for label, color in _PROCESSED_RECORDS_PRIMARY_COLORS.items():
        assert mapping_options[label]["color"] == color
    for label in _PROCESSED_RECORDS_SECONDARY_LABELS:
        assert "color" not in mapping_options[label]

    parameter_properties = {
        prop.get("id"): prop.get("value")
        for prop in parameter_overrides[0].get("properties", [])
    }
    assert parameter_properties["custom.align"] == "left"
    assert parameter_properties["custom.cellOptions"] == {"type": "color-text"}

    value_overrides = [
        override
        for override in processed.get("fieldConfig", {}).get("overrides", [])
        if override.get("matcher", {}).get("options") == "value"
    ]
    assert len(value_overrides) == 1
    value_properties = {
        prop.get("id"): prop.get("value")
        for prop in value_overrides[0].get("properties", [])
    }
    assert value_properties["custom.align"] == "right"
    assert value_properties["custom.width"] == 70
    assert value_properties["custom.cellOptions"] == {"type": "color-text"}
    assert value_properties["mappings"] == (
        _expected_processed_records_display_token_mappings()
    )
    assert "color" not in value_properties
    assert "thresholds" not in value_properties
    assert "decimals" not in value_properties

    percentage_overrides = [
        override
        for override in processed.get("fieldConfig", {}).get("overrides", [])
        if override.get("matcher", {}).get("options") == "percintage"
    ]
    assert len(percentage_overrides) == 1
    percentage_properties = {
        prop.get("id"): prop.get("value")
        for prop in percentage_overrides[0].get("properties", [])
    }
    assert percentage_properties["custom.align"] == "left"
    assert percentage_properties["custom.cellOptions"] == {"type": "color-text"}
    assert percentage_properties["mappings"] == (
        _expected_processed_records_display_token_mappings()
    )
    assert "color" not in percentage_properties
    assert "thresholds" not in percentage_properties

    row_status_overrides = [
        override
        for override in processed.get("fieldConfig", {}).get("overrides", [])
        if override.get("matcher", {}).get("options") == "row_status"
    ]
    assert len(row_status_overrides) == 1
    row_status_properties = {
        prop.get("id"): prop.get("value")
        for prop in row_status_overrides[0].get("properties", [])
    }
    assert row_status_properties["displayName"] == ""
    assert row_status_properties["custom.width"] == 1
    assert row_status_properties["custom.align"] == "center"
    assert row_status_properties["custom.cellOptions"] == {
        "type": "color-background",
        "applyToRow": True,
    }
    assert row_status_properties["mappings"] == (
        _expected_processed_records_row_status_mappings()
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
    expected_duplicate_uses = _expected_duplicate_uses()
    assert duplicate_uses_by_expr == expected_duplicate_uses, (
        "Dashboard exact PromQL duplication drifted outside the audited allowlist: "
        f"{duplicate_uses_by_expr}"
    )
    _assert_dq_duplicate_reuse_semantics()
    _assert_lineage_control_plane_ownership_handoff()
