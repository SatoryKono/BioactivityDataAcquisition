#!/usr/bin/env python3
"""Apply Dashboard System 2.0 Phase-2 residual JSON surgeries (DUX2-02…06)."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"


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


def ensure_color_bg_table(panel: dict, *, value_fields: list[str] | None = None) -> None:
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


def visualization_upgrades() -> None:
    # Overview Inputs
    ov = load("bioetl-overview-v2.json")
    p = by_title(ov)
    if "Inputs" in p:
        ensure_color_bg_table(p["Inputs"])
        append_desc(
            p["Inputs"],
            "Phase-2: status cells use color-background thresholds (OK/WARN/CRIT). "
            "Not peer-comparable to Range evidence elsewhere.",
        )
    if "First Action" in p:
        append_desc(
            p["First Action"],
            "CTA budget ≤4 routes. Empty/NO_ROUTE: validate pipeline/run_type universe "
            "before treating as healthy.",
        )
    save("bioetl-overview-v2.json", ov)

    # Provider matrices
    pr = load("bioetl-provider-health-v2.json")
    p = by_title(pr)
    for title in (
        "Monitor GLOBAL Provider Severity Matrix",
        "Inspect Critical Providers",
        "Inspect Provider Top Causes",
    ):
        if title in p:
            ensure_color_bg_table(p[title])
    if "First Action" in p:
        p["First Action"].setdefault("options", {})["content"] = (
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
            p["First Action"],
            "Phase-2 CTA standard. Empty causes with non-OK severity is an explainability gap.",
        )
    if "Inspect Provider Top Causes" in p:
        p["Inspect Provider Top Causes"].setdefault("fieldConfig", {}).setdefault(
            "defaults", {}
        )["noValue"] = (
            "VALID EMPTY (no active causes). Non-OK GLOBAL severity without causes = "
            "explainability gap — check scrape/rules."
        )
    save("bioetl-provider-health-v2.json", pr)

    # Runtime healthy path
    rt = load("bioetl-runtime.json")
    p = by_title(rt)
    if "Runtime Blockers" in p:
        append_desc(
            p["Runtime Blockers"],
            "When Status=OK and this table is empty → VALID EMPTY (healthy path). "
            "Do not treat empty as missing telemetry; check Runtime Telemetry Gap for scrape trust.",
        )
        p["Runtime Blockers"].setdefault("fieldConfig", {}).setdefault(
            "defaults", {}
        )["noValue"] = "VALID EMPTY — no active blockers (healthy path if Status=OK)"
        ensure_color_bg_table(p["Runtime Blockers"])
    if "First Action" in p:
        p["First Action"].setdefault("options", {})["content"] = (
            "<div style='padding:0.4rem 0.65rem;line-height:1.45'>"
            "<b>Unhealthy:</b> Status → Blockers → Metrics trust (Telemetry Gap) → "
            "Detect/Localize.<br/>"
            "<b>Healthy:</b> Status OK + empty blockers (VALID EMPTY) → secondary KPIs; "
            "do not chase empty tables.<br/>"
            "<b>Next (≤4 CTAs via panel links):</b> status · blockers · Trust · DQ."
            "</div>"
        )
    save("bioetl-runtime.json", rt)

    # DQ
    dq = load("bioetl-dq-v2.json")
    p = by_title(dq)
    if "Inspect DQ Current Reasons" in p:
        ensure_color_bg_table(p["Inspect DQ Current Reasons"])
        append_desc(
            p["Inspect DQ Current Reasons"],
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

    # Trust next action polish
    cp = load("bioetl-control-plane-v1.json")
    p = by_title(cp)
    if "Next Action: Replay Diagnostics" in p:
        p["Next Action: Replay Diagnostics"].setdefault("options", {})["content"] = (
            "<h3>Next Action (≤4) — explicable Trust verdict</h3>"
            "<ol style='margin:0.2rem 0 0 1.1rem;padding:0'>"
            "<li>Read Status (INCOMPLETE blocks resume).</li>"
            "<li>Replay Safety + Checkpoint Freshness + Manifest/Ledger + Telemetry Missing.</li>"
            "<li>If INCOMPLETE, repair missing telemetry/scrape first.</li>"
            "<li>Run Explorer for exact identity; expand drilldown rows only if needed.</li>"
            "</ol>"
        )
    for title in (
        "Monitor: Replay Safety State",
        "Monitor: Manifest / Ledger Integrity",
        "Inspect: Telemetry Missing",
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
                'topk(10, max by (pipeline, run_type, reason) (bioetl_runtime_current_blocker_reason) > 0)',
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
    if "Control-plane / DQ handoffs" in p:
        p["Control-plane / DQ handoffs"]["title"] = "Next actions (≤4)"
        p["Control-plane / DQ handoffs"]["options"] = {
            "mode": "markdown",
            "content": (
                "1. **0. Trust** — resume/replay safety for this family.\n"
                "2. **4. Data Quality** — quarantine aggregates (not record forensics).\n"
                "3. **5. Incident Workspace** — multi-domain suspects.\n"
                "4. **CLI** — `bioetl run-manifest show <run-id>` · "
                "`bioetl quarantine inspect --pipeline <pipeline>`.\n"
            ),
        }
        p["Control-plane / DQ handoffs"]["links"] = []  # avoid dup targets; nav owns hops
        append_desc(
            p["Control-plane / DQ handoffs"],
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
