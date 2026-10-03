"""Generate same-UID static notices for the unvalidated Ops HTTP profile."""

from __future__ import annotations

import json
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
    """Write or verify the six notices without modifying the full profile."""
    sources = sorted((root / "grafana/dashboards").glob("*.json"))
    if len(sources) != 5:
        raise ValueError("Expected exactly five full dashboard sources")
    destination = root / "grafana/dashboards-prometheus-only"
    ok = True
    for source in sources:
        notice = build_notice(json.loads(source.read_text(encoding="utf-8")))
        serialized = json.dumps(notice, indent=2, ensure_ascii=False) + "\n"
        target = destination / source.name
        if check:
            if not target.exists() or target.read_text(encoding="utf-8") != serialized:
                print(f"drift prometheus_only/{source.name}")
                ok = False
        else:
            from scripts.ops.observability.grafana.render_nav_bus import (
                write_dashboard_source,
            )

            write_dashboard_source(target, serialized, root=root)
    return ok
