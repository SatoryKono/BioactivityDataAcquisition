"""Unit coverage for Phase 4.2/4.3 Incident reflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.observability.grafana.apply_phase4_reflow import (
    DOMAINS_HEIGHT,
    DOMAINS_PANEL_ID,
    FLEET_ROW_ID,
    apply_dq,
    apply_incident,
    incomplete_bands,
)


pytestmark = pytest.mark.unit

INCIDENT = Path("grafana/dashboards/bioetl-incident-v1.json")
DQ = Path("grafana/dashboards/bioetl-dq-v2.json")


def test_incident_fleet_bands_sum_to_24() -> None:
    data = json.loads(INCIDENT.read_text(encoding="utf-8"))
    assert incomplete_bands(data) == []
    row = next(p for p in data["panels"] if p.get("id") == FLEET_ROW_ID)
    assert "sum to 24" in (row.get("description") or "")


def test_incident_domains_height_matches_limit_field_budget() -> None:
    data = json.loads(INCIDENT.read_text(encoding="utf-8"))

    def walk(panels):
        for panel in panels or []:
            yield panel
            yield from walk(panel.get("panels"))

    domains = next(p for p in walk(data["panels"]) if p.get("id") == DOMAINS_PANEL_ID)
    assert domains["gridPos"]["h"] == DOMAINS_HEIGHT
    limits = [t for t in domains.get("transformations") or [] if t.get("id") == "limit"]
    assert limits and limits[0]["options"]["limitField"] == 6


def test_reflow_is_idempotent() -> None:
    data = json.loads(INCIDENT.read_text(encoding="utf-8"))
    first = apply_incident(data)
    second = apply_incident(data)
    assert incomplete_bands(data) == []
    assert first["domains_height_after"] == DOMAINS_HEIGHT
    assert second["fleet_bands_adjusted"] == 0


def test_dq_domains_height_matches_limit_field_budget() -> None:
    data = json.loads(DQ.read_text(encoding="utf-8"))

    def walk(panels):
        for panel in panels or []:
            yield panel
            yield from walk(panel.get("panels"))

    domains = next(p for p in walk(data["panels"]) if p.get("id") == DOMAINS_PANEL_ID)
    assert domains["gridPos"]["h"] == DOMAINS_HEIGHT
    limits = [t for t in domains.get("transformations") or [] if t.get("id") == "limit"]
    assert limits and limits[0]["options"]["limitField"] == 6
    follower = next(p for p in walk(data["panels"]) if p.get("id") == 9452)
    assert follower["gridPos"]["y"] == domains["gridPos"]["y"] + DOMAINS_HEIGHT


def test_dq_reflow_is_idempotent() -> None:
    data = json.loads(DQ.read_text(encoding="utf-8"))
    first = apply_dq(data)
    second = apply_dq(data)
    assert first["domains_height_after"] == DOMAINS_HEIGHT
    assert second["panels_shifted_up"] == 0
