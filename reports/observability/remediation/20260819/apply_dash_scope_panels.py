"""One-shot DASH-SCOPE panel mutator for worktree grafana JSON."""

from __future__ import annotations

import json
from pathlib import Path

WT = Path(r"E:/github/wt-dash-scope-9009/grafana/dashboards")
D6 = (
    "/d/bioetl-run-explorer-v1?${__url_time_range}"
    "&var-pipeline=${pipeline}&var-run_type=${run_type}"
    "&var-run_id=${run_id}&var-workflow=${workflow}&viewPanel=9402"
)
SET_RANGE = (
    "/d/bioetl-run-explorer-v1?from=${__data.fields.from_ms}"
    "&to=${__data.fields.to_ms}"
    "&var-pipeline=${pipeline}&var-run_type=${run_type}"
    "&var-run_id=${run_id}&var-workflow=${workflow}&viewPanel=9402"
)
SUMMARY_URL = (
    "/ops/observability/pipeline-run-report?pipeline=${pipeline}"
    "&run_id=${run_id}&view=summary&from=${__from}&to=${__to}"
)
D6_LINK = {
    "title": "Open 6. Run Explorer for selected run",
    "url": D6,
    "targetBlank": False,
    "includeVars": False,
}
SET_RANGE_LINK = {
    "title": "Set range to run",
    "url": SET_RANGE,
    "targetBlank": False,
    "includeVars": False,
}


def load(name: str) -> dict[str, object]:
    return json.loads((WT / name).read_text(encoding="utf-8"))


def dump(name: str, payload: dict[str, object]) -> None:
    (WT / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def walk(panels: object):
    for pan in panels or []:
        if not isinstance(pan, dict):
            continue
        yield pan
        nested = pan.get("panels")
        if isinstance(nested, list):
            yield from walk(nested)


def find(dashboard: dict[str, object], pid: int) -> dict[str, object]:
    for pan in walk(dashboard.get("panels")):
        if pan.get("id") == pid:
            return pan
    raise KeyError(pid)


def ensure_d6_link(panel: dict[str, object]) -> None:
    fc = panel.setdefault("fieldConfig", {})
    if not isinstance(fc, dict):
        return
    defaults = fc.setdefault("defaults", {})
    if not isinstance(defaults, dict):
        return
    links = defaults.setdefault("links", [])
    if not isinstance(links, list):
        return
    replaced = False
    for item in links:
        if isinstance(item, dict) and "bioetl-run-explorer-v1" in str(
            item.get("url", "")
        ):
            item["url"] = D6
            item["title"] = "Open 6. Run Explorer for selected run"
            item["targetBlank"] = False
            item["includeVars"] = False
            replaced = True
    if not replaced:
        links.append(dict(D6_LINK))
    panel_links = panel.get("links")
    if isinstance(panel_links, list):
        for item in panel_links:
            if isinstance(item, dict) and "bioetl-run-explorer-v1" in str(
                item.get("url", "")
            ):
                if "viewPanel=" not in str(item.get("url", "")):
                    item["url"] = D6


def add_enum3_mapping(panel: dict[str, object]) -> None:
    fc = panel.get("fieldConfig")
    if not isinstance(fc, dict):
        return
    defaults = fc.get("defaults")
    if isinstance(defaults, dict):
        th = defaults.get("thresholds")
        if isinstance(th, dict):
            steps = th.get("steps")
            if isinstance(steps, list) and not any(
                isinstance(step, dict) and step.get("value") == 3 for step in steps
            ):
                steps.append({"color": "gray", "value": 3})
        mappings = defaults.get("mappings")
        if isinstance(mappings, list):
            for mapping in mappings:
                if isinstance(mapping, dict) and mapping.get("type") == "value":
                    opts = mapping.setdefault("options", {})
                    if isinstance(opts, dict) and "3" not in opts:
                        opts["3"] = {"text": "UNKNOWN", "color": "gray"}
    for ov in fc.get("overrides") or []:
        if not isinstance(ov, dict):
            continue
        matcher = ov.get("matcher") or {}
        if not isinstance(matcher, dict):
            continue
        if matcher.get("options") != "Value":
            continue
        for prop in ov.get("properties") or []:
            if not isinstance(prop, dict) or prop.get("id") != "mappings":
                continue
            mappings = prop.get("value") or []
            if not isinstance(mappings, list):
                continue
            for mapping in mappings:
                if isinstance(mapping, dict) and mapping.get("type") == "value":
                    opts = mapping.setdefault("options", {})
                    if isinstance(opts, dict) and "3" not in opts:
                        opts["3"] = {"text": "UNKNOWN", "color": "gray"}


def summary_panel(panel_id: int, title: str, grid: dict[str, int]) -> dict[str, object]:
    return {
        "id": panel_id,
        "type": "table",
        "title": title,
        "gridPos": grid,
        "datasource": "BioETL Ops HTTP",
        "description": (
            "SELECTED RUN · Compact pipeline_run_report_v1 projection "
            "(identity, times, gold out, contract exclusions, coverage). "
            "Missing run is VALID EMPTY / SELECT RUN, not OK. "
            "Set range to run opens 6. Run Explorer at started_at-5m .. completed_at+5m. "
            "Do not treat CURRENT Prometheus as this UUID."
        ),
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "align": "left",
                    "cellOptions": {"type": "auto"},
                    "inspect": True,
                },
                "unit": "none",
                "noValue": (
                    "SELECT RUN — no exact Run ID selected. Choose a run first. "
                    "VALID EMPTY if the selected run has no report."
                ),
                "links": [dict(D6_LINK), dict(SET_RANGE_LINK)],
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "set_range_to_run"},
                    "properties": [
                        {"id": "links", "value": [dict(SET_RANGE_LINK)]},
                    ],
                },
                {
                    "matcher": {"id": "byName", "options": "run_id"},
                    "properties": [
                        {"id": "links", "value": [dict(D6_LINK)]},
                    ],
                },
            ],
        },
        "options": {
            "showHeader": True,
            "footer": {"show": False},
            "cellHeight": "sm",
        },
        "targets": [
            {
                "format": "table",
                "parser": "backend",
                "refId": "A",
                "root_selector": "summary",
                "source": "url",
                "type": "json",
                "url": SUMMARY_URL,
                "url_options": {"data": "", "method": "GET"},
                "expr": "",
            }
        ],
        "transformations": [
            {
                "id": "organize",
                "options": {
                    "excludeByName": {
                        "Time": True,
                        "__name__": True,
                        "Value": True,
                    },
                    "indexByName": {
                        "run_id": 0,
                        "status": 1,
                        "started_at": 2,
                        "completed_at": 3,
                        "gold_records_out": 4,
                        "excluded_by_contract": 5,
                        "covers_selected_run": 6,
                        "coverage_offset": 7,
                        "set_range_to_run": 8,
                        "from_ms": 9,
                        "to_ms": 10,
                    },
                    "renameByName": {},
                },
            }
        ],
        "links": [dict(D6_LINK)],
    }


def reason_panel() -> dict[str, object]:
    return {
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "description": (
            "CURRENT · Status reason and source_state for the selected provider "
            "(or worst four when provider=All). Enum 0=OK, 1=WARN, 2=CRIT, 3=UNKNOWN. "
            "missing_health_status means no health_status series — not a healthy fleet. "
            "Adapter filter is hidden; adapter=All unless a chip says otherwise."
        ),
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "custom": {
                    "align": "auto",
                    "cellOptions": {"type": "auto"},
                    "inspect": False,
                },
                "mappings": [
                    {
                        "type": "special",
                        "options": {
                            "match": "null",
                            "result": {"text": "UNKNOWN", "color": "gray"},
                        },
                    },
                    {
                        "type": "special",
                        "options": {
                            "match": "nan",
                            "result": {"text": "UNKNOWN", "color": "gray"},
                        },
                    },
                ],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "gray", "value": None},
                        {"color": "green", "value": 0},
                        {"color": "orange", "value": 1},
                        {"color": "red", "value": 2},
                        {"color": "gray", "value": 3},
                    ],
                },
                "unit": "short",
                "noValue": (
                    "UNKNOWN — missing health_status for this provider, "
                    "or VALID EMPTY if the selected provider has no universe row."
                ),
            },
            "overrides": [
                {
                    "matcher": {
                        "id": "byRegexp",
                        "options": r"^(Value|#Value|Value \(.*\)|value|Value #.*)$",
                    },
                    "properties": [{"id": "displayName", "value": "Status"}],
                },
                {
                    "matcher": {"id": "byName", "options": "Value"},
                    "properties": [
                        {
                            "id": "custom.cellOptions",
                            "value": {"type": "color-background", "mode": "basic"},
                        },
                        {
                            "id": "mappings",
                            "value": [
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
                                {
                                    "type": "special",
                                    "options": {
                                        "match": "nan",
                                        "result": {"text": "UNKNOWN", "color": "gray"},
                                    },
                                },
                            ],
                        },
                    ],
                },
                {
                    "matcher": {"id": "byName", "options": "reason"},
                    "properties": [
                        {"id": "custom.width", "value": 280},
                        {
                            "id": "custom.cellOptions",
                            "value": {"type": "auto", "wrapText": True},
                        },
                    ],
                },
            ],
        },
        "gridPos": {"h": 5, "w": 12, "x": 12, "y": 10},
        "id": 9107,
        "options": {
            "cellHeight": "sm",
            "footer": {
                "countRows": False,
                "fields": "",
                "reducer": ["sum"],
                "show": False,
            },
            "showHeader": True,
            "sortBy": [{"desc": True, "displayName": "Status"}],
        },
        "pluginVersion": "10.4.0",
        "targets": [
            {
                "expr": (
                    "topk(4, max by (provider, reason, source_state) "
                    '(bioetl_provider_current_status_info{provider=~"$provider"}))'
                ),
                "format": "table",
                "instant": True,
                "legendFormat": "{{provider}} {{reason}} {{source_state}}",
                "refId": "A",
            }
        ],
        "title": "Inspect Status Reason",
        "type": "table",
        "transformations": [
            {
                "id": "organize",
                "options": {
                    "excludeByName": {"Time": True, "__name__": True},
                    "indexByName": {
                        "provider": 0,
                        "reason": 1,
                        "source_state": 2,
                        "Value": 3,
                    },
                    "renameByName": {
                        "Value": "Status",
                        "source_state": "source_state",
                    },
                },
            }
        ],
    }


def main() -> None:
    prov = load("bioetl-provider-health-v2.json")
    p9101 = find(prov, 9101)
    p9101["gridPos"]["w"] = 12
    add_enum3_mapping(p9101)
    add_enum3_mapping(find(prov, 9102))
    add_enum3_mapping(find(prov, 9401))
    root = prov["panels"]
    assert isinstance(root, list)
    if not any(p.get("id") == 9107 for p in walk(root)):
        idx = next(i for i, panel in enumerate(root) if panel.get("id") == 9101)
        root.insert(idx + 1, reason_panel())
    dump("bioetl-provider-health-v2.json", prov)
    print("provider", len(list(walk(prov.get("panels")))))

    ov = load("bioetl-overview-v2.json")
    ensure_d6_link(find(ov, 9300))
    children = find(ov, 9602).setdefault("panels", [])
    assert isinstance(children, list)
    if not any(p.get("id") == 9603 for p in children):
        children.append(
            summary_panel(
                9603,
                "Review Selected Run Summary",
                {"x": 0, "y": 62, "w": 24, "h": 5},
            )
        )
    dump("bioetl-overview-v2.json", ov)
    print("overview", len(list(walk(ov.get("panels")))))

    rt = load("bioetl-runtime.json")
    ensure_d6_link(find(rt, 9402))
    children = find(rt, 9993).setdefault("panels", [])
    assert isinstance(children, list)
    if not any(p.get("id") == 9998 for p in children):
        children.append(
            summary_panel(
                9998,
                "Review Selected Run Summary",
                {"x": 0, "y": 134, "w": 24, "h": 5},
            )
        )
    dump("bioetl-runtime.json", rt)
    print("runtime", len(list(walk(rt.get("panels")))))

    dq = load("bioetl-dq-v2.json")
    ensure_d6_link(find(dq, 9402))
    children = find(dq, 9405).setdefault("panels", [])
    assert isinstance(children, list)
    if not any(p.get("id") == 9406 for p in children):
        children.append(
            summary_panel(
                9406,
                "Review Selected Run Summary",
                {"x": 0, "y": 107, "w": 24, "h": 5},
            )
        )
    dump("bioetl-dq-v2.json", dq)
    print("dq", len(list(walk(dq.get("panels")))))

    inc = load("bioetl-incident-v1.json")
    panels = inc.get("panels")
    assert isinstance(panels, list)
    if not any(p.get("id") == 2100 for p in panels):
        panels.append(
            {
                "id": 2100,
                "type": "row",
                "title": "Inspect Selected Run Summary",
                "collapsed": True,
                "gridPos": {"h": 1, "w": 24, "x": 0, "y": 20},
                "description": (
                    "SELECTED RUN · Compact pipeline_run_report_v1 projection. "
                    "Expand after selecting an exact Run ID. Missing run is "
                    "SELECT RUN / VALID EMPTY, not OK."
                ),
                "panels": [
                    summary_panel(
                        2101,
                        "Review Selected Run Summary",
                        {"x": 0, "y": 21, "w": 24, "h": 5},
                    )
                ],
            }
        )
    dump("bioetl-incident-v1.json", inc)
    print("incident", len(list(walk(inc.get("panels")))))

    for name, pids in (
        ("bioetl-control-plane-v1.json", (9402, 9418)),
        ("bioetl-run-explorer-v1.json", (9402, 3010)),
        ("bioetl-provider-health-v2.json", (9402,)),
    ):
        dash = load(name)
        for pid in pids:
            ensure_d6_link(find(dash, pid))
        dump(name, dash)
        print(name, len(list(walk(dash.get("panels")))))


if __name__ == "__main__":
    main()
