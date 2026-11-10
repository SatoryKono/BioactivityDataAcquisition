#!/usr/bin/env python3
"""Apply DSA-02..08 residual dashboard narrative/layout repairs.

Surgical JSON edits only. Does not invent metrics or change UIDs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"
RUN_CONTEXT_THIN_TITLE = "Run context (thin) -> Run Explorer hub"
THIN_SHELL_EXACT_RUN_HUB = "Thin shell only. Canonical exact-run hub: Run Explorer."


def load(name: str) -> dict[str, Any]:
    return json.loads((DASH / name).read_text(encoding="utf-8"))


def save(name: str, data: dict[str, Any]) -> None:
    (DASH / name).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def walk(panels: list[dict[str, Any]] | None):
    for panel in panels or []:
        yield panel
        if panel.get("type") == "row":
            yield from walk(panel.get("panels") or [])


def by_id(data: dict[str, Any], pid: int) -> dict[str, Any] | None:
    for panel in walk(data.get("panels") or []):
        if panel.get("id") == pid:
            return panel
    return None


def set_desc(panel: dict[str, Any] | None, text: str) -> None:
    if panel is not None:
        panel["description"] = text


def set_title(panel: dict[str, Any] | None, text: str) -> None:
    if panel is not None:
        panel["title"] = text


def set_text_content(panel: dict[str, Any] | None, content: str) -> None:
    if panel is None:
        return
    opts = panel.setdefault("options", {})
    opts["content"] = content
    opts.setdefault("mode", "markdown")


def _partition_run_explorer_children(
    children: list[dict[str, Any]],
    re: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]]]:
    recent: dict[str, Any] | None = None
    next_actions: dict[str, Any] | None = None
    rest: list[dict[str, Any]] = []
    for child in children:
        cid = child.get("id")
        if cid == 3010:
            recent = child
        elif cid == 3001:
            next_actions = child
        else:
            rest.append(child)
    if recent is None:
        recent = by_id(re, 3010)
    if next_actions is None:
        next_actions = by_id(re, 3001)
    return recent, next_actions, rest


def _layout_run_explorer_scope(re: dict[str, Any]) -> None:
    set_text_content(
        by_id(re, 1),
        "**Run Explorer — empty vs selected narrative**\n\n"
        "| Mode | First screen |\n"
        "| --- | --- |\n"
        "| **No `run_id`** | Use **Recent pipeline runs** to pick a run; "
        "ID/Processed stay empty until selection |\n"
        "| **Selected `run_id`** | Read **ID** -> **Processed Records** -> expand "
        "**Selected run detail** (funnel/reasons/artifacts) |\n\n"
        "`run_id` is Ops HTTP identity only — never a Prometheus label. "
        "Long IDs: copy from table fields.\n",
    )
    set_desc(
        by_id(re, 1),
        "DSA-08: empty = browse recent runs; selected = identity -> accounting -> detail.",
    )


def _layout_run_explorer_hubs(
    *,
    recent: dict[str, Any] | None,
    re: dict[str, Any],
) -> None:
    if recent is not None:
        recent["gridPos"] = {"h": 7, "w": 24, "x": 0, "y": 6}
        set_title(recent, "Browse · Recent pipeline runs (no selection)")
        set_desc(
            recent,
            "No-selection utility. Pick a run to set run_id. Ops HTTP index — not Prometheus.",
        )
    id_p = by_id(re, 9402)
    pr_p = by_id(re, 9403)
    if id_p is not None:
        id_p["gridPos"] = {"h": 6, "w": 12, "x": 0, "y": 13}
        set_desc(
            id_p,
            "Exact-run identity hub (Ops HTTP). Canonical portfolio hub for ID panels.",
        )
    if pr_p is not None:
        pr_p["gridPos"] = {"h": 6, "w": 12, "x": 12, "y": 13}
        set_desc(
            pr_p,
            "Bronze/Silver/Gold accounting hub (Ops HTTP). "
            "Canonical portfolio hub for Processed Records.",
        )


def _layout_run_explorer_detail_row(
    row: dict[str, Any] | None,
    rest: list[dict[str, Any]],
) -> None:
    if row is None:
        return
    row["title"] = "Selected run detail (Ops HTTP; expand after selection)"
    row["collapsed"] = True
    row["gridPos"] = {"h": 1, "w": 24, "x": 0, "y": 19}
    y = 0
    for child in rest:
        gp = child.setdefault("gridPos", {"h": 5, "w": 24, "x": 0, "y": 0})
        gp["y"] = y
        gp["x"] = 0
        gp["w"] = 24
        y += int(gp.get("h") or 5)
    row["panels"] = rest


def _layout_run_explorer_next_actions(
    next_actions: dict[str, Any] | None,
) -> None:
    if next_actions is None:
        return
    next_actions["gridPos"] = {"h": 4, "w": 24, "x": 0, "y": 20}
    set_text_content(
        next_actions,
        "**Next actions (<=4)**\n"
        "1. No selection -> pick from **Recent pipeline runs**.\n"
        "2. Selected -> verify **ID** + **Processed Records** accounting invariant.\n"
        "3. Expand **Selected run detail** for funnel/reasons/artifacts.\n"
        "4. Resume/replay safety -> Trust **Review First Recovery Action** (not this board).\n",
    )
    set_desc(
        next_actions,
        "DSA-08 decision rail for empty/selected modes.",
    )


def _append_panels_by_ids(
    ordered: list[dict[str, Any]],
    by_pid: dict[Any, dict[str, Any]],
    pids: tuple[int, ...],
) -> None:
    for pid in pids:
        panel = by_pid.get(pid)
        if panel is not None:
            ordered.append(panel)


def _order_run_explorer_panels(
    *,
    panels: list[dict[str, Any]],
    recent: dict[str, Any] | None,
    row: dict[str, Any] | None,
    next_actions: dict[str, Any] | None,
    rest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_pid = {p.get("id"): p for p in panels}
    ordered: list[dict[str, Any]] = []
    _append_panels_by_ids(ordered, by_pid, (1000, 1))
    if recent is not None:
        ordered.append(recent)
    _append_panels_by_ids(ordered, by_pid, (9402, 9403))
    if row is not None:
        ordered.append(row)
    if next_actions is not None:
        ordered.append(next_actions)

    seen = {p.get("id") for p in ordered}
    nested_ids = {c.get("id") for c in rest}
    for panel in panels:
        pid = panel.get("id")
        if pid in seen or pid in {3010, 3001, 3099}:
            continue
        if panel.get("type") != "row" and pid in nested_ids:
            continue
        ordered.append(panel)
    return ordered


def _print_run_explorer_summary(re: dict[str, Any]) -> None:
    count = len(list(walk(re.get("panels") or [])))
    print(f"run explorer ok panel_count={count}")
    for panel in re["panels"]:
        collapsed = ""
        if panel.get("type") == "row":
            collapsed = "collapsed=" + str(panel.get("collapsed"))
        print(
            " ",
            panel.get("id"),
            panel.get("type"),
            panel.get("title"),
            panel.get("gridPos"),
            collapsed,
        )
        if panel.get("type") == "row":
            for child in panel.get("panels") or []:
                print("    child", child.get("id"), child.get("title"))


def apply_overview() -> None:
    ov = load("bioetl-overview-v2.json")
    set_desc(
        by_id(ov, 214),
        "Composite fleet verdict (state x confidence x basis). "
        "state from bioetl_l0_status (0=OK,1=WARN,>=2=CRIT,null=UNKNOWN). "
        "confidence is low when series absent (UNKNOWN/TELEMETRY_ABSENT) — not silent green. "
        "basis: pair with Inputs matrix and First Action; do not treat domain tables as peer badges. "
        "next_action: First Action ranked route. Empty Inputs with Status=OK is VALID_EMPTY fleet.",
    )
    set_desc(
        by_id(ov, 215),
        "Ranked next-best-action (<=4). Prefer domain handoff with scope preserved. "
        "Not a multi-paragraph runbook. Open Incident when multi-domain; domain board for localization.",
    )
    row = by_id(ov, 9012)
    if row is not None:
        row["title"] = "Diagnostics & Docs (Logs / Traces / Raw Metrics)"
        set_desc(
            row,
            "Domain status matrix detail (Control Plane / Runtime / DQ / Provider / "
            "Validation / Workflow) plus diagnostics nav. Collapsed by default — first "
            "screen uses Status + Inputs + First Action only (DSA-02).",
        )
    set_desc(
        by_id(ov, 9015),
        "Range silver rejects evidence — NOT a peer fleet health KPI. "
        "Handoff: Data Quality accounting + Run Explorer for exact-run counts.",
    )
    rc = by_id(ov, 9602)
    if rc is not None:
        rc["title"] = RUN_CONTEXT_THIN_TITLE
        set_desc(
            rc,
            "DSA-04: exact-run ID/Processed Records live on Run Explorer. "
            "This shell is collapsed forensic handoff only.",
        )
    for pid in (9300, 9301):
        set_desc(
            by_id(ov, pid),
            "Thin shell only. Canonical hub: bioetl-run-explorer-v1. "
            "Do not treat as first-screen fleet KPI.",
        )
    set_desc(
        by_id(ov, 99),
        "Scope + identity anchors only. Full prose runbooks stay off first paint. "
        "Verdict grammar: state x confidence x basis x next_action (see verdict-ontology.md).",
    )
    save("bioetl-overview-v2.json", ov)
    print("overview ok")


def apply_runtime() -> None:
    rt = load("bioetl-runtime.json")
    me = by_id(rt, 9102)
    set_title(me, "Metrics Evidence")
    set_desc(
        me,
        "Telemetry confidence chip (Metrics Evidence). Detect missing/stale scrape "
        "or rule-group evidence. Non-zero forces Status=INCOMPLETE. "
        "SCRAPING/gap is NOT peer pipeline health. Pair with Status + Runtime Blockers.",
    )
    set_desc(
        by_id(rt, 9101),
        "Current runtime blockers. Healthy state is compact VALID_EMPTY when Status=OK. "
        "Non-empty list = localization evidence. Data-path accounting -> DQ / Run Explorer "
        "handoff, not this panel.",
    )
    set_text_content(
        by_id(rt, 9991),
        "**Pipeline Flow — next actions (<=4)**\n"
        "1. Read **Status** + **Metrics Evidence** (telemetry confidence; "
        "gap => fix scrape/rules first).\n"
        "2. Open top **Runtime Blockers** row for owning stage/reason.\n"
        "3. Data-path Bronze/Silver mismatch -> **Data Quality** / **Run Explorer** "
        "(not peer runtime KPI).\n"
        "4. Multi-domain or unclear -> **Incident Workspace** with scope preserved.\n",
    )
    set_desc(
        by_id(rt, 9991),
        "DSA-05: state -> confidence -> blockers -> handoff. No giant peer KPI wall.",
    )
    sec = by_id(rt, 9992)
    if sec is not None:
        sec["title"] = "Secondary KPIs (collapsed; not peer first-screen cards)"
    rc = by_id(rt, 9993)
    if rc is not None:
        rc["title"] = RUN_CONTEXT_THIN_TITLE
    for pid in (9402, 9403):
        set_desc(
            by_id(rt, pid),
            THIN_SHELL_EXACT_RUN_HUB,
        )
    set_desc(
        by_id(rt, 9401),
        "Runtime verdict (state x confidence x basis x next_action). "
        "Trusted status from bioetl_runtime_current_status_trusted. "
        "INCOMPLETE when telemetry gap; UNKNOWN when series missing. "
        "next_action: First Action rail / Runtime Blockers.",
    )
    save("bioetl-runtime.json", rt)
    print("runtime ok")


def apply_provider() -> None:
    ph = load("bioetl-provider-health-v2.json")
    if by_id(ph, 9401) is None or by_id(ph, 9101) is None:
        print("provider fleet panels removed; skip CURRENT copy")
        return
    set_desc(
        by_id(ph, 9401),
        "Fleet dependency verdict = state x freshness/confidence. "
        "UNKNOWN + missing freshness = telemetry blind spot (not VALID_EMPTY healthy). "
        "Pair with Severity Matrix (sort critical->degraded->unknown->healthy) and Top Causes. "
        "Selected provider may disagree with fleet — label fleet vs selected.",
    )
    set_text_content(
        by_id(ph, 9002),
        "**Dependency Health — next actions (<=4)**\n"
        "1. Read **Status** with **Telemetry Freshness** "
        "(blind spot vs confirmed degradation).\n"
        "2. Open worst row in **Severity Matrix** / **Critical Providers**.\n"
        "3. Confirm **Top Causes** (VALID_EMPTY only if Status=OK and freshness healthy).\n"
        "4. Affected run identity -> **Run Explorer**; multi-domain -> **Incident**.\n",
    )
    set_desc(
        by_id(ph, 9002),
        "DSA-06: freshness-aware fleet triage. Optional latency stays in "
        "Selected Provider Detail (collapsed).",
    )
    set_desc(
        by_id(ph, 9101),
        "GLOBAL provider severity matrix. Interpret with freshness: "
        "critical -> degraded -> unknown/stale -> healthy. "
        "No data + UNKNOWN Status = blind spot, not empty healthy fleet.",
    )
    set_desc(
        by_id(ph, 9103),
        "Top causes with empty-state taxonomy: VALID_EMPTY only when Status=OK and "
        "freshness healthy; otherwise treat empty as missing signal.",
    )
    set_desc(
        by_id(ph, 9104),
        "Fleet telemetry freshness/confidence. Stale/missing reduces verdict confidence.",
    )
    sel = by_id(ph, 91)
    if sel is not None:
        sel["title"] = "Selected Provider Detail"
        set_desc(
            sel,
            "Conditional selected-provider latency/retry trends. Collapsed until needed; "
            "not first-screen when selector empty (DSA-06).",
        )
    rc = by_id(ph, 9405)
    if rc is not None:
        rc["title"] = RUN_CONTEXT_THIN_TITLE
    for pid in (9402, 9403):
        set_desc(
            by_id(ph, pid),
            THIN_SHELL_EXACT_RUN_HUB,
        )
    save("bioetl-provider-health-v2.json", ph)
    print("provider ok")


OBSERVABILITY_PANEL_IDS = (9102, 907, 894, 9491)
OBSERVABILITY_LEGEND = """Observability states — source and next action

Incident severity and evidence quality are separate. A telemetry CRIT describes visibility.

| State | Source / meaning | Next action |
| --- | --- | --- |
| OK | Observed health inputs satisfy healthy criteria | Confirm coverage, then monitor |
| WARN | Observed warning threshold | Inspect domain and threshold |
| CRIT / FIRING | Critical threshold / firing alert rule; cause unproven | Triage domain evidence; verify cause |
| UNKNOWN | Absent verdict, source unavailable or query failed | Inspect query, selectors and source |
| NO OBSERVATIONS | No events with producer, scope and event-family witnesses verified | Confirm scope/window; check witnesses |
| TELEMETRY MISSING | Required series, scrape or rule evidence absent | Restore emission, scraping or rules |
| Not verified | UNVERIFIED cause or missing observation/publication timestamps | Verify cause and freshness in domain evidence |
| Blank / No data | Empty frame or missing field; no verdict | Inspect query and scope; never assume zero |

Real zero requires an observed sample. VALID EMPTY requires documented witnesses.
PRESENT means coverage, not success; DEGRADED is a monitoring warning.
Not provided means missing attribute; PENDING means an alert awaiting its firing duration.
CURRENT / GLOBAL evidence does not attest a selected historical Run ID.
Contract: docs/03-guides/dashboards/contracts/observability-states.md (LA-13; shared with LA-04 / LA-05).
"""


def _ensure_observability_row(
    root: list[dict[str, Any]],
    fleet: dict[str, Any],
) -> dict[str, Any]:
    """Insert a disclosure header while preserving existing panel geometry."""
    row = next((p for p in root if p.get("id") == 8809), None)
    if row is not None:
        return row
    row_y = fleet["gridPos"]["y"]
    for panel in root:
        if panel.get("gridPos", {}).get("y", -1) >= row_y:
            for descendant in walk([panel]):
                descendant["gridPos"]["y"] += 1
    row = {
        "id": 8809,
        "type": "row",
        "panels": [],
        "gridPos": {"x": 0, "y": row_y, "w": 24, "h": 1},
    }
    root.insert(root.index(fleet), row)
    return row


def _detach_observability_panels(
    root: list[dict[str, Any]],
    row: dict[str, Any],
) -> list[dict[str, Any]]:
    """Remove migrated copies from their old parents, retaining the new row."""
    for panel in walk(root):
        if panel.get("type") == "row" and panel is not row:
            panel["panels"] = [
                p
                for p in panel.get("panels", [])
                if p.get("id") not in OBSERVABILITY_PANEL_IDS
            ]
    return [p for p in root if p.get("id") not in OBSERVABILITY_PANEL_IDS]


def _build_observability_row_children(
    row: dict[str, Any], signals: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Legend plus relocated signal panels stacked under the Observability row."""
    children = [
        panel
        for panel in row.get("panels", [])
        if panel.get("id") not in {*OBSERVABILITY_PANEL_IDS, 8810}
    ]
    legend = {
        "id": 8810,
        "type": "text",
        "title": "Review Observability States",
        "gridPos": {"x": 0, "y": row["gridPos"]["y"] + 1, "w": 12, "h": 2},
        "description": OBSERVABILITY_LEGEND,
        "options": {
            "mode": "html",
            "content": (
                '<div style="font-size:16px;line-height:1.2">'
                "OK · WARN · CRIT / FIRING · UNKNOWN · NO OBSERVATIONS · "
                "TELEMETRY MISSING · Not verified · Blank / No data — never assume zero. "
                "Sources and actions: panel info.</div>"
            ),
        },
    }
    top = legend["gridPos"]["y"]
    geometry = {
        894: {"x": 12, "y": top, "w": 8, "h": 2},
        9102: {"x": 0, "y": top + 2, "w": 8, "h": 3},
        907: {"x": 8, "y": top + 2, "w": 7, "h": 3},
        9491: {"x": 15, "y": top + 2, "w": 8, "h": 3},
    }
    for panel_id in OBSERVABILITY_PANEL_IDS:
        panel = signals.get(panel_id)
        if panel is None:
            continue
        panel["gridPos"] = geometry[panel_id]
        if panel_id == 894:
            content = panel.get("options", {}).get("content", "")
            if "Coverage is not success" not in content:
                panel["description"] = content
            panel["options"] = {
                "mode": "html",
                "content": '<div style="font-size:16px;line-height:1.2">Coverage is not success. Limits: panel info.</div>',
            }
        children.append(panel)
    return [legend, *children]


def apply_observability_states(data: dict[str, Any]) -> None:
    """Separate visibility evidence without changing queries or dropping panels."""
    root = data.get("panels") or []
    fleet = next((p for p in root if p.get("id") == 8808), None)
    if fleet is None:
        return
    signals = {p["id"]: p for p in walk(root) if p.get("id") in OBSERVABILITY_PANEL_IDS}
    row = _ensure_observability_row(root, fleet)
    # Keep the existing row during check-mode reads; never strip its children
    # before comparing the generated dashboard with its on-disk source.
    data["panels"] = _detach_observability_panels(root, row)
    root = data["panels"]
    root.remove(row)
    root.insert(root.index(fleet), row)
    row.update(
        title="Observability Signals",
        collapsed=True,
        description=(
            "Visibility evidence, separate from product incidents. Expand for the state legend, "
            "coverage and telemetry limits. Missing evidence is never a measured zero."
        ),
    )
    row["panels"] = _build_observability_row_children(row, signals)


def apply_incident() -> None:
    inc = load("bioetl-incident-v1.json")
    set_desc(
        by_id(inc, 9401),
        "Incident header status (labelled only). Map 0=OK,1=WARN,2=CRIT,3/null=UNKNOWN. "
        "Never bare numbers. Confidence from missing telemetry / VALID_EMPTY suspects. "
        "Read-only workspace.",
    )
    set_text_content(
        by_id(inc, 2001),
        "**Incident Console — next best actions (<=4, read-only)**\n"
        "1. Read labelled **Status** (never bare numbers).\n"
        "2. Open top row in **Ranked Active Suspects** (domain handoff).\n"
        "3. Confirm **Evidence timeline**: Current Alerts + Alert State History "
        "(same chain).\n"
        "4. Exact identity -> **Run Explorer**; resume -> Trust **Review First Recovery Action**.\n"
        "No persistent incident write-path in this workspace.\n",
    )
    set_desc(by_id(inc, 2001), "DSA-07 decision rail. Read-only.")
    set_desc(
        by_id(inc, 2010),
        "Single ranked suspect matrix across Runtime/Provider/DQ. Domain label "
        "identifies source; row links preserve scope. VALID_EMPTY when no active "
        "suspects. Primary evidence before domain forensics.",
    )
    set_title(by_id(inc, 2005), "Evidence timeline · Current Alerts (now)")
    set_desc(
        by_id(inc, 2005),
        "Instant ALERTS snapshot (firing/pending). Pair with Alert State History as "
        "one temporal chain. VALID_EMPTY when none.",
    )
    set_title(by_id(inc, 2006), "Evidence timeline · Alert State History (range)")
    set_desc(
        by_id(inc, 2006),
        "Range ALERTS history — not a persistent incident log. Same chain as "
        "Current Alerts (now).",
    )
    set_text_content(
        by_id(inc, 2007),
        "**Impact / confidence (structured, read-only)**\n\n"
        "| Field | How to read |\n"
        "| --- | --- |\n"
        "| **Impact bounds** | Affected pipelines/providers from Ranked Active "
        "Suspects + Current Alerts scope |\n"
        "| **Confidence** | high if Status mapped + suspects non-empty; low if "
        "Status=UNKNOWN or telemetry missing |\n"
        "| **Basis** | Suspect domain label + alertname; not AI diagnosis |\n"
        "| **Next action** | Domain board handoff or Run Explorer for exact-run "
        "proof |\n"
        "| **Write-path** | None — external incident tools only |\n",
    )
    set_desc(
        by_id(inc, 2007),
        "DSA-07 structured impact/confidence card (prose template). No owner/ack store.",
    )
    dom = by_id(inc, 2099)
    if dom is not None:
        dom["title"] = "Domain suspect detail (forensics; collapsed)"
    apply_observability_states(inc)
    save("bioetl-incident-v1.json", inc)
    print("incident ok")


def apply_run_explorer() -> None:
    re = load("bioetl-run-explorer-v1.json")
    panels = list(re.get("panels") or [])
    row = by_id(re, 3099)
    children = list(row.get("panels") or []) if row is not None else []
    recent, next_actions, rest = _partition_run_explorer_children(children, re)
    _layout_run_explorer_scope(re)
    _layout_run_explorer_hubs(recent=recent, re=re)
    _layout_run_explorer_detail_row(row, rest)
    _layout_run_explorer_next_actions(next_actions)
    re["panels"] = _order_run_explorer_panels(
        panels=panels,
        recent=recent,
        row=row,
        next_actions=next_actions,
        rest=rest,
    )
    re["description"] = (
        "Run Explorer 2.0 narrative. Exact completed run via Ops HTTP "
        "pipeline_run_report_v1. run_id never a Prometheus label. First screen: "
        "browse recent runs + identity/accounting hub; selected-run forensics "
        "collapsed until expanded."
    )
    save("bioetl-run-explorer-v1.json", re)
    _print_run_explorer_summary(re)


def apply_trust_dq() -> None:
    cp = load("bioetl-control-plane-v1.json")
    set_desc(
        by_id(cp, 9401),
        "Replay/resume verdict (state x confidence x basis x next_action). "
        "INCOMPLETE when required evidence missing (telemetry/checkpoint). "
        "next_action: Review First Recovery Action rail. Color is secondary to labels.",
    )
    rc = by_id(cp, 9412)
    if rc is not None:
        rc["title"] = RUN_CONTEXT_THIN_TITLE
    for pid in (9402, 9403):
        set_desc(
            by_id(cp, pid),
            f"{THIN_SHELL_EXACT_RUN_HUB} "
            "Trust keeps collapsed copy for resume forensics.",
        )
    save("bioetl-control-plane-v1.json", cp)

    dq = load("bioetl-dq-v2.json")
    set_desc(
        by_id(dq, 9401),
        "Data trust NOW verdict (state x confidence x basis x next_action). "
        "Now / Run / Range are not peer badges. "
        "next_action: First Action rail + Current Reasons.",
    )
    set_text_content(
        by_id(dq, 9103),
        "**Data trust — next actions (<=4)**\n"
        "1. Read **Status** + **Now · DQ Threshold/Reasons** (not range zeros).\n"
        "2. If blocked/quarantine/rejects > 0, use accounting with denominators "
        "(expand Run/Range lanes).\n"
        "3. Selected run -> **Run Explorer** hub; resume -> Trust **Review First Recovery Action**.\n"
        "4. Range cards are SLA/freshness context only — not peer severity.\n",
    )
    rc = by_id(dq, 9405)
    if rc is not None:
        rc["title"] = RUN_CONTEXT_THIN_TITLE
    for pid in (9402, 9403):
        set_desc(
            by_id(dq, pid),
            THIN_SHELL_EXACT_RUN_HUB,
        )
    save("bioetl-dq-v2.json", dq)
    print("trust+dq ok")


def main() -> None:
    apply_overview()
    apply_runtime()
    apply_provider()
    apply_incident()
    apply_run_explorer()
    apply_trust_dq()
    print("DSA residual dashboard apply complete")


if __name__ == "__main__":
    main()
