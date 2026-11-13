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
        _repair_panel(panel)
    return dashboard


def _repair_panel(panel: dict[str, Any]) -> None:
    """Apply only the migration rules relevant to this panel."""
    panel_id = panel.get("id")
    if panel_id in {3, 6, 7}:
        _mark_unsupported_storage(panel)
    if panel.get("type") == "text":
        if panel_id == 8:
            _explain_unavailable_ingestion(panel)
        elif panel_id == 11:
            _explain_scrape_interval(panel)
    if panel_id == 12:
        _repair_rule_duration(panel)
    if panel_id == 14:
        _repair_scrape_interval(panel)


def _mark_unsupported_storage(panel: dict[str, Any]) -> None:
    """Mark removed local-storage metrics as unsupported."""
    panel["description"] = (
        "Unsupported legacy local-storage metric; use Prometheus 2.0 Stats."
    )
    defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
    defaults.update(
        noValue="UNSUPPORTED · Legacy metric",
        color={"mode": "fixed", "fixedColor": "gray"},
    )


def _explain_unavailable_ingestion(panel: dict[str, Any]) -> None:
    """Explain why legacy ingestion counts are unavailable."""
    panel["options"] = {
        **panel.get("options", {}),
        "content": (
            "#### Samples Ingested\n"
            "Legacy local-storage export unavailable on the current TSDB. "
            "This panel does not show accepted sample counts and is not a "
            "diagnostic signal for ingestion health."
        ),
        "mode": "markdown",
    }


def _explain_scrape_interval(panel: dict[str, Any]) -> None:
    """Distinguish the scrape interval from execution duration."""
    panel["options"] = {
        **panel.get("options", {}),
        "content": (
            "#### Scrape Interval\n"
            "This graph shows the observed scrape interval between target "
            "scrapes. For scrape execution duration and percentiles, use "
            "``scrape_duration_seconds``; this panel does not show duration."
        ),
        "mode": "markdown",
    }


def _repair_rule_duration(panel: dict[str, Any]) -> None:
    """Migrate the removed evaluator metric without changing filters."""
    panel.setdefault("fieldConfig", {}).setdefault("defaults", {})["unit"] = "s"
    for target in panel.get("targets") or []:
        expr = str(target.get("expr") or "")
        if "prometheus_evaluator_duration_seconds" in expr:
            target["expr"] = expr.replace(
                "prometheus_evaluator_duration_seconds",
                "prometheus_rule_group_duration_seconds",
            )


def _repair_scrape_interval(panel: dict[str, Any]) -> None:
    """Retain the interval query and label its unit accurately."""
    # Preserve the actual query and its history rather than silently
    # exchanging the metric underneath an existing graph.
    panel["title"] = "Scrape Interval"
    panel["description"] = (
        "Observed time between target scrapes, not scrape execution duration. "
        "Use scrape_duration_seconds to diagnose scrape execution cost."
    )
    panel.setdefault("fieldConfig", {}).setdefault("defaults", {})["unit"] = "s"
