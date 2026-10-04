"""Generate same-UID static notices for the unvalidated Ops HTTP profile."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]


def build_notice(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Copy identity only; never inherit query or datasource-bearing objects."""
    return {
        "id": None,
        "uid": dashboard["uid"],
        "title": dashboard["title"],
        "tags": ["bioetl", "prometheus-only", "ops-http-unavailable"],
        "schemaVersion": dashboard["schemaVersion"],
        "version": 1,
        "editable": False,
        "timezone": "browser",
        "refresh": "",
        "time": {"from": "now-12h", "to": "now"},
        "annotations": {"list": []},
        "templating": {"list": []},
        "links": [],
        "panels": [
            {
                "id": 1,
                "title": "Ops HTTP not provisioned",
                "type": "text",
                "gridPos": {"x": 0, "y": 0, "w": 24, "h": 8},
                "options": {
                    "mode": "markdown",
                    "content": (
                        "## Ops HTTP not provisioned\n\n"
                        "This static dashboard is the fail-closed prometheus_only profile. "
                        "No retention, replay, identity, or run verdict can be inferred.\n\n"
                        "Verify managed runtime identity, Ops HTTP readiness and the Infinity "
                        "dependency before selecting dashboard_profile=full. "
                        "This notice performs no queries and does not report a healthy state."
                    ),
                },
            }
        ],
    }


def render_notices(root: Path = ROOT, *, check: bool = False) -> bool:
    """Delegate persistence to the canonical dashboard generator."""
    from scripts.ops.observability.grafana.render_nav_bus import (
        render_notices as render,
    )

    return render(root, check=check)
