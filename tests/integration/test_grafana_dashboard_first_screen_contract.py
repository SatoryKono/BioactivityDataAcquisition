"""First-screen Grafana dashboard contracts for operator triage dashboards."""

from pathlib import Path

import pytest
import yaml

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)


pytestmark = pytest.mark.integration

_DESIGN_SYSTEM_PATH = Path("docs/03-guides/dashboards/design-system.md")
_OBSERVABILITY_RULES_PATH = Path("grafana/prometheus-rules/bioetl_observability.yml")


def test_design_system_defines_first_screen_decision_matrix() -> None:
    """#3700: design docs must define first-screen responsibility explicitly."""
    text = _DESIGN_SYSTEM_PATH.read_text(encoding="utf-8")
    required_tokens = {
        "First-screen responsibility and panel decision matrix",
        "`bioetl-runtime`",
        "`bioetl-provider-health-v2`",
        "`bioetl-dq-v2`",
        "`bioetl_runtime_current_status`",
        "`bioetl_provider_current_status`",
        "`bioetl_dq_current_status`",
        "Selected-range count/rate/trend",
        "First-screen current-status panels MUST NOT use `$__range`",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, (
        "dashboard design-system must preserve first-screen decision matrix; "
        f"missing={missing}"
    )


def test_current_status_recording_rules_are_canonicalized() -> None:
    """#3698: Runtime/Provider/DQ current status belongs in recording rules."""
    payload = yaml.safe_load(_OBSERVABILITY_RULES_PATH.read_text(encoding="utf-8"))
    records: dict[str, list[dict[str, object]]] = {}
    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            record = rule.get("record")
            if isinstance(record, str):
                records.setdefault(record, []).append(rule)

    required_records = {
        "bioetl_runtime_current_status",
        "bioetl_runtime_current_blocker_reason",
        "bioetl_provider_current_status",
        "bioetl_provider_current_cause",
        "bioetl_dq_current_status",
        "bioetl_dq_current_reason",
    }
    missing = sorted(record for record in required_records if record not in records)
    assert not missing, f"missing canonical current-status records: {missing}"

    for status_record in (
        "bioetl_runtime_current_status",
        "bioetl_provider_current_status",
        "bioetl_dq_current_status",
    ):
        expressions = [str(rule.get("expr", "")) for rule in records[status_record]]
        assert expressions
        assert all("$__range" not in expression for expression in expressions), (
            f"{status_record} must use fixed current windows/rules, not Grafana range"
        )


def test_runtime_provider_dq_first_screens_use_canonical_current_status() -> None:
    """L2 first screens must answer current state before range evidence."""
    expectations = {
        "bioetl-runtime.json": {
            "Monitor Runtime Current Status": "bioetl_runtime_current_status",
            "Inspect Top Runtime Blockers": "bioetl_runtime_current_blocker_reason",
        },
        "bioetl-provider-health-v2.json": {
            "Monitor GLOBAL Provider Severity Matrix": "bioetl_provider_current_status",
            "Inspect Provider Top Causes": "bioetl_provider_current_cause",
        },
        "bioetl-dq-v2.json": {
            "Monitor DQ Current Status": "bioetl_dq_current_status",
            "Inspect DQ Current Reasons": "bioetl_dq_current_reason",
        },
    }

    for dashboard_name, panel_expectations in expectations.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / dashboard_name)
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title, expected_metric in panel_expectations.items():
            panel = panels.get(panel_title)
            assert panel is not None, (
                f"{dashboard_name} must expose first-screen panel {panel_title!r}"
            )
            assert panel.get("gridPos", {}).get("y", 999) <= 10, (
                f"{dashboard_name}:{panel_title} must be visible before range evidence"
            )
            expressions = [
                target.get("expr", "")
                for target in panel.get("targets", [])
                if isinstance(target.get("expr"), str)
            ]
            assert any(expected_metric in expr for expr in expressions), (
                f"{dashboard_name}:{panel_title} must consume {expected_metric}"
            )
            assert all("$__range" not in expr for expr in expressions), (
                f"{dashboard_name}:{panel_title} must not use selected range for current status"
            )


def test_provider_and_dq_range_evidence_panels_are_below_first_screen() -> None:
    provider = load_dashboard(Path("grafana/dashboards/bioetl-provider-health-v2.json"))
    dq = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    range_panels = {
        "bioetl-provider-health-v2.json": (
            provider,
            [
                "Monitor Healthy Checks (Selected Range)",
                "Monitor Degraded Checks (Selected Range)",
                "Track Provider Failure Rate (Selected Range)",
                "Track Health Checks Total (Selected Range)",
                "Track Failure and Degraded Trend by Provider",
                "Track Provider Failure Share (Selected Range)",
            ],
        ),
        "bioetl-dq-v2.json": (
            dq,
            [
                "Track Range Evidence: Bronze -> Silver -> Gold",
                "Silver Filter Rejects",
            ],
        ),
    }

    for dashboard_name, (dashboard, panel_titles) in range_panels.items():
        panels = {
            panel.get("title"): panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("title")
        }
        for panel_title in panel_titles:
            panel = panels.get(panel_title)
            assert panel is not None, f"{dashboard_name} missing {panel_title!r}"
            assert panel.get("gridPos", {}).get("y", 0) >= 18, (
                f"{dashboard_name}:{panel_title} must sit below first-screen current state"
            )
            description = str(panel.get("description", "")).lower()
            assert "selected-range" in f"{panel_title.lower()} {description}", (
                f"{dashboard_name}:{panel_title} must identify selected-range semantics"
            )
