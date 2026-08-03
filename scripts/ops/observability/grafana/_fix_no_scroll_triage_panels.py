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
    "Open Review First Recovery Action or Run Explorer."
    "</div>"
)

# Single line for h=2 Review First Recovery Action (title + one content line).
TRUST_PRIMARY = (
    '<div style="padding:2px 8px;line-height:1.25;font-size:12px;overflow:hidden">'
    "<strong>Review First Recovery Action</strong>: "
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
        if title == "Review First Recovery Action":
            opts = dict(panel.get("options") or {})
            links = opts.get("dataLinks")
            opts["mode"] = "html"
            opts["content"] = TRUST_PRIMARY
            if links is not None:
                opts["dataLinks"] = links
            panel["options"] = opts
            print(
                "Trust Review First Recovery Action compact, h=",
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
    'white-space:normal">'
    "<strong>Which provider is degraded, and why?</strong> "
    "Provider-global scope: GLOBAL severity + telemetry freshness · "
    "Selected-provider Status can disagree by design<br>"
    "Blank Provider → <strong>Selection required</strong>. "
    "UNKNOWN freshness = missing Runtime telemetry — inspect scrape target."
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

TRUST_REPLAY_SAFETY_REVIEW = (
    '<div style="padding:4px 8px;line-height:1.3;font-size:12px;white-space:normal">'
    "<strong>Remaining replay-safety signals:</strong> duplicate-record evidence and "
    "occurrence-only vs semantic drift classification.<br>"
    "Keep high-cardinality IDs out of Prometheus. Use identity evidence, manifests, "
    "ledger/checkpoint diagnostics, and artifact lineage for exact proof."
    "</div>"
)

OVERVIEW_DIAGNOSTICS_NAVIGATION = (
    '<div style="padding:4px 8px;line-height:1.35;font-size:12px;white-space:normal">'
    "<strong>Raw metric entrypoints</strong><br>"
    "<code>bioetl_l0_status</code> — current verdict · "
    "<code>bioetl_l0_next_action_route</code> — first-action route<br>"
    "<code>bioetl_l0_input_status_selected</code> — input status. "
    "Open Trust, Pipeline Diagnostics, Data Quality, or Provider Health for reasons."
    "</div>"
)

RUNTIME_ESCALATION_REVIEW = (
    '<div style="padding:4px 8px;line-height:1.3;font-size:12px;white-space:normal">'
    "<strong>Runtime escalation:</strong> blockers → phase evidence → action.<br>"
    "Use Incident Workspace for multi-domain impact; Run Explorer for exact-run proof."
    "</div>"
)

INCIDENT_IMPACT_CONFIDENCE = (
    '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;'
    'padding:4px 8px;line-height:1.3;font-size:12px;white-space:normal">'
    "<div><strong>Impact</strong><br>Affected pipeline/provider scope from suspects "
    "and current alerts.</div>"
    "<div><strong>Confidence</strong><br>High with mapped Status + suspects; low with "
    "UNKNOWN or missing telemetry.</div>"
    "<div><strong>Basis</strong><br>Domain label + alertname; read-only evidence, "
    "not AI diagnosis.</div>"
    "</div>"
)

RUN_LAYERS_ACCOUNTING = (
    '<div style="padding:4px 8px;line-height:1.3;font-size:12px;white-space:normal">'
    "<strong>Layer accounting:</strong> use Processed Records for the compact view "
    "and <code>pipeline_run_report_v1.layers</code> for exact counts.<br>"
    "Actions: Open JSON · Open Markdown · inspect reconciliation before escalation."
    "</div>"
)

RUN_STAGE_TIMINGS_FAILURE = (
    '<div style="padding:4px 8px;line-height:1.3;font-size:12px;white-space:normal">'
    "<strong>Stage timing / failure:</strong> optional blocks appear only when the "
    "selected run report recorded them.<br>"
    "Empty means not recorded for this run, not zero duration or successful execution. "
    "Open JSON or Markdown for exact evidence."
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
            print(
                "Runtime Provenance compact, h=", (panel.get("gridPos") or {}).get("h")
            )
    for row in data.get("panels") or []:
        if row.get("type") != "row" or row.get("title") != "Escalate":
            continue
        children = row.get("panels") or []
        escalation = next(
            (panel for panel in children if panel.get("id") == 2541),
            None,
        )
        if escalation is None:
            continue
        grid = escalation.get("gridPos") or {}
        if grid.get("h") == 2:
            grid["h"] = 3
            for panel in children:
                child_grid = panel.get("gridPos") or {}
                if child_grid.get("y", -1) >= 34:
                    child_grid["y"] += 1
        _set_html_panel(escalation, RUNTIME_ESCALATION_REVIEW)
    save(path, data)


def fix_provider() -> None:
    path = DASH / "bioetl-provider-health-v2.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for panel in walk(data.get("panels")):
        if panel.get("title") == "Provenance" and panel.get("id") == 9400:
            _set_html_panel(panel, PROVIDER_PROVENANCE)
            print(
                "Provider Provenance compact, h=", (panel.get("gridPos") or {}).get("h")
            )
    save(path, data)


def fix_incident() -> None:
    path = DASH / "bioetl-incident-v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for panel in walk(data.get("panels")):
        title = panel.get("title")
        if title == "Provenance" and panel.get("id") == 9400:
            _set_html_panel(panel, INCIDENT_PROVENANCE)
            print(
                "Incident Provenance compact, h=", (panel.get("gridPos") or {}).get("h")
            )
        if title == "Next Best Actions":
            _set_html_panel(panel, INCIDENT_NEXT_BEST)
            print(
                "Incident Next Best Actions compact, h=",
                (panel.get("gridPos") or {}).get("h"),
            )
        if title == "Impact / confidence (honest bounds)" and panel.get("id") == 2007:
            _set_html_panel(panel, INCIDENT_IMPACT_CONFIDENCE)
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
            print(
                "Overview Provenance compact, h=", (panel.get("gridPos") or {}).get("h")
            )
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
                        if (
                            val.get("applyToRow")
                            or val.get("type") == "color-background"
                        ):
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
            grid = panel.get("gridPos") or {}
            if grid.get("h") == 6:
                grid["h"] = 7
                for sibling in data.get("panels") or []:
                    sibling_grid = sibling.get("gridPos") or {}
                    if sibling_grid.get("y", -1) >= 12:
                        sibling_grid["y"] += 1
                first_action = next(
                    (
                        sibling
                        for sibling in data.get("panels") or []
                        if sibling.get("id") == 215
                    ),
                    None,
                )
                if first_action is not None:
                    (first_action.get("gridPos") or {})["h"] = 7
            print(
                "Overview Inputs cellHeight=sm, applyToRow cleared, h=",
                (panel.get("gridPos") or {}).get("h"),
                "y=",
                (panel.get("gridPos") or {}).get("y"),
            )
        if title == "Diagnostics Navigation" and pid == 9021:
            _set_html_panel(panel, OVERVIEW_DIAGNOSTICS_NAVIGATION)
            (panel.get("gridPos") or {})["h"] = 5
    save(path, data)


def fix_trust_replay_review() -> None:
    path = DASH / "bioetl-control-plane-v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for panel in walk(data.get("panels")):
        if panel.get("id") == 139:
            _set_html_panel(panel, TRUST_REPLAY_SAFETY_REVIEW)
            (panel.get("gridPos") or {})["h"] = 4
            panel["description"] = (
                "No-scroll review card. The identity evidence endpoint already covers "
                "manifest/run identity, execution/config/contract/input anchors, replay "
                "parentage, copyable full values, and checkpoint anchor comparison. "
                "Checkpoint freshness lag supplies bounded age evidence. Remaining "
                "signals are replay duplicate-record evidence and occurrence-only versus "
                "semantic drift classification. Exact IDs remain in identity evidence, "
                "manifest, ledger, checkpoint, artifact, and lineage diagnostics rather "
                "than Prometheus labels."
            )
    save(path, data)


def fix_run_explorer() -> None:
    path = DASH / "bioetl-run-explorer-v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for panel in walk(data.get("panels")):
        if panel.get("id") == 3016:
            _set_html_panel(panel, RUN_LAYERS_ACCOUNTING)
        if panel.get("id") == 3014:
            _set_html_panel(panel, RUN_STAGE_TIMINGS_FAILURE)
    save(path, data)


def main() -> None:
    fix_trust()
    fix_trust_replay_review()
    fix_overview()
    fix_runtime()
    fix_provider()
    fix_incident()
    fix_run_explorer()


if __name__ == "__main__":
    main()
