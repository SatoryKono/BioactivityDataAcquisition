#!/usr/bin/env python3
"""Apply Dashboard System 2.0 Phase-2 residual JSON surgeries (DUX2-02…06)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"

# Panel title identities (python:S1192).
PANEL_FIRST_ACTION = "First Action"
PANEL_INSPECT_PROVIDER_TOP_CAUSES = "Inspect Provider Top Causes"
PANEL_RUNTIME_BLOCKERS = "Runtime Blockers"
PANEL_INSPECT_DQ_CURRENT_REASONS = "Inspect DQ Current Reasons"
PANEL_CONTROL_PLANE_DQ_HANDOFFS = "Control-plane / DQ handoffs"


def load(name: str) -> dict:
    return json.loads((DASH / name).read_text(encoding="utf-8"))


def save(name: str, payload: dict) -> None:
    (DASH / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def walk(panels: list) -> list:
    out: list = []
    for p in panels:
        out.append(p)
        nested = p.get("panels")
        if isinstance(nested, list):
            out.extend(walk(nested))
    return out


def by_title(d: dict) -> dict[str, dict]:
    return {
        str(p.get("title")): p
        for p in walk(d.get("panels", []))
        if isinstance(p.get("title"), str)
    }


def ensure_color_bg_table(
    panel: dict, *, value_fields: list[str] | None = None
) -> None:
    """Prefer color-background cells for status-like table columns."""
    fc = panel.setdefault("fieldConfig", {})
    defaults = fc.setdefault("defaults", {})
    custom = defaults.setdefault("custom", {})
    custom["cellOptions"] = {"type": "color-background", "mode": "basic"}
    defaults.setdefault(
        "thresholds",
        {
            "mode": "absolute",
            "steps": [
                {"color": "green", "value": None},
                {"color": "orange", "value": 1},
                {"color": "red", "value": 2},
            ],
        },
    )
    defaults.setdefault("color", {"mode": "thresholds"})
    if value_fields:
        overrides = fc.setdefault("overrides", [])
        existing = {
            o.get("matcher", {}).get("options")
            for o in overrides
            if isinstance(o, dict)
        }
        for field in value_fields:
            if field in existing:
                continue
            overrides.append(
                {
                    "matcher": {"id": "byName", "options": field},
                    "properties": [
                        {
                            "id": "custom.cellOptions",
                            "value": {"type": "color-background", "mode": "basic"},
                        },
                        {"id": "color", "value": {"mode": "thresholds"}},
                    ],
                }
            )


def append_desc(panel: dict, text: str) -> None:
    cur = str(panel.get("description") or "")
    if text in cur:
        return
    panel["description"] = (cur + " " + text).strip()


def link(
    title: str,
    url: str,
) -> dict:
    return {
        "title": title,
        "url": url,
        "type": "link",
        "icon": "dashboard",
        "targetBlank": False,
        "keepTime": False,
        "includeVars": False,
    }


def table_panel(
    pid: int,
    title: str,
    expr: str,
    *,
    x: int,
    y: int,
    w: int,
    h: int,
    description: str,
) -> dict:
    return {
        "id": pid,
        "type": "table",
        "title": title,
        "description": description,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [
            {
                "expr": expr,
                "format": "table",
                "instant": True,
                "refId": "A",
            }
        ],
        "fieldConfig": {
            "defaults": {
                "noValue": "VALID EMPTY — no active rows in selected scope",
                "custom": {
                    "align": "left",
                    "cellOptions": {"type": "color-background", "mode": "basic"},
                    "inspect": False,
                },
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "orange", "value": 1},
                        {"color": "red", "value": 2},
                    ],
                },
            },
            "overrides": [],
        },
        "options": {"showHeader": True, "footer": {"show": False}},
    }


def _upgrade_overview_dashboard() -> None:
    ov = load("bioetl-overview-v2.json")
    p = by_title(ov)
    if "Inputs" in p:
        ensure_color_bg_table(p["Inputs"])
        append_desc(
            p["Inputs"],
            "Phase-2: status cells use color-background thresholds (OK/WARN/CRIT). "
            "Not peer-comparable to Range evidence elsewhere.",
        )
    if PANEL_FIRST_ACTION in p:
        append_desc(
            p[PANEL_FIRST_ACTION],
            "CTA budget ≤4 routes. Empty/NO_ROUTE: validate pipeline/run_type universe "
            "before treating as healthy.",
        )
    save("bioetl-overview-v2.json", ov)


def _upgrade_provider_dashboard() -> None:
    pr = load("bioetl-provider-health-v2.json")
    p = by_title(pr)
    for title in (
        "Monitor GLOBAL Provider Severity Matrix",
        "Inspect Critical Providers",
        PANEL_INSPECT_PROVIDER_TOP_CAUSES,
    ):
        if title in p:
            ensure_color_bg_table(p[title])
    if PANEL_FIRST_ACTION in p:
        p[PANEL_FIRST_ACTION].setdefault("options", {})["content"] = (
            "<h3>First Action (≤4)</h3>"
            "<ol style='margin:0.2rem 0 0 1.1rem;padding:0'>"
            "<li>Read GLOBAL severity matrix (fleet, not selected).</li>"
            "<li>Open top causes / critical providers.</li>"
            "<li>Check telemetry freshness (TELEMETRY ABSENT ≠ OK).</li>"
            "<li>Selected-provider detail is supporting only.</li>"
            "</ol>"
            "<p><b>Empty matrix/causes:</b> VALID EMPTY if severity OK; if severity "
            "non-OK → explainability/scrape gap, not healthy.</p>"
        )
        append_desc(
            p[PANEL_FIRST_ACTION],
            "Phase-2 CTA standard. Empty causes with non-OK severity is an explainability gap.",
        )
    if PANEL_INSPECT_PROVIDER_TOP_CAUSES in p:
        p[PANEL_INSPECT_PROVIDER_TOP_CAUSES].setdefault("fieldConfig", {}).setdefault(
            "defaults", {}
        )["noValue"] = (
            "VALID EMPTY (no active causes). Non-OK GLOBAL severity without causes = "
            "explainability gap — check scrape/rules."
        )
    save("bioetl-provider-health-v2.json", pr)


def _upgrade_runtime_dashboard() -> None:
    rt = load("bioetl-runtime.json")
    p = by_title(rt)
    if PANEL_RUNTIME_BLOCKERS in p:
        append_desc(
            p[PANEL_RUNTIME_BLOCKERS],
            "When Status=OK and this table is empty → VALID EMPTY (healthy path). "
            "Do not treat empty as missing telemetry; check Runtime Telemetry Gap for scrape trust.",
        )
        p[PANEL_RUNTIME_BLOCKERS].setdefault("fieldConfig", {}).setdefault(
            "defaults", {}
        )["noValue"] = "VALID EMPTY — no active blockers (healthy path if Status=OK)"
        ensure_color_bg_table(p[PANEL_RUNTIME_BLOCKERS])
    if PANEL_FIRST_ACTION in p:
        p[PANEL_FIRST_ACTION].setdefault("options", {})["content"] = (
            "<div style='padding:0.4rem 0.65rem;line-height:1.45'>"
            "<b>Unhealthy:</b> Status → Blockers → Metrics trust (Telemetry Gap) → "
            "Detect/Localize.<br/>"
            "<b>Healthy:</b> Status OK + empty blockers (VALID EMPTY) → secondary KPIs; "
            "do not chase empty tables.<br/>"
            "<b>Next (≤4 CTAs via panel links):</b> status · blockers · Trust · DQ."
            "</div>"
        )
    save("bioetl-runtime.json", rt)


def _upgrade_dq_dashboard() -> None:
    dq = load("bioetl-dq-v2.json")
    p = by_title(dq)
    if PANEL_INSPECT_DQ_CURRENT_REASONS in p:
        ensure_color_bg_table(p[PANEL_INSPECT_DQ_CURRENT_REASONS])
        append_desc(
            p[PANEL_INSPECT_DQ_CURRENT_REASONS],
            "NOW lane only — not peer-comparable to Range freshness badges.",
        )
    if "Review: First Action" in p:
        p["Review: First Action"].setdefault("options", {})["content"] = (
            "<h3>First Action — three lanes (not peer badges)</h3>"
            "<ol style='margin:0.2rem 0 0 1.1rem;padding:0'>"
            "<li><b>Now:</b> Status + threshold + current reasons.</li>"
            "<li><b>Run:</b> expand Silver/Gold reject rows.</li>"
            "<li><b>Range:</b> freshness/attrition — never compare as peer severity to Now.</li>"
            "<li>Empty reasons with OK Status = VALID EMPTY.</li>"
            "</ol>"
        )
    if "Status" in p:
        append_desc(
            p["Status"],
            "NOW-lane current DQ status only (bioetl_dq_current_status).",
        )
    save("bioetl-dq-v2.json", dq)


def visualization_upgrades() -> None:
    _upgrade_overview_dashboard()
    _upgrade_provider_dashboard()
    _upgrade_runtime_dashboard()
    _upgrade_dq_dashboard()

    # Trust next action polish (SSOT title: Review First Recovery Action — DS2-03)
    cp = load("bioetl-control-plane-v1.json")
    p = by_title(cp)
    recovery = p.get("Review First Recovery Action") or p.get(
        "Next Action: Replay Diagnostics"
    )
    if recovery is not None:
        recovery.setdefault("options", {})["content"] = (
            "**Review First Recovery Action:** Status + four cards below. "
            "INCOMPLETE/UNKNOWN → repair evidence before resume. "
            "Exact run → Run Explorer. VALID_EMPTY blockers only when Status=OK and cards clean."
        )
        recovery["title"] = "Review First Recovery Action"
        recovery.setdefault("options", {}).setdefault(
            "dataLinks",
            [
                {
                    "title": "Open Replay Safety Diagnostics",
                    "url": (
                        "/d/bioetl-control-plane-v1/bioetl-control-plane-v1"
                        "?viewPanel=130&var-pipeline=$pipeline&var-run_type=$run_type"
                        "&${__url_time_range}&var-workflow=$workflow"
                    ),
                    "targetBlank": False,
                    "includeVars": False,
                }
            ],
        )
        recovery["options"]["mode"] = recovery["options"].get("mode") or "markdown"
    for title in (
        "Monitor Replay Safety",
        "Monitor Manifest & Ledger Failures",
        "Monitor Telemetry Coverage",
    ):
        if title in p and p[title].get("type") == "stat":
            append_desc(
                p[title],
                "Trust card: non-OK/INCOMPLETE always has basis in description mapping.",
            )
    save("bioetl-control-plane-v1.json", cp)


def incident_depth() -> None:
    d = load("bioetl-incident-v1.json")
    panels = d.get("panels", [])
    # Keep nav, provenance, status, NBA; replace single Ranked Suspects with three domain tables
    keep_ids = {1000, 9400, 9401, 2001}
    new_panels = [p for p in panels if p.get("id") in keep_ids]

    # Status (9401): keep runbook-only dataLinks. Nav bus owns Overview/Runtime handoffs
    # so panel CTAs must not duplicate those target UIDs.
    status = next(p for p in new_panels if p.get("id") == 9401)
    status_options = status.setdefault("options", {})
    status_options["dataLinks"] = [
        link
        for link in status_options.get("dataLinks") or []
        if isinstance(link, dict) and "runbooks/" in str(link.get("url", ""))
    ]
    if not status_options["dataLinks"]:
        status_options["dataLinks"] = [
            {
                "title": "Open Runtime Troubleshooting Runbook",
                "url": (
                    "https://github.com/SatoryKono/BioactivityDataAcquisition/"
                    "blob/main/docs/05-operations/runbooks/observability-checklist.md"
                ),
                "targetBlank": True,
                "includeVars": False,
            }
        ]

    # Update NBA content + links (no duplicates with nav targets for provider if nav has it —
    # use only unique non-nav CTAs: self-view panels avoided; use domain explorers already on nav
    # so NBA uses text-only steps + max 2 extra links not on nav? Nav has all boards.
    # Policy: NBA panel.links empty; rely on nav bus; avoid duplicate target UID test failures.
    nba = next(p for p in new_panels if p.get("id") == 2001)
    nba["title"] = "Next Best Actions"
    nba["options"] = {
        "mode": "html",
        "content": (
            "<h3>Next Best Actions (≤4)</h3>"
            "<ol style='margin:0.2rem 0 0 1.1rem;padding:0'>"
            "<li>Read Status strip (L0 worst-of).</li>"
            "<li>Scan domain suspect tables (Runtime / Provider / DQ) — not one mega-OR.</li>"
            "<li>Open matching workspace via Navigation bus (time range preserved).</li>"
            "<li>Empty all tables + Status OK = VALID EMPTY; empty with CRIT = TELEMETRY/projection gap.</li>"
            "</ol>"
        ),
    }
    nba["description"] = (
        "Phase-2 Incident CTAs: navigation bus owns dashboard handoffs to avoid "
        "duplicate target UIDs. Domain suspect tables below rank evidence."
    )
    nba["links"] = []
    nba["gridPos"] = {"h": 4, "w": 24, "x": 0, "y": 7}

    y = 11
    new_panels.extend(
        [
            table_panel(
                2002,
                "Suspects · Runtime blockers",
                "topk(10, max by (pipeline, run_type, reason) (bioetl_runtime_current_blocker_reason) > 0)",
                x=0,
                y=y,
                w=8,
                h=8,
                description=(
                    "Runtime current blockers only (bioetl_runtime_current_blocker_reason). "
                    "VALID EMPTY when no active blockers."
                ),
            ),
            table_panel(
                2003,
                "Suspects · Provider causes",
                "topk(10, max by (provider, cause) (bioetl_provider_current_cause) > 0)",
                x=8,
                y=y,
                w=8,
                h=8,
                description=(
                    "Provider causes (bioetl_provider_current_cause). Fleet population; "
                    "not selected-provider only. Empty + non-OK Status = explainability gap."
                ),
            ),
            table_panel(
                2004,
                "Suspects · DQ reasons",
                "topk(10, max by (pipeline, reason) (bioetl_dq_current_reason) > 0)",
                x=16,
                y=y,
                w=8,
                h=8,
                description=(
                    "DQ current reasons (bioetl_dq_current_reason). NOW-lane evidence. "
                    "VALID EMPTY when no active reasons."
                ),
            ),
            table_panel(
                2005,
                "Alert / Event Timeline (range)",
                'count by (alertname, alertstate) (ALERTS{alertstate=~"firing|pending"})',
                x=0,
                y=y + 8,
                w=24,
                h=6,
                description=(
                    "Prometheus ALERTS support surface (no business-logic rewrite). "
                    "Platform-agnostic incident timeline. VALID EMPTY when no firing/pending."
                ),
            ),
        ]
    )
    d["panels"] = new_panels
    d["description"] = (
        "Incident Workspace (Phase-2). Domain-separated suspects (Runtime / Provider / DQ) "
        "plus ALERTS timeline. Not Grafana Drilldown Investigations. Entry hop: Fleet or this board."
    )
    d["tags"] = list(
        dict.fromkeys(list(d.get("tags") or []) + ["dashboard-2.0", "phase-2"])
    )
    save("bioetl-incident-v1.json", d)


def run_explorer_depth() -> None:
    d = load("bioetl-run-explorer-v1.json")
    p = by_title(d)
    if "Run Scope" in p:
        p["Run Scope"]["options"] = {
            "mode": "markdown",
            "content": (
                "### Run Explorer — single-run narrative\n\n"
                "pipeline=`$pipeline` · run_type=`$run_type` · run_id=`$run_id` · "
                "workflow=`$workflow`\n\n"
                "`run_id` is **HTTP-only** identity context. Never add it to PromQL.\n\n"
                "**Read order:** (1) ID identity table · (2) Processed Records "
                "(Bronze/Silver/Gold) · (3) handoffs below.\n\n"
                "Empty ID with backend healthy → invalid/absent run scope (not VALID EMPTY records).\n"
            ),
        }
    if PANEL_CONTROL_PLANE_DQ_HANDOFFS in p:
        p[PANEL_CONTROL_PLANE_DQ_HANDOFFS]["title"] = "Next actions (≤4)"
        p[PANEL_CONTROL_PLANE_DQ_HANDOFFS]["options"] = {
            "mode": "markdown",
            "content": (
                "1. **0. Trust** — resume/replay safety for this family.\n"
                "2. **4. Data Quality** — quarantine aggregates (not record forensics).\n"
                "3. **5. Incident Workspace** — multi-domain suspects.\n"
                "4. **CLI** — `bioetl run-manifest show <run-id>` · "
                "`bioetl quarantine inspect --pipeline <pipeline>`.\n"
            ),
        }
        p[PANEL_CONTROL_PLANE_DQ_HANDOFFS][
            "links"
        ] = []  # avoid dup targets; nav owns hops
        append_desc(
            p[PANEL_CONTROL_PLANE_DQ_HANDOFFS],
            "Phase-2: CTA list; dashboard hops via Navigation bus to avoid duplicate UIDs.",
        )
    for title in ("ID", "Processed Records"):
        if title in p:
            append_desc(
                p[title],
                "HTTP Ops only. Generic Grafana No data is not acceptance: check "
                "/health/live and selector scope first.",
            )
    d["description"] = (
        "Run Explorer (Phase-2). Single-run identity + stage accounting via BioETL Ops HTTP. "
        "run_id is never a Prometheus label."
    )
    save("bioetl-run-explorer-v1.json", d)


def main() -> None:
    visualization_upgrades()
    incident_depth()
    run_explorer_depth()
    print("DUX2 residual JSON surgeries applied")


if __name__ == "__main__":
    main()
