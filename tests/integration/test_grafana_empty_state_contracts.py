"""Grafana empty-state rendering contracts."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)


pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("dashboard_file", "panel_title"),
    [
        (
            "bioetl-control-plane-v1.json",
            "Compare Checkpoint Outcomes",
        ),
    ],
)
def test_empty_state_distribution_panels_do_not_invent_observations(
    dashboard_file: str, panel_title: str
) -> None:
    """An absent counter must remain distinguishable from measured zero."""
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

    expressions = [
        target.get("expr", "")
        for target in panel.get("targets", [])
        if isinstance(target.get("expr"), str)
    ]
    assert expressions
    assert all("vector(0)" not in expr for expr in expressions)
    assert "TELEMETRY MISSING" in panel["fieldConfig"]["defaults"]["noValue"]


def test_unfinished_run_never_inherits_the_success_color() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-run-explorer-v1.json"))
    panel = next(p for p in dashboard["panels"] if p["id"] == 3010)
    mappings = {}
    for override in panel["fieldConfig"]["overrides"]:
        if str(override["matcher"].get("options", "")).casefold() != "processing":
            continue
        for prop in override["properties"]:
            if prop["id"] == "mappings":
                for mapping in prop["value"]:
                    if mapping["type"] == "value":
                        mappings.update(mapping["options"])
    assert mappings["unfinished"]["color"] == "gray"
    assert mappings["unfinished"]["color"] != mappings["success"]["color"]


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
