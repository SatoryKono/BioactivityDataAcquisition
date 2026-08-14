"""Apply all DS2 Wave 0 + Wave 1 dashboard and test fixes. Verify after write."""

from __future__ import annotations

import json
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"
TESTS = ROOT / "tests" / "integration"

# Dashboard / panel title identities (python:S1192).
DASHBOARD_RUNTIME = "bioetl-runtime.json"
DASHBOARD_INCIDENT_V1 = "bioetl-incident-v1.json"
DASHBOARD_CONTROL_PLANE_V1 = "bioetl-control-plane-v1.json"
PANEL_PRIMARY_RECOVERY = "Review First Recovery Action"
PANEL_NEXT_ACTION_REPLAY_DIAGNOSTICS = "Next Action: Replay Diagnostics"

# Grafana dashboards are recursively heterogeneous JSON documents.  This
# script intentionally mutates that external boundary in place, so ``Any`` is
# confined to the JSON object alias instead of leaking into product code.
type JsonObject = dict[str, Any]


def walk(panels: list[JsonObject] | None) -> Iterator[JsonObject]:
    for p in panels or []:
        yield p
        yield from walk(p.get("panels"))


def load_dash(name: str) -> JsonObject:
    path = DASH / name
    data = cast(JsonObject, json.loads(path.read_text(encoding="utf-8")))
    return data


def save_dash(name: str, data: JsonObject) -> None:
    path = DASH / name
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # verify round-trip
    check = json.loads(path.read_text(encoding="utf-8"))
    assert check.get("uid") == data.get("uid")
    print("saved+verified", path)


def fix_runtime() -> None:
    rt = load_dash(DASHBOARD_RUNTIME)
    found = False
    for p in walk(rt.get("panels")):
        if p.get("id") == 9105:
            found = True
            p["type"] = "timeseries"
            p["title"] = "Monitor Aggregate Stage Lag"
            p["description"] = (
                "Continuous stage lag seconds by stage (Prom low-cardinality). "
                "Timeseries frame for localization; not a discrete state timeline. "
                "No run_id Prom labels."
            )
            p["fieldConfig"] = {
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {
                        "axisBorderShow": False,
                        "axisCenteredZero": False,
                        "axisColorMode": "text",
                        "axisLabel": "lag (s)",
                        "drawStyle": "line",
                        "fillOpacity": 15,
                        "lineInterpolation": "linear",
                        "lineWidth": 2,
                        "pointSize": 3,
                        "showPoints": "never",
                        "spanNulls": False,
                        "stacking": {"group": "A", "mode": "none"},
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "green", "value": None},
                            {"color": "orange", "value": 60},
                            {"color": "red", "value": 300},
                        ],
                    },
                    "unit": "s",
                    "noValue": "UNKNOWN",
                },
                "overrides": [],
            }
            p["options"] = {
                "legend": {
                    "calcs": ["lastNotNull", "max"],
                    "displayMode": "table",
                    "placement": "bottom",
                    "showLegend": True,
                },
                "tooltip": {"mode": "multi", "sort": "desc"},
            }
        if p.get("id") == 9991 or str(p.get("title") or "").startswith("First Action"):
            options = cast(JsonObject, p.setdefault("options", {}))
            options["mode"] = "markdown"
            options["content"] = (
                "**Next best actions**\n"
                "1. Read **Status** + Metrics Evidence (confidence) before treating OK as final.\n"
                "2. Localize via **Aggregate Stage Lag** + Runtime Blockers.\n"
                "3. Escalate: DQ / Provider / Trust / Run Explorer with time preserved.\n"
                "4. Empty lag series → check scrape/rules (UNKNOWN is not OK)."
            )
        if p.get("id") == 9101 and p.get("type") == "table":
            defaults = p.setdefault("fieldConfig", {}).setdefault("defaults", {})
            defaults["links"] = [
                {
                    "title": "Open Run Explorer",
                    "url": (
                        "/d/bioetl-run-explorer-v1/bioetl-run-explorer-v1"
                        "?${__url_time_range}&var-workflow=${workflow}"
                        "&var-pipeline=${pipeline}&var-run_type=${run_type}"
                        "&var-run_id=${run_id}"
                    ),
                    "targetBlank": False,
                },
                {
                    "title": "Open Data Quality",
                    "url": (
                        "/d/bioetl-dq-v2/bioetl-dq-v2?${__url_time_range}"
                        "&var-workflow=${workflow}&var-pipeline=${pipeline}"
                        "&var-run_type=${run_type}"
                    ),
                    "targetBlank": False,
                },
            ]
    if not found:
        raise SystemExit("9105 not found")
    save_dash(DASHBOARD_RUNTIME, rt)
    # hard verify
    rt2 = load_dash(DASHBOARD_RUNTIME)
    p9105 = next(p for p in walk(rt2.get("panels")) if p.get("id") == 9105)
    assert p9105["type"] == "timeseries", p9105["type"]
    print("runtime 9105 OK", p9105["type"], p9105["title"])


def _incident_status_mappings() -> list[JsonObject]:
    return [
        {
            "type": "value",
            "options": {
                "0": {"text": "OK", "color": "green"},
                "1": {"text": "WARN", "color": "orange"},
                "2": {"text": "CRIT", "color": "red"},
                "3": {"text": "UNKNOWN", "color": "gray"},
            },
        },
        {
            "type": "special",
            "options": {
                "match": "null",
                "result": {"text": "UNKNOWN", "color": "gray"},
            },
        },
    ]


def _incident_status_thresholds() -> JsonObject:
    return {
        "mode": "absolute",
        "steps": [
            {"color": "green", "value": None},
            {"color": "orange", "value": 1},
            {"color": "red", "value": 2},
            {"color": "gray", "value": 3},
        ],
    }


def _incident_value_override() -> JsonObject:
    return {
        "matcher": {
            "id": "byRegexp",
            "options": r"^(Value|#Value|Value \(.*\)|value)$",
        },
        "properties": [
            {
                "id": "custom.cellOptions",
                "value": {"type": "color-background", "mode": "basic"},
            },
            {"id": "color", "value": {"mode": "thresholds"}},
            {
                "id": "thresholds",
                "value": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "orange", "value": 1},
                        {"color": "red", "value": 2},
                    ],
                },
            },
        ],
    }


def _fix_incident_table(panel: JsonObject, *, value_override: JsonObject) -> None:
    fc = panel.setdefault("fieldConfig", {})
    defaults = fc.setdefault("defaults", {})
    custom = defaults.setdefault("custom", {})
    custom["cellOptions"] = {"type": "auto"}
    custom["align"] = "left"
    custom["inspect"] = False
    defaults["color"] = {"mode": "thresholds"}
    fc["overrides"] = [deepcopy(value_override)]


def _apply_incident_status_panel(panel: JsonObject) -> None:
    defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
    defaults["mappings"] = _incident_status_mappings()
    defaults["thresholds"] = _incident_status_thresholds()
    defaults["color"] = {"mode": "thresholds"}
    defaults["noValue"] = "UNKNOWN"
    defaults["decimals"] = 0
    panel["description"] = (
        "Worst-of L0 status for selected pipeline/run_type. "
        "Vocabulary: 0=OK, 1=WARN, 2=CRIT, 3/null=UNKNOWN (labelled; never bare numeric)."
    )


def _incident_handoff_urls() -> dict[int, str]:
    return {
        2002: (
            "/d/bioetl-runtime/bioetl-runtime?${__url_time_range}"
            "&var-workflow=${workflow}"
            "&var-pipeline=${__data.fields.pipeline:percentencode}"
            "&var-run_type=${run_type}"
        ),
        2003: (
            "/d/bioetl-provider-health-v2/bioetl-provider-health-v2?${__url_time_range}"
            "&var-workflow=${workflow}"
            "&var-provider=${__data.fields.provider:percentencode}"
        ),
        2004: (
            "/d/bioetl-dq-v2/bioetl-dq-v2?${__url_time_range}"
            "&var-workflow=${workflow}"
            "&var-pipeline=${__data.fields.pipeline:percentencode}"
            "&var-run_type=${run_type}"
        ),
    }


def _apply_incident_handoffs(by_id: dict[int, JsonObject]) -> None:
    for pid, url in _incident_handoff_urls().items():
        if pid not in by_id:
            continue
        defaults = by_id[pid].setdefault("fieldConfig", {}).setdefault("defaults", {})
        defaults["links"] = [
            {"title": "Open domain workspace", "url": url, "targetBlank": False}
        ]


def _incident_domain_links() -> list[JsonObject]:
    return [
        {
            "title": "Open Pipeline Diagnostics",
            "url": (
                "/d/bioetl-runtime/bioetl-runtime?${__url_time_range}"
                "&var-workflow=${workflow}"
                "&var-pipeline=${__data.fields.pipeline:percentencode}"
                "&var-run_type=${run_type}&var-run_id=${run_id}"
            ),
            "targetBlank": False,
        },
        {
            "title": "Open Provider Health",
            "url": (
                "/d/bioetl-provider-health-v2/bioetl-provider-health-v2?${__url_time_range}"
                "&var-workflow=${workflow}&var-pipeline=${pipeline}"
                "&var-run_type=${run_type}"
                "&var-provider=${__data.fields.provider:percentencode}"
            ),
            "targetBlank": False,
        },
        {
            "title": "Open Data Quality",
            "url": (
                "/d/bioetl-dq-v2/bioetl-dq-v2?${__url_time_range}"
                "&var-workflow=${workflow}"
                "&var-pipeline=${__data.fields.pipeline:percentencode}"
                "&var-run_type=${run_type}"
            ),
            "targetBlank": False,
        },
        {
            "title": "Open Run Explorer",
            "url": (
                "/d/bioetl-run-explorer-v1/bioetl-run-explorer-v1?${__url_time_range}"
                "&var-workflow=${workflow}&var-pipeline=${pipeline}"
                "&var-run_type=${run_type}&var-run_id=${run_id}"
            ),
            "targetBlank": False,
        },
    ]


def _ranked_suspects_panel(*, value_override: JsonObject) -> JsonObject:
    return {
        "id": 2010,
        "type": "table",
        "title": "Ranked Active Suspects",
        "description": (
            "Cross-domain ranked suspects (Runtime / Provider / DQ). "
            "Domain label identifies source; field links provide scoped handoff. "
            "VALID_EMPTY when no active suspects. Read-only."
        ),
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 9},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [
            {
                "refId": "A",
                "expr": (
                    "topk(15, label_replace(label_replace("
                    "max by (pipeline, run_type, reason) "
                    "(bioetl_runtime_current_blocker_reason) > 0, "
                    '"domain", "runtime", "", ""), '
                    '"signal", "$1", "reason", "(.*)"))'
                ),
                "legendFormat": "runtime",
                "instant": True,
                "format": "table",
            },
            {
                "refId": "B",
                "expr": (
                    "topk(15, label_replace(label_replace("
                    "max by (provider, cause) (bioetl_provider_current_cause) > 0, "
                    '"domain", "provider", "", ""), '
                    '"signal", "$1", "cause", "(.*)"))'
                ),
                "legendFormat": "provider",
                "instant": True,
                "format": "table",
            },
            {
                "refId": "C",
                "expr": (
                    "topk(15, label_replace(label_replace("
                    "max by (pipeline, reason) (bioetl_dq_current_reason) > 0, "
                    '"domain", "dq", "", ""), '
                    '"signal", "$1", "reason", "(.*)"))'
                ),
                "legendFormat": "dq",
                "instant": True,
                "format": "table",
            },
        ],
        "transformations": [
            {"id": "merge", "options": {}},
            {
                "id": "organize",
                "options": {
                    "excludeByName": {
                        "Time": True,
                        "Time 1": True,
                        "Time 2": True,
                    },
                    "indexByName": {},
                    "renameByName": {},
                },
            },
        ],
        "fieldConfig": {
            "defaults": {
                "noValue": "VALID_EMPTY — no active suspects across domains",
                "custom": {
                    "align": "left",
                    "cellOptions": {"type": "auto"},
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
                "links": _incident_domain_links(),
            },
            "overrides": [deepcopy(value_override)],
        },
        "options": {
            "showHeader": True,
            "cellHeight": "sm",
            "footer": {
                "show": False,
                "reducer": ["sum"],
                "countRows": False,
                "fields": "",
            },
            "sortBy": [{"displayName": "Value", "desc": True}],
        },
    }


def _layout_incident_core_panels(
    by_id: dict[int, JsonObject],
    *,
    value_override: JsonObject,
) -> None:
    """Apply grid positions and NBA content for core incident panels."""
    nav = by_id.get(1000)
    prov = by_id.get(9400)
    status = by_id.get(9401)
    nba = by_id.get(2001)
    alerts = by_id.get(2005)
    hist = by_id.get(2006)
    impact = by_id.get(2007)
    if nav:
        nav["gridPos"] = {"h": 3, "w": 24, "x": 0, "y": 0}
    if prov:
        prov["gridPos"] = {"h": 3, "w": 16, "x": 0, "y": 3}
    if status:
        status["gridPos"] = {"h": 3, "w": 8, "x": 16, "y": 3}
    if nba:
        nba["gridPos"] = {"h": 3, "w": 24, "x": 0, "y": 6}
        nba.setdefault("options", {})["mode"] = "markdown"
        nba["options"]["content"] = (
            "**Next best actions (≤4)**\n"
            "1. Read labelled **Status** (never bare numbers).\n"
            "2. Open top row in **Ranked Active Suspects** (domain handoff).\n"
            "3. Confirm alerts history for the selected range.\n"
            "4. Exact identity → Run Explorer; resume → Trust Review First Recovery Action.\n"
            "Read-only workspace — no persistent incident record."
        )
    if alerts:
        alerts["gridPos"] = {"h": 6, "w": 12, "x": 0, "y": 17}
        _fix_incident_table(alerts, value_override=value_override)
    if hist:
        hist["gridPos"] = {"h": 6, "w": 12, "x": 12, "y": 17}
    if impact:
        impact["gridPos"] = {"h": 4, "w": 24, "x": 0, "y": 23}


def _incident_detail_row(
    by_id: dict[int, JsonObject], *, value_override: JsonObject
) -> JsonObject:
    detail_row: JsonObject = {
        "id": 2099,
        "type": "row",
        "title": "Domain suspect detail (forensics)",
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": 27},
        "collapsed": True,
        "panels": [],
    }
    for i, pid in enumerate((2002, 2003, 2004)):
        src = by_id.get(pid)
        if not src:
            continue
        child = deepcopy(src)
        _fix_incident_table(child, value_override=value_override)
        child["gridPos"] = {"h": 7, "w": 8, "x": i * 8, "y": 28}
        detail_row["panels"].append(child)
    return detail_row


def _verify_incident_dashboard() -> None:
    inc2 = load_dash(DASHBOARD_INCIDENT_V1)
    st = next(p for p in walk(inc2.get("panels")) if p.get("id") == 9401)
    maps = (st.get("fieldConfig") or {}).get("defaults", {}).get("mappings") or []
    flat = {}
    for mapping in maps:
        if mapping.get("type") != "value":
            continue
        for key, value in (mapping.get("options") or {}).items():
            if isinstance(value, dict):
                flat[str(key)] = value.get("text")
    assert flat.get("3") == "UNKNOWN", flat
    t2002 = next(p for p in walk(inc2.get("panels")) if p.get("id") == 2002)
    cell = (
        (t2002.get("fieldConfig") or {})
        .get("defaults", {})
        .get("custom", {})
        .get("cellOptions", {})
        .get("type")
    )
    assert cell == "auto", cell
    assert any(p.get("id") == 2010 for p in walk(inc2.get("panels")))
    print("incident OK")


def fix_incident() -> None:
    inc = load_dash(DASHBOARD_INCIDENT_V1)
    panels = inc.get("panels") or []
    by_id = {p.get("id"): p for p in panels}
    value_override = _incident_value_override()

    if 9401 in by_id:
        _apply_incident_status_panel(by_id[9401])
    for pid in (2002, 2003, 2004, 2005):
        if pid in by_id:
            _fix_incident_table(by_id[pid], value_override=value_override)
    _apply_incident_handoffs(by_id)
    ranked = _ranked_suspects_panel(value_override=value_override)
    _layout_incident_core_panels(by_id, value_override=value_override)
    detail_row = _incident_detail_row(by_id, value_override=value_override)
    ordered = [
        p
        for p in (
            by_id.get(1000),
            by_id.get(9400),
            by_id.get(9401),
            by_id.get(2001),
            ranked,
            by_id.get(2005),
            by_id.get(2006),
            by_id.get(2007),
            detail_row,
        )
        if p is not None
    ]
    inc["panels"] = ordered
    save_dash(DASHBOARD_INCIDENT_V1, inc)
    _verify_incident_dashboard()


def fix_trust() -> None:
    cp = load_dash(DASHBOARD_CONTROL_PLANE_V1)
    for p in walk(cp.get("panels")):
        if p.get("id") == 906:
            p["title"] = PANEL_PRIMARY_RECOVERY
            p.setdefault("options", {})["mode"] = "markdown"
            p["options"]["content"] = (
                "**Review First Recovery Action (Safety Gate)** — act only after Status + four evidence cells:\n"
                "1. **INCOMPLETE/UNKNOWN** → repair telemetry / checkpoint / integrity before resume.\n"
                "2. Non-OK gate cell → open that drilldown "
                "(Replay Safety / Checkpoint / Manifest / Telemetry).\n"
                "3. Exact run selected → **Run Explorer** for identity proof.\n"
                "4. VALID_EMPTY blockers only when Status=OK and cards clean."
            )
            p["options"]["dataLinks"] = [
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
            ]
        if p.get("title") in {
            "Monitor Replay Safety",
            "Monitor Checkpoint Age",
            "Monitor Manifest/Ledger",
            "Monitor Telemetry",
        }:
            desc = p.get("description") or ""
            note = (
                " Safety-gate cell (not an independent KPI); "
                "pair with Status + Review First Recovery Action."
            )
            if "Safety-gate cell" not in desc:
                p["description"] = (desc + note).strip()
    save_dash(DASHBOARD_CONTROL_PLANE_V1, cp)
    cp2 = load_dash(DASHBOARD_CONTROL_PLANE_V1)
    titles = {p.get("title") for p in walk(cp2.get("panels"))}
    assert PANEL_PRIMARY_RECOVERY in titles
    assert PANEL_NEXT_ACTION_REPLAY_DIAGNOSTICS not in titles
    print("trust OK")


def _append_desc_note(panel: JsonObject, *, marker: str, note: str) -> None:
    """Append a description note when the marker is not already present."""
    desc = panel.get("description") or ""
    if marker not in desc:
        panel["description"] = (desc + note).strip()


def _fix_dq_panels(dq: JsonObject) -> None:
    for panel in walk(dq.get("panels")):
        if panel.get("title") == "Status" and panel.get("type") == "stat":
            _append_desc_note(
                panel,
                marker="NOW-lane",
                note=(
                    " NOW-lane decision only; range KPI cards are accounting, "
                    "not peer severity."
                ),
            )
        title = panel.get("title") or ""
        if panel.get("type") == "text" and (
            "First Action" in title or panel.get("id") in {9103, 9991, 2001}
        ):
            panel.setdefault("options", {})["mode"] = "markdown"
            panel["options"]["content"] = (
                "**Data trust — next actions**\n"
                "1. Read **NOW Status** + current threshold/reasons (not range zeros).\n"
                "2. If blocked/quarantine/rejects > 0, use accounting with denominators.\n"
                "3. Selected run → Run Explorer; resume → Trust Review First Recovery Action.\n"
                "4. Range cards are SLA/freshness context only."
            )


def _is_fleet_matrix_panel(panel: JsonObject) -> bool:
    title = panel.get("title") or ""
    if panel.get("type") not in {"table", "bargauge"}:
        return False
    if "Provider" not in title and "Fleet" not in title and "Severity" not in title:
        return False
    y = (panel.get("gridPos") or {}).get("y", 99)
    return y <= 25


def _provider_context_link() -> JsonObject:
    return {
        "title": "Open selected provider context",
        "url": (
            "/d/bioetl-provider-health-v2/bioetl-provider-health-v2"
            "?${__url_time_range}&var-workflow=${workflow}"
            "&var-provider=${__data.fields.provider:percentencode}"
            "&var-pipeline=${pipeline}&var-run_type=${run_type}"
        ),
        "targetBlank": False,
    }


def _fix_provider_health_panels(ph: JsonObject) -> None:
    for panel in walk(ph.get("panels")):
        if not _is_fleet_matrix_panel(panel):
            continue
        _append_desc_note(
            panel,
            marker="Fleet-first",
            note=(
                " Fleet-first matrix: answer without forcing a provider selector; "
                "select row to deep-dive."
            ),
        )
        if panel.get("type") == "table":
            defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
            defaults.setdefault("links", [_provider_context_link()])


_RUN_EXPLORER_BROWSE_CONTENT = (
    "**Browse vs Selected run**\n"
    "- **Browse:** population/list without `run_id` — identity panels "
    "show N/A until selection.\n"
    "- **Selected:** set `run_id` (Ops HTTP identity, never a Prometheus label).\n"
    "- Handoff from Incident/Runtime/Trust preserves time range + pipeline context."
)

_RUN_EXPLORER_GUIDE_CONTENT = (
    "**Browse vs Selected run**\n"
    "- **Browse:** no `run_id` — forensics show N/A until exact selection.\n"
    "- **Selected:** `run_id` is Ops HTTP identity only (never Prom label).\n"
    "- Preserve time range on handoff back to origin workspace."
)


def _shift_run_explorer_panels(run_explorer: JsonObject, *, delta_y: int = 3) -> None:
    for panel in run_explorer.get("panels") or []:
        grid_pos = panel.get("gridPos") or {}
        if "y" in grid_pos:
            grid_pos["y"] = int(grid_pos["y"]) + delta_y


def _fix_run_explorer_panels(run_explorer: JsonObject) -> None:
    for panel in run_explorer.get("panels") or []:
        if panel.get("id") == 1 and panel.get("type") == "text":
            panel.setdefault("options", {})["mode"] = "markdown"
            panel["options"]["content"] = _RUN_EXPLORER_BROWSE_CONTENT
            return
    guide: JsonObject = {
        "id": 9405,
        "type": "text",
        "title": "Browse · Selected run",
        "gridPos": {"h": 3, "w": 24, "x": 0, "y": 3},
        "options": {
            "mode": "markdown",
            "content": _RUN_EXPLORER_GUIDE_CONTENT,
        },
    }
    _shift_run_explorer_panels(run_explorer)
    run_explorer.setdefault("panels", []).insert(1, guide)


def fix_dq_provider_run() -> None:
    dq = load_dash("bioetl-dq-v2.json")
    _fix_dq_panels(dq)
    save_dash("bioetl-dq-v2.json", dq)

    ph = load_dash("bioetl-provider-health-v2.json")
    _fix_provider_health_panels(ph)
    save_dash("bioetl-provider-health-v2.json", ph)

    run_explorer = load_dash("bioetl-run-explorer-v1.json")
    _fix_run_explorer_panels(run_explorer)
    save_dash("bioetl-run-explorer-v1.json", run_explorer)
    print("dq/provider/run OK")


def fix_tests() -> None:
    path = TESTS / "test_grafana_config.py"
    text = path.read_text(encoding="utf-8")
    text2 = text.replace(PANEL_NEXT_ACTION_REPLAY_DIAGNOSTICS, PANEL_PRIMARY_RECOVERY)
    path.write_text(text2, encoding="utf-8")
    assert PANEL_PRIMARY_RECOVERY in path.read_text(encoding="utf-8")
    assert PANEL_NEXT_ACTION_REPLAY_DIAGNOSTICS not in path.read_text(encoding="utf-8")
    print("tests OK", path)


def main() -> None:
    print("ROOT", ROOT)
    assert (ROOT / "grafana" / "dashboards").is_dir()
    fix_runtime()
    fix_incident()
    fix_trust()
    fix_dq_provider_run()
    fix_tests()
    print("ALL DS2 FIXES APPLIED AND VERIFIED")


if __name__ == "__main__":
    main()
