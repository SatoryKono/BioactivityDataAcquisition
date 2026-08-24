"""Shared Grafana Provenance readability contract (#7226-#7233)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.integration._grafana_test_support import panel_base_title

ROOT = Path(__file__).resolve().parents[2]
DASHBOARDS = ROOT / "grafana" / "dashboards"

pytestmark = pytest.mark.integration

_SPECS = {
    "bioetl-control-plane-v1.json": (
        9400,
        "Inspect Scope & Evidence",
        (
            "Can this run be replayed safely?",
            "SELECTED RUN",
            "not this run",
            "incomplete evidence — not OK",
        ),
    ),
    "bioetl-overview-v2.json": (
        99,
        "Inspect Scope & Evidence",
        (
            "What is broken or degraded right now?",
            "Status + First Action",
            "TIME RANGE",
        ),
    ),
    "bioetl-runtime.json": (
        9400,
        "Understand Pipeline Scope",
        (
            "Is the pipeline progressing, and what is blocking delivery?",
            "health/phase/blockers",
            "SCRAPING",
        ),
    ),
    "bioetl-provider-health-v2.json": (
        9400,
        "Understand Evidence Scope",
        (
            "Which provider is degraded, and why?",
            "SELECTED PROVIDER",
            "inspect scrape target",
        ),
    ),
    "bioetl-dq-v2.json": (
        9400,
        "Understand Evidence Scope",
        (
            "Is data conformant, and what impact needs action?",
            "Status/reasons",
            "scopes are not peers",
        ),
    ),
    "bioetl-incident-v1.json": (
        9400,
        "Understand Incident Scope",
        (
            "What is the highest-confidence active suspect?",
            "EMPTY DOMAIN",
            "not a healthy-fleet verdict",
        ),
    ),
    "bioetl-run-explorer-v1.json": (
        1,
        "Understand Run Scope",
        (
            "Which exact run should be inspected?",
            "BROWSE",
            "not this time range",
            "report artifacts, not triage bodies",
        ),
    ),
}

_REQUIRED_CSS = (
    "padding:6px 10px",
    "border-left:4px solid #ff9830",
    "background:rgba(255,152,48,0.08)",
    "font-size:16px",
    "font-size:18px",
    "line-height:1.35",
    "white-space:normal",
    "overflow-wrap:anywhere",
    "max-width:96ch",
)
_REQUIRED_CSS_FIRST_WINDOW_H3 = (
    "padding:4px 10px",
    "border-left:4px solid #ff9830",
    "background:rgba(255,152,48,0.08)",
    "font-size:16px",
    "line-height:1.2",
    "white-space:normal",
    "overflow-wrap:anywhere",
    "max-width:96ch",
)
_FIRST_WINDOW_H3 = {
    "bioetl-overview-v2.json",
    "bioetl-run-explorer-v1.json",
}


@pytest.mark.parametrize(
    ("filename", "panel_id", "title", "required_copy"),
    tuple(
        (filename, panel_id, title, required_copy)
        for filename, (panel_id, title, required_copy) in _SPECS.items()
    ),
)
def test_provenance_panel_readability_contract(
    filename: str,
    panel_id: int,
    title: str,
    required_copy: tuple[str, ...],
) -> None:
    dashboard = json.loads((DASHBOARDS / filename).read_text(encoding="utf-8"))
    panel = next(item for item in dashboard["panels"] if item.get("id") == panel_id)
    content = str(panel["options"]["content"])

    assert panel_base_title(panel) == title
    min_h = 3 if filename in _FIRST_WINDOW_H3 else 4
    assert panel["gridPos"]["h"] >= min_h
    assert panel["options"]["mode"] == "html"
    css = (
        _REQUIRED_CSS_FIRST_WINDOW_H3 if filename in _FIRST_WINDOW_H3 else _REQUIRED_CSS
    )
    assert all(token in content for token in css)
    assert all(token in content for token in required_copy)
    assert "white-space:nowrap" not in content
    assert "font-size:12px" not in content

    companions = [
        item
        for item in dashboard["panels"]
        if item.get("gridPos", {}).get("y") == panel["gridPos"]["y"]
        and item.get("id") != panel_id
    ]
    for companion in companions:
        assert companion["gridPos"]["h"] >= 4
