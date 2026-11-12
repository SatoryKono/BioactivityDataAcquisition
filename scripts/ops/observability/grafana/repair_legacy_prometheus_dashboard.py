"""Prepare the existing optional legacy service dashboard for Prometheus 3.

This is not a sixth BioETL dashboard or an automatic provisioning step. Call
``repair_dashboard`` on a current Grafana export, then review/apply that export.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def repair_dashboard(source: dict[str, Any]) -> dict[str, Any]:
    """Retain the existing UID and distinguish unavailable legacy signals."""
    if source.get("uid") != "rpfmFFz7z":
        raise ValueError("Expected the existing Prometheus Stats service dashboard")
    dashboard = deepcopy(source)
    dashboard["title"] = "Prometheus Stats (legacy)"
    dashboard["tags"] = sorted(set(dashboard.get("tags", [])) | {"legacy"})
    dashboard["description"] = (
        "Legacy service dashboard. Prometheus 1 local-storage metrics are unsupported "
        "on the current TSDB. Use Prometheus 2.0 Stats for storage telemetry. "
        "Unavailable legacy metrics never establish healthy storage."
    )
    for panel in dashboard.get("panels", []):
        if panel.get("id") in {3, 6, 7}:
            panel["description"] = (
                "Unsupported legacy local-storage metric; use Prometheus 2.0 Stats."
            )
            defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
            defaults.update(
                noValue="UNSUPPORTED · Legacy metric",
                color={"mode": "fixed", "fixedColor": "gray"},
            )
        if panel.get("id") == 14:
            # Preserve the actual query and its history rather than silently
            # exchanging the metric underneath an existing graph.
            panel["title"] = "Scrape Interval"
            panel["description"] = (
                "Observed time between target scrapes, not scrape execution duration. "
                "Use scrape_duration_seconds to diagnose scrape execution cost."
            )
            panel.setdefault("fieldConfig", {}).setdefault("defaults", {})["unit"] = "s"
    return dashboard
