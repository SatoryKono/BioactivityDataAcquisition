#!/usr/bin/env python3
"""Remove internal scroll from Trust/Overview triage panels without layout reflow.

Keeps original gridPos (contract tests pin y/h). Fits content by compact HTML and
Inputs table cellHeight=sm (no applyToRow).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"


def walk(panels: list | None):
    for panel in panels or []:
        yield panel
        yield from walk(panel.get("panels"))


def save(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# Two-line max, 12px, tight padding — fits Grafana text panel at h=3 (with title chrome).
TRUST_PROVENANCE = (
    '<div style="padding:2px 6px;border-left:3px solid #64748b;'
    "background:rgba(100,116,139,0.10);line-height:1.2;font-size:12px;"
    'overflow:hidden;white-space:normal">'
    "<strong>Replay trust</strong> · Status → Reason → Action · "
    "<code>$workflow</code>/<code>$pipeline</code>/<code>$run_type</code>/"
    "run <code>$run_id</code><br>"
    "<strong>UNKNOWN</strong> = evidence incomplete — not OK. "
    "Open Primary recovery or Run Explorer."
    "</div>"
)

# Single line for h=2 Primary recovery (title + one content line).
TRUST_PRIMARY = (
    '<div style="padding:2px 8px;line-height:1.25;font-size:12px;overflow:hidden">'
    "<strong>Primary recovery</strong>: "
    "1) Status + Replay Safety/Checkpoint · "
    "2) UNKNOWN/INCOMPLETE → verify scrape · "
    "3) Open blockers · "
    "4) Run Explorer identity"
    "</div>"
)

# Keep Overview primary-question phrase required by tests.
OV_PROVENANCE = (
    '<div style="padding:2px 6px;border-left:3px solid #64748b;'
    "background:rgba(100,116,139,0.10);line-height:1.2;font-size:12px;"
    'overflow:hidden;white-space:normal">'
    "<strong>What is broken or degraded right now</strong>, and "
    "<strong>where should the operator drill down first</strong>? "
    "Status → First Action → Inputs · "
    "<code>$workflow</code>/<code>$pipeline</code>/<code>$run_type</code>/"
    "run <code>$run_id</code><br>"
    "UNKNOWN = evidence incomplete. Prefer First Action over raw numbers."
    "</div>"
)


def fix_trust() -> None:
    path = DASH / "bioetl-control-plane-v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for panel in walk(data.get("panels")):
        title = panel.get("title")
        pid = panel.get("id")
        if title == "Provenance" and pid == 9400:
            opts = dict(panel.get("options") or {})
            opts["mode"] = "html"
            opts["content"] = TRUST_PROVENANCE
            panel["options"] = opts
            # Do not change gridPos
            print("Trust Provenance compact, h=", (panel.get("gridPos") or {}).get("h"))
        if title == "Primary recovery":
            opts = dict(panel.get("options") or {})
            links = opts.get("dataLinks")
            opts["mode"] = "html"
            opts["content"] = TRUST_PRIMARY
            if links is not None:
                opts["dataLinks"] = links
            panel["options"] = opts
            print(
                "Trust Primary recovery compact, h=",
                (panel.get("gridPos") or {}).get("h"),
                "links",
                len(links or []),
            )
    save(path, data)


RUNTIME_PROVENANCE = (
    '<div style="padding:2px 6px;border-left:3px solid #64748b;'
    "background:rgba(100,116,139,0.10);line-height:1.2;font-size:12px;"
    'overflow:hidden;white-space:normal">'
    "<strong>Pipeline diagnostics</strong> · Status/Health → Phase → Blockers → Action · "
    "<code>$pipeline</code>/<code>$run_type</code>/stage <code>$stage</code>/"
    "run <code>$run_id</code><br>"
    "SCRAPING = execution evidence, not delivery OK. Silver/Gold zeros while scraping = "
    "<strong>Not started</strong>."
    "</div>"
)

PROVIDER_PROVENANCE = (
    '<div style="padding:2px 6px;border-left:3px solid #ff9830;'
    "background:rgba(255,152,48,0.08);line-height:1.2;font-size:12px;"
    'overflow:hidden;white-space:normal">'
    "<strong>Which provider is degraded, and why?</strong> "
    "Start with GLOBAL severity + telemetry freshness · "
    "Selected-provider Status can disagree by design<br>"
    "Blank Provider → <strong>Selection required</strong>. "
    "UNKNOWN freshness = telemetry missing — inspect scrape target."
    "</div>"
)

INCIDENT_PROVENANCE = (
    '<div style="padding:2px 6px;border-left:3px solid #64748b;'
    "background:rgba(100,116,139,0.10);line-height:1.2;font-size:12px;"
    'overflow:hidden;white-space:normal">'
    "<strong>Incident triage</strong> · Status → Impact/confidence → Next action · "
    "<code>$workflow</code>/<code>$pipeline</code>/<code>$run_type</code>/"
    "run <code>$run_id</code><br>"
    "Read labelled Status (never bare numbers). Empty domain = "
    "<strong>No active suspects</strong>, not healthy fleet."
    "</div>"
)

INCIDENT_NEXT_BEST = (
    '<div style="padding:2px 8px;line-height:1.25;font-size:12px;overflow:hidden">'
    "<strong>Next best actions (≤4, read-only)</strong> — "
    "1) Read labelled <strong>Status</strong> · "
    "2) Open top Ranked Active Suspect domain · "
    "3) Confirm Current Alerts age/severity · "
    "4) Run Explorer for exact-run proof"
    "</div>"
)


def _set_html_panel(panel: dict, content: str) -> None:
    opts = dict(panel.get("options") or {})
    links = opts.get("dataLinks")
    opts["mode"] = "html"
    opts["content"] = content
    if links is not None:
        opts["dataLinks"] = links
    panel["options"] = opts


def fix_runtime() -> None:
    path = DASH / "bioetl-runtime.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for panel in walk(data.get("panels")):
        if panel.get("title") == "Provenance" and panel.get("id") == 9400:
            _set_html_panel(panel, RUNTIME_PROVENANCE)
            print("Runtime Provenance compact, h=", (panel.get("gridPos") or {}).get("h"))
    save(path, data)


def fix_provider() -> None:
    path = DASH / "bioetl-provider-health-v2.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for panel in walk(data.get("panels")):
        if panel.get("title") == "Provenance" and panel.get("id") == 9400:
            _set_html_panel(panel, PROVIDER_PROVENANCE)
            print("Provider Provenance compact, h=", (panel.get("gridPos") or {}).get("h"))
    save(path, data)


def fix_incident() -> None:
    path = DASH / "bioetl-incident-v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for panel in walk(data.get("panels")):
        title = panel.get("title")
        if title == "Provenance" and panel.get("id") == 9400:
            _set_html_panel(panel, INCIDENT_PROVENANCE)
            print("Incident Provenance compact, h=", (panel.get("gridPos") or {}).get("h"))
        if title == "Next Best Actions":
            _set_html_panel(panel, INCIDENT_NEXT_BEST)
            print(
                "Incident Next Best Actions compact, h=",
                (panel.get("gridPos") or {}).get("h"),
            )
    save(path, data)


def fix_overview() -> None:
    path = DASH / "bioetl-overview-v2.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for panel in walk(data.get("panels")):
        title = panel.get("title")
        pid = panel.get("id")
        if title == "Provenance" and pid == 99:
            opts = dict(panel.get("options") or {})
            opts["mode"] = "html"
            opts["content"] = OV_PROVENANCE
            panel["options"] = opts
            print("Overview Provenance compact, h=", (panel.get("gridPos") or {}).get("h"))
        if title == "Inputs" and pid == 9002:
            opts = dict(panel.get("options") or {})
            opts["cellHeight"] = "sm"
            opts["showHeader"] = True
            panel["options"] = opts
            fc = dict(panel.get("fieldConfig") or {})
            defaults = dict(fc.get("defaults") or {})
            custom = dict(defaults.get("custom") or {})
            cell = dict(custom.get("cellOptions") or {})
            if cell.get("type") == "color-background":
                cell = {"type": "color-background", "mode": "basic"}
            custom["cellOptions"] = cell
            defaults["custom"] = custom
            overrides = []
            for ov in list(fc.get("overrides") or []):
                ov = dict(ov)
                props = []
                for prop in list(ov.get("properties") or []):
                    prop = dict(prop)
                    if prop.get("id") == "custom.cellOptions":
                        val = dict(prop.get("value") or {})
                        if val.get("applyToRow") or val.get("type") == "color-background":
                            prop["value"] = {
                                "type": "color-background",
                                "mode": "basic",
                            }
                    props.append(prop)
                ov["properties"] = props
                overrides.append(ov)
            fc["defaults"] = defaults
            fc["overrides"] = overrides
            panel["fieldConfig"] = fc
            print(
                "Overview Inputs cellHeight=sm, applyToRow cleared, h=",
                (panel.get("gridPos") or {}).get("h"),
                "y=",
                (panel.get("gridPos") or {}).get("y"),
            )
    save(path, data)


def main() -> None:
    fix_trust()
    fix_overview()
    fix_runtime()
    fix_provider()
    fix_incident()


if __name__ == "__main__":
    main()
