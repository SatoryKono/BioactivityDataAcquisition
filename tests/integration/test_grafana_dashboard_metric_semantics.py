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
    get_row_child_panels,
    load_dashboard,
)
from tests.integration._grafana_processed_records_assertions import (
    assert_processed_records_field_overrides,
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
RULES_PATH = Path("grafana/prometheus-rules/bioetl_observability.yml")
MAX_OVER_TIME_COUNTER_POLICY_PATH = Path(
    "configs/quality/promql_max_over_time_counter_policy.yaml"
)
_MAX_OVER_TIME_METRIC_RE = re.compile(r"max_over_time\(\s*([a-zA-Z_:][a-zA-Z0-9_:]*)")
_PROCESSED_RECORDS_DASHBOARDS = (
    "bioetl-control-plane-v1.json",
    "bioetl-dq-v2.json",
    "bioetl-overview-v2.json",
    "bioetl-provider-health-v2.json",
    "bioetl-run-explorer-v1.json",
    "bioetl-runtime.json",
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
    """Historical pipe-token mappings removed (PFILL-01).

    Value/percentage cells now carry plain counts and percents; parameter
    coloring stays on the ``parameter`` column overrides.
    """
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
    dashboard = load_dashboard(_require_dashboard("bioetl-runtime.json"))
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
        "Monitor Fleet Health",
        "Review First Action",
        "Review Active Alerts",
        "Review Domain Status",
    }
    compact_evidence = {
        "Track Runtime Blockers": (9018, "bioetl_l1_runtime_blocker_status"),
        "Track Data Quality Status": (9019, "bioetl_l1_dq_status"),
        "Track Gold Lifecycle": (9020, "bioetl_l1_gold_lifecycle_status"),
        "Review Failed Runs": (9010, "bioetl_pipeline_runs_total"),
        "Review Recent Terminal Runs": (9011, "bioetl_pipeline_runs_total"),
    }
    disclosure_by_panel = {
        "Track Runtime Blockers": "Domain Status Tracks",
        "Track Data Quality Status": "Domain Status Tracks",
        "Track Gold Lifecycle": "Domain Status Tracks",
        "Review Failed Runs": "Inspect Range Evidence",
        "Review Recent Terminal Runs": "Inspect Range Evidence",
    }

    for dashboard_path in (Path("grafana/dashboards/bioetl-overview-v2.json"),):
        dashboard = load_dashboard(dashboard_path)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        max_first_answer_y = max(
            panels[title].get("gridPos", {}).get("y", 0)
            for title in first_answer_titles
        )
        disclosure_rows = {
            title: next(
                panel
                for panel in dashboard.get("panels", [])
                if panel.get("title") == title
            )
            for title in set(disclosure_by_panel.values())
        }
        disclosure_children = {
            title: {
                panel.get("title"): panel
                for panel in get_row_child_panels(dashboard, title)
                if panel.get("title")
            }
            for title in disclosure_rows
        }
        for row in disclosure_rows.values():
            assert row.get("type") == "row"
            assert row.get("collapsed") is (
                row.get("title") in {"Domain Status Tracks", "Inspect Range Evidence"}
            )
            assert row.get("gridPos", {}).get("y", 0) > max_first_answer_y
        for panel_title, row_title in disclosure_by_panel.items():
            assert panel_title in disclosure_children[row_title]

        for panel_title, (panel_id, expected_metric) in compact_evidence.items():
            row_title = disclosure_by_panel[panel_title]
            row = disclosure_rows[row_title]
            panel = disclosure_children[row_title][panel_title]
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            description = str(panel.get("description", "")).lower()
            data_links = panel.get("options", {}).get("dataLinks", [])

            assert panel.get("id") == panel_id, dashboard_path
            assert panel.get("gridPos", {}).get("y", 0) > row.get("gridPos", {}).get(
                "y", 0
            )
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
            assert "selected range" in description
            assert (
                "does not determine l0 status or first action" in description
                or "does not determine current fleet health" in description
                or "is not proof that current fleet health is ok" in description
                or "absence is not proof that current fleet health is ok" in description
                or "not proof that current fleet health is ok" in description
            )
            assert data_links
            assert all(
                str(link.get("title", "")).startswith("Open ") for link in data_links
            )

        for panel_title in ("Monitor Fleet Health", "Review First Action"):
            assert "$__range" not in "\n".join(
                get_panel_expressions(panels[panel_title])
            )


@pytest.mark.parametrize(
    "dashboard_name",
    [
        "bioetl-runtime.json",
        "bioetl-provider-health-v2.json",
        "bioetl-dq-v2.json",
    ],
)
def test_operator_context_shell_panels_preserve_canonical_semantics(
    dashboard_name: str,
) -> None:
    """Shared context shell panels must preserve Overview-derived semantics."""
    dashboard = load_dashboard(_require_dashboard(dashboard_name))
    panels = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    assert {9400, 9401, 9402, 9403} <= panels.keys()

    provenance = panels[9400]
    provenance_description = str(provenance.get("description", "")).lower()
    provenance_content = str(provenance.get("options", {}).get("content", "")).lower()
    # Check for scope/evidence in description or content
    assert (
        "scope" in provenance_description
        or "evidence" in provenance_description
        or "scope" in provenance_content
        or "evidence" in provenance_content
    )
    if dashboard_name in {
        "bioetl-control-plane-v1.json",
        "bioetl-runtime.json",
    }:
        assert "pipeline" in provenance_description
        assert (
            "run type" in provenance_description or "run_type" in provenance_description
        )
        assert "run id" in provenance_description or "run_id" in provenance_description
    if dashboard_name == "bioetl-workflow-overview.json":
        assert "run id only fills the local id card" in provenance_content
        assert "selected range workflow scope" in provenance_content
        assert "exact run: id card only" in provenance_content
        assert "never exact-run proof" in provenance_content
    assert "context shell:" not in provenance_content
    assert "workflow=" not in provenance_content
    assert "pipeline=" not in provenance_content
    assert "run id=" not in provenance_content
    assert "run_id is http identity context" not in provenance_content

    status = panels[9401]
    status_expressions = get_panel_expressions({"panels": [status]})
    status_description = str(status.get("description", "")).lower()
    assert status_expressions
    assert all("run_id" not in expr for expr in status_expressions)
    assert all("payload_hash" not in expr for expr in status_expressions)
    if dashboard_name == "bioetl-workflow-overview.json":
        assert any("$__range" in expr for expr in status_expressions)
        assert "selected range workflow evidence status" in status_description
        assert "not current live run state" in status_description
        assert "not exact-run evidence" in status_description
        assert "run_id remains local id-only identity context" in status_description
    elif dashboard_name == "bioetl-provider-health-v2.json":
        assert any(
            "bioetl_provider_current_status" in expr for expr in status_expressions
        )
        # Provider headline is current-status based (no selected range glue).
        assert all("$__range" not in expr for expr in status_expressions)
        assert status_description, (
            "Provider Monitor Current DQ Status must document operator semantics"
        )
        assert not any("), max_over_time" in expr for expr in status_expressions)
    elif dashboard_name == "bioetl-control-plane-v1.json":
        assert all("$__range" not in expr for expr in status_expressions)
        assert any(
            "bioetl_control_plane_current_status_trusted" in expr
            for expr in status_expressions
        )
        assert "replay/resume" in status_description
        assert "3=incomplete" in status_description.replace(" ", "")
    else:
        assert all("$__range" not in expr for expr in status_expressions)
        assert "current" in status_description
    assert "0=ok" in status_description
    assert "null=unknown" in status_description

    identity = panels[9402]
    identity_description = str(identity.get("description", "")).lower()
    assert identity.get("datasource") == "BioETL Ops HTTP"
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

    processed = panels[9403]
    processed_expressions = get_panel_expressions({"panels": [processed]})
    processed_description = str(processed.get("description", "")).lower()
    assert processed.get("datasource") == "BioETL Ops HTTP"
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
    assert "accounting" in processed_description or (
        "counts" in processed_description and "outcomes" in processed_description
    )
    if dashboard_name == "bioetl-runtime.json":
        assert "unresolved scope" in processed_description
        assert "backend failure" in processed_description
        assert any(
            next_action in processed_description
            for next_action in ("/health/live", "run explorer")
        )
    else:
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
        panels["Review Identity Anchors"],
        panels["Review Identity Gaps"],
        panels["Compare Checkpoint Anchors"],
        panels["Copy Identity Values"],
        panels["Review Required Replay Anchors"],
        panels["Review Additional Forensic Anchors"],
    ]

    for panel in identity_panels:
        assert panel.get("datasource") == "BioETL Ops HTTP"
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
        if panel.get("title") == "Review Identity Anchors"
    )
    description = str(panel.get("description", "")).lower()
    assert "short values are shown" in description
    assert "full values remain available" in description
    transformation_payload = json.dumps(panel.get("transformations", []))
    assert "value_short" in transformation_payload
    assert "value_full" in transformation_payload
    assert "source_type" in transformation_payload
    assert "drilldown_target" in transformation_payload


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
        "Inspect Control Plane Alert Conditions": (
            "bioetl_runtime_pipeline_run_type_universe",
            'run_type=~"$run_type"',
        ),
        "Inspect Provider Alert Conditions": (
            "bioetl_provider_current_status",
            'provider=~"$provider_hint"',
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
        "bioetl-runtime.json": {
            "Track Phase Duration",
            "Track Pipeline Duration",
        },
        "bioetl-provider-health-v2.json": {
            "Track Health-Check Latency p95",
            "Inspect Health-Check Latency p95",
            "Track Request Latency p95",
            "Track Rate-Limiter Wait p95",
        },
        "bioetl-dq-v2.json": {"Track DQ Check Duration p95"},
        "bioetl-control-plane-v1.json": {
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
            "Track Replay Drift by Type",
            "No data means no replay drift events were observed in range or replay drift telemetry is absent",
            "No replay drift samples",
        ),
        (
            "bioetl-control-plane-v1.json",
            "Track Global Checkpoint Admin Latency",
            "Expected Empty classification: No data is valid when no checkpoint "
            "operator/admin duration samples were emitted",
            "No GLOBAL checkpoint operator latency samples in range. This is optional "
            "admin/operator telemetry, not pipeline success evidence.",
        ),
        (
            "bioetl-control-plane-v1.json",
            "Review Missing Lineage by Layer",
            "Use as lineage risk triage only; it does not prove complete artifact "
            "identity graph or exact artifact refs.",
            "No missing-lineage reference samples in range. Empty means no sampled "
            "lineage-missing events or absent telemetry, not proof of full lineage "
            "closure.",
        ),
        (
            "bioetl-control-plane-v1.json",
            "Track Global Audit Write Latency",
            "No data means no latency samples, not zero latency.",
            "No GLOBAL audit write latency samples in range. Empty means no audit "
            "writes were timed or audit telemetry is absent, not zero latency.",
        ),
        (
            "bioetl-control-plane-v1.json",
            "Track Global Audit Query Latency",
            "No data means no latency samples, not zero latency.",
            "No GLOBAL audit query latency samples in range. Empty means no audit "
            "queries were timed or audit telemetry is absent, not zero latency.",
        ),
        (
            "bioetl-dq-v2.json",
            "Track DQ Check Duration p95",
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
    assert description
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == expected_no_value


def test_count_like_summary_panels_use_rounding_or_boolean_conditions() -> None:
    """Count-like summary panels should avoid fractional event semantics."""
    expected_panel_snippets = {
        "bioetl-provider-health-v2.json": {
            "Monitor Healthy Checks": "round(",
            "Monitor Degraded Checks": "round(",
            "Monitor Health Checks": "round(",
        },
        "bioetl-dq-v2.json": {
            "Monitor Quarantined Records": "round(",
            "Monitor Silver Filter Rejects": "round(",
            "Monitor Silver Validation Failures": "round(",
        },
        "bioetl-runtime.json": {
            "Monitor Pipeline Alert Conditions": "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m",
            "Inspect DQ Alert Conditions": "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
            "Inspect Control Plane Alert Conditions": "bioetl_runtime_alert_condition_manifest_write_failed_15m",
            "Inspect Provider Alert Conditions": "bioetl_runtime_alert_condition_provider_failure_rate_high_15m",
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


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        ("bioetl-dq-v2.json", "Monitor Volume-Weighted DQ Score"),
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
    assert all("last_over_time(" in expr and "[7d]" in expr for expr in expressions), (
        f"Panel '{panel_title}' in {dashboard_file} must retain the last real DQ "
        "sample between representative runs"
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
            if item.get("title") == "Monitor Worst-Entity DQ Score"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor Worst-Entity DQ Score' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_dq_validation_score" in expr for expr in expressions)
    assert all("last_over_time(" in expr and "[7d]" in expr for expr in expressions)
    assert all("or vector(0)" not in expr for expr in expressions), (
        "Monitor Worst-Entity DQ Score must preserve no-data rather than rendering score 0"
    )
    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("noValue") == "UNKNOWN", (
        "Monitor Worst-Entity DQ Score must render missing score samples as UNKNOWN"
    )


def test_dq_current_status_panels_preserve_unknown_no_data_state() -> None:
    """Current DQ status panels must not convert missing telemetry to OK."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Monitor Current DQ Status",
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
        "Monitor Current DQ Status",
        "Monitor DQ Threshold State",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == expected_panels

    expected_mappings = {
        "Monitor Current DQ Status": {
            "0": {"text": "OK", "color": "green"},
            "1": {"text": "WARN", "color": "orange"},
            "2": {"text": "CRIT", "color": "red"},
            "3": {"text": "UNKNOWN", "color": "gray"},
        },
        "Monitor DQ Threshold State": {
            "0": {"text": "OK", "color": "green"},
            "1": {"text": "WARN", "color": "orange"},
            "2": {"text": "CRIT", "color": "red"},
        },
    }
    for panel_title, panel in panels.items():
        mappings = panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
        value_mapping = next(
            (mapping for mapping in mappings if mapping.get("type") == "value"),
            None,
        )
        assert value_mapping is not None, (
            f"{panel_title} must define explicit operator status mappings"
        )
        assert value_mapping.get("options") == expected_mappings[panel_title], (
            f"{panel_title} status vocabulary drifted"
        )


def test_dq_current_status_panels_use_canonical_severity_threshold_steps() -> None:
    """Current DQ status panels must use standard L0 severity threshold steps."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Monitor Current DQ Status",
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
        "Monitor Current DQ Status",
        "Monitor DQ Threshold State",
        "Inspect Current DQ Reasons",
    }
    # Silver Reject Explorer handoffs were removed; keep actionability on the
    # status/threshold cards while the reasons table remains diagnostic-only.
    panels_requiring_links = {
        "Monitor Current DQ Status",
        "Monitor DQ Threshold State",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == expected_panels

    for panel_title in panels_requiring_links:
        panel = panels[panel_title]
        data_links = panel.get("options", {}).get("dataLinks", [])
        assert data_links, f"{panel_title} must expose at least one actionable dataLink"
        assert all(link.get("title") for link in data_links), (
            f"{panel_title} dataLinks must have human-readable titles"
        )
        assert all(link.get("url") for link in data_links), (
            f"{panel_title} dataLinks must target a dashboard or runbook URL"
        )

    reasons_links = (
        panels["Inspect Current DQ Reasons"].get("options", {}).get("dataLinks", [])
    )
    assert not any(
        "Silver Reject Explorer" in str(link.get("title", "")) for link in reasons_links
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
    assert any("bioetl_dq_current_status" in expr for expr in expressions), (
        "Threshold state must preserve explicit OK via bioetl_dq_current_status fallback"
    )
    assert all("sum(bioetl_dq_current_reason" not in expr for expr in expressions), (
        "Threshold state must not sum current reasons into an unbounded severity value"
    )


def test_dq_current_status_and_reasons_share_one_instant_snapshot() -> None:
    """WARN/CRIT cannot be reduced from history while reasons use current data."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panels = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("id") in {9401, 9101, 9102}
    }
    assert set(panels) == {9401, 9101, 9102}
    for panel_id, panel in panels.items():
        targets = panel.get("targets", [])
        assert targets and all(target.get("instant") is True for target in targets), (
            f"DQ current panel {panel_id} must use an instant query"
        )

    reasons = panels[9102]
    expression = str(reasons["targets"][0]["expr"])
    compact_expression = expression.replace(" ", "")
    for marker in (
        "reason_evidence_unavailable",
        "verify_dq_reason_rules",
        '"severity","warn"',
        '"severity","crit"',
        "unlesson(pipeline)",
    ):
        assert marker in compact_expression
    no_value = str(reasons["fieldConfig"]["defaults"]["noValue"]).lower()
    assert "valid only when current dq status is ok" in no_value


def test_runtime_diagnostic_panels_preserve_unknown_no_data_state() -> None:
    """Runtime diagnostic gauges must not convert missing telemetry to OK."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    expected_panels = {
        "Monitor Pipeline Status",
        "Monitor Metrics Coverage",
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
    """Runtime telemetry gap must include Prometheus rule health and actual metrics presence
    (Pushgateway-compatible)."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Metrics Coverage"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor Metrics Coverage' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert expressions == ["max(bioetl_runtime_trust_gap_status_10m)"]

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
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Track Failure Rate"
        ),
        None,
    )
    assert panel is not None, "Panel 'Track Failure Rate' not found"

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("unit") == "percentunit"
    assert defaults.get("min") == 0
    assert defaults.get("max") == 1
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "gray", "value": None},
        {"color": "orange", "value": 0.05},
        {"color": "red", "value": 0.2},
    ]
    assert panel.get("type") == "stat"
    assert "selected range" in str(panel.get("description", "")).lower()


def test_provider_severity_matrix_preserves_unknown_and_critical_mapping() -> None:
    """Provider first-screen severity matrix must fail closed and color CRIT correctly."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Fleet Severity"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor Fleet Severity' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_provider_current_status" in expr for expr in expressions)
    assert all("or vector(0)" not in expr for expr in expressions), (
        "Provider severity matrix must preserve UNKNOWN/NO DATA instead of synthetic OK"
    )

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    # Null/missing stays gray (not healthy green); explicit 0 remains OK/green.
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "gray", "value": None},
        {"color": "green", "value": 0},
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


def test_provider_telemetry_freshness_fails_closed_when_status_is_missing() -> None:
    """Provider first screen must expose telemetry freshness separately from health."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Telemetry Freshness"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor Telemetry Freshness' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert len(expressions) == 1
    expression = expressions[0]
    # Current first-screen freshness is a presence gate on projected current status.
    assert "bioetl_provider_current_status" in expression
    assert 'provider=~"$provider"' in expression
    assert "or vector(0)" not in expression
    assert "> bool 0" not in expression

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
    assert value_mapping["options"]["0"]["text"] == "PRESENT"
    assert value_mapping["options"]["1"]["text"] == "WARN"
    assert "Alias mapping: PRESENT=OK" in str(panel.get("description", ""))
    special_mapping = next(
        mapping
        for mapping in defaults.get("mappings", [])
        if mapping.get("type") == "special"
    )
    assert special_mapping["options"]["match"] == "null"
    assert special_mapping["options"]["result"]["text"] == "UNKNOWN"
    assert panel.get("options", {}).get("colorMode") == "background"

    description = str(panel.get("description", "")).lower()
    assert "telemetry" in description
    assert "unknown" in description or "fail-closed" in description


def test_provider_critical_table_keeps_severity_only_scope() -> None:
    """Critical providers table must only show active degraded/failing rows."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Non-OK Providers"
        ),
        None,
    )
    assert panel is not None, "Panel 'Inspect Non-OK Providers' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert expressions == ["max by (provider) (bioetl_provider_current_status) >= 1"]

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    # Null/missing stays gray (not healthy green); explicit 0 remains OK/green.
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "gray", "value": None},
        {"color": "green", "value": 0},
        {"color": "orange", "value": 1},
        {"color": "red", "value": 2},
    ]

    description = str(panel.get("description", ""))
    assert "DEGRADED or FAILING" in description
    assert "provider-status" in description.lower() or "current" in description.lower()


def test_provider_health_status_panel_fails_closed_to_unknown() -> None:
    """Raw provider status panel must preserve UNKNOWN for known providers with no sample."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Inspect Raw Health Status"
        ),
        None,
    )
    assert panel is not None, "Panel 'Inspect Raw Health Status' not found"

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
            if item.get("title") == "Inspect Top Provider Causes"
        ),
        None,
    )
    assert panel is not None, "Panel 'Inspect Top Provider Causes' not found"

    expressions = [target.get("expr", "") for target in panel.get("targets", [])]
    assert any("bioetl_provider_current_cause" in expr for expr in expressions)
    assert all(
        "bioetl_provider_current_status >= 1" not in expr for expr in expressions
    )
    assert all("status_without_projected_cause" not in expr for expr in expressions)
    assert all("unless on (provider)" not in expr for expr in expressions)

    combined = " ".join(
        (
            str(panel.get("description", "")),
            str(panel.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")),
        )
    )
    combined_lower = combined.lower()
    assert "top current causes" in combined_lower
    assert "degradation" in combined_lower


def test_provider_diagnostic_panels_preserve_no_data_for_tokens_and_circuit_breakers() -> (
    None
):
    """Token/circuit-breaker diagnostics must not synthesize healthy or fake adapter rows."""
    dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-provider-health-v2.json")
    )
    expectations = {
        "Monitor Available Rate-Limit Tokens": (
            "bioetl_rate_limiter_tokens_available",
            "or vector(0)",
        ),
        "Monitor Circuit-Breaker State": (
            "bioetl_circuit_breaker_state",
            "or vector(0)",
        ),
        "Track Circuit-Breaker Trips": (
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
        "Track Rate-Limiter Wait p95": "optional telemetry can stay empty",
        "Monitor Available Rate-Limit Tokens": "optional telemetry can stay empty",
        "Monitor Circuit-Breaker State": "adapter-scoped telemetry can stay empty",
        "Track Circuit-Breaker Trips": "does not refute current provider severity",
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
            if item.get("title") == "Monitor Degraded Checks"
        ),
        None,
    )
    assert panel is not None, "Panel 'Monitor Degraded Checks' not found"

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "green", "value": None}
    ]


def test_dq_selected_range_evidence_panels_use_neutral_thresholds() -> None:
    """Selected-range DQ evidence cards must not reuse live severity thresholds."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Monitor Bronze Records",
        "Monitor Gold Records",
        "Monitor Quarantined Records",
        "Monitor Silver Validation Failures",
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
        panels["Monitor Gold Records"].get("description", "")
    ).lower()
    assert "selected" in gold_description or "range" in gold_description
    assert "gold" in gold_description


def test_dq_blocked_record_evidence_panels_use_neutral_thresholds() -> None:
    """Blocked-record evidence panels must not reapply entity YAML ratio thresholds in Grafana."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Monitor Blocked Records",
        "Track DQ Threshold Events",
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
    """Freshness age must expose the DQ 24h/72h policy directly in hours."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    panel = next(
        (
            item
            for item in get_dashboard_panels(dashboard)
            if item.get("title") == "Monitor Worst Freshness Age"
        ),
        None,
    )
    assert panel is not None, "Freshness lag panel not found in bioetl-dq-v2.json"

    defaults = panel.get("fieldConfig", {}).get("defaults", {})
    assert defaults.get("unit") == "h"
    assert defaults.get("thresholds", {}).get("steps") == [
        {"color": "green", "value": None},
        {"color": "orange", "value": 24},
        {"color": "red", "value": 72},
    ]
    expressions = get_panel_expressions({"panels": [panel]})
    assert expressions and all("/ 3600" in expr for expr in expressions)


def test_dq_problem_panels_expose_actionable_datalinks() -> None:
    """Key DQ incident panels must offer direct operator handoff."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    expected_panels = {
        "Monitor Worst-Entity DQ Score",
        "Monitor Worst Freshness Age",
        "Monitor Silver Filter Rejects",
    }
    # Silver Reject Explorer handoffs were removed; reject accounting stays on-panel.
    panels_requiring_links = {
        "Monitor Worst-Entity DQ Score",
        "Monitor Worst Freshness Age",
    }
    panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dashboard)
        if panel.get("title") in expected_panels
    }
    assert set(panels) == expected_panels

    for panel_title in panels_requiring_links:
        panel = panels[panel_title]
        data_links = panel.get("options", {}).get("dataLinks", [])
        assert data_links, f"{panel_title} must expose at least one actionable dataLink"
        assert all(
            str(link.get("title", "")).startswith("Open ") for link in data_links
        ), f"{panel_title} must use canonical Open ... dataLink titles"

    reject_panel = panels["Monitor Silver Filter Rejects"]
    reject_links = reject_panel.get("options", {}).get("dataLinks", [])
    assert not any(
        "Silver Reject Explorer" in str(link.get("title", "")) for link in reject_links
    )
    assert not reject_panel.get("links"), (
        "Monitor Silver Filter Rejects should not use legacy panel links"
    )


def test_dashboards_do_not_use_prometheus_created_timestamps() -> None:
    """Operator dashboards must not expose Prometheus client bookkeeping timestamps."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        expressions = get_panel_expressions(dashboard)
        assert all("_created" not in expr for expr in expressions), (
            f"Dashboard {dashboard_path.name} must not use Prometheus *_created series"
        )


def test_selected_range_kpis_follow_declared_counter_window_intent() -> None:
    """Selected-range KPI panels must match their declared counter-window intent."""
    panel_expectations = {
        "bioetl-overview-v2.json": {
            "Review Failed Runs": {
                "intent": "event_delta",
                "required": ("increase(",),
                "forbidden": ("max_over_time(", "last_over_time("),
            },
            "Review Recent Terminal Runs": {
                "intent": "event_delta",
                "required": ("increase(",),
                "forbidden": ("max_over_time(", "last_over_time("),
            },
        },
        "bioetl-dq-v2.json": {
            "Track Record Flow by Stage": {
                "intent": "pushed_snapshot_evidence",
                "required": ("max_over_time(",),
                "forbidden": ("last_over_time(",),
            },
            "Monitor Bronze Records": {
                "intent": "pushed_snapshot_evidence",
                "required": ("max_over_time(",),
                "forbidden": ("last_over_time(",),
            },
            "Monitor Gold Records": {
                "intent": "pushed_snapshot_evidence",
                "required": ("max_over_time(",),
                "forbidden": ("last_over_time(",),
            },
        },
        "bioetl-runtime.json": {
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
    """Every Counter used with max_over_time must match the reviewed policy."""
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
        for rule in group.get("rules", []):
            expression = str(rule.get("expr", ""))
            matched = set(_MAX_OVER_TIME_METRIC_RE.findall(expression))
            matched &= counter_metrics
            if matched:
                rule_name = rule.get("record") or rule.get("alert")
                source = f"{group.get('name')}:{rule_name}"
                reviewed.append((source, matched, expression))

    unexpected = {
        metric
        for _source, matched, _expression in reviewed
        for metric in matched - allowed_metrics
    }
    assert not unexpected
    assert len(reviewed) == policy["reviewed_expression_count"]
    assert policy["event_delta_function"] == "increase"
    assert policy["exact_multi_run_total_source"] == "RunLedger"

    for source, matched, expression in reviewed:
        if "bioetl_silver_filter_rejections_total" in matched:
            assert "> bool 0" in expression or "> 0" in expression, source


@pytest.mark.parametrize("dashboard_name", _PROCESSED_RECORDS_DASHBOARDS)
def test_processed_records_parameter_rows_sort_and_display_cleanly(
    dashboard_name: str,
) -> None:
    """Processed Records rows must sort numerically without leaking sort prefixes."""
    dashboard = load_dashboard(_require_dashboard(dashboard_name))
    panels = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    identity_id, processed_id = (
        (9300, 9301) if dashboard_name == "bioetl-overview-v2.json" else (9402, 9403)
    )
    identity = panels[identity_id]
    processed = panels[processed_id]
    assert (
        identity.get("gridPos", {}).get("h")
        == processed.get("gridPos", {}).get("h")
        == 6
    )
    if dashboard_name == "bioetl-run-explorer-v1.json":
        assert identity.get("gridPos", {}).get("w") == 10
        assert processed.get("gridPos", {}).get("w") == 14
        assert (
            "valid empty"
            in str(
                identity.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")
            ).lower()
        )
        assert (
            "query error"
            in str(
                processed.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")
            ).lower()
        )
    assert (
        identity.get("options", {}).get("cellHeight")
        == processed.get("options", {}).get("cellHeight")
        == "sm"
    )
    default_identity_cell_options = (
        identity.get("fieldConfig", {})
        .get("defaults", {})
        .get("custom", {})
        .get("cellOptions", {})
    )
    assert default_identity_cell_options.get("wrapText") is not True
    identity_cell_options = [
        property_.get("value", {})
        for override in identity.get("fieldConfig", {}).get("overrides", [])
        for property_ in override.get("properties", [])
        if property_.get("id") == "custom.cellOptions"
    ]
    assert all(
        cell_options.get("wrapText") is not True
        for cell_options in identity_cell_options
        if isinstance(cell_options, dict)
    )

    assert processed.get("datasource") == "BioETL Ops HTTP"
    _assert_processed_records_target_contract(processed)

    processed_json = json.dumps(processed, sort_keys=True)

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
    rename_by_name = organize_options.get("renameByName", {})
    assert rename_by_name.get("parameter") == "parameter"
    # API field ``value`` is the record count; operator-facing column is ``count``.
    assert rename_by_name.get("value") == "count"
    assert rename_by_name.get("percentage") == "percentage"
    assert rename_by_name.get("row_status") == ""
    assert organize_options.get("indexByName", {}).get("parameter") == 0
    assert organize_options.get("indexByName", {}).get("value") == 1
    assert organize_options.get("indexByName", {}).get("percentage") == 2
    assert organize_options.get("indexByName", {}).get("row_status") == 3
    excluded_fields = organize_options.get("excludeByName", {})
    assert excluded_fields.get("row_status") is True
    # Legacy typo field may still appear from stale backends; hide it in Grafana.
    assert excluded_fields.get("percintage") is True
    assert "percintage" not in organize_options.get("indexByName", {})
    assert "percintage" not in organize_options.get("renameByName", {})
    # All Processed Records tables show parameter + count + percentage.
    assert excluded_fields.get("percentage") is not True
    assert excluded_fields.get("parameter") is not True
    assert excluded_fields.get("value") is not True
    assert excluded_fields.get("count") is not True

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

    assert_processed_records_field_overrides(
        processed,
        expected_row_status_mappings=(
            _expected_processed_records_row_status_mappings()
        ),
    )
