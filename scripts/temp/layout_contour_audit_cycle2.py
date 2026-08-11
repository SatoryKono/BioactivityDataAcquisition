#!/usr/bin/env python3
"""Layout contour audit extractor for BioETL Grafana dashboards (cycle-2).

Read-only analysis of shipped JSON under grafana/dashboards/.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DASH_DIR = ROOT / "grafana" / "dashboards"
OUT_DIR = (
    ROOT
    / "reports"
    / "audit"
    / "dashboard-cycle"
    / "20260811T180000Z-c205349-dash"
    / "cycle-2"
)

DASHBOARDS = [
    "bioetl-control-plane-v1.json",
    "bioetl-overview-v2.json",
    "bioetl-runtime.json",
    "bioetl-provider-health-v2.json",
    "bioetl-dq-v2.json",
    "bioetl-incident-v1.json",
    "bioetl-run-explorer-v1.json",
]

# Contract-aligned first-screen answer panels (from tests + design-system).
ANSWER_PANELS: dict[str, list[str]] = {
    "bioetl-overview-v2": [
        "Monitor Fleet Health",
        "Review First Action",
        "Review Domain Status",
    ],
    "bioetl-control-plane-v1": [
        "Monitor Replay Readiness",
        "Monitor Replay Safety",
        "Monitor Checkpoint Age",
        "Monitor Manifest & Ledger Failures",
        "Monitor Telemetry Coverage",
        "Review Recovery Action",
    ],
    "bioetl-runtime": [
        "Monitor Pipeline Status",
        "Review Runtime Blockers",
        "Monitor Metrics Coverage",
        "Start Pipeline Triage",
    ],
    "bioetl-provider-health-v2": [
        "Monitor Fleet Severity",
        "Inspect Top Provider Causes",
        "Monitor Telemetry Freshness",
        "Start Provider Triage",
    ],
    "bioetl-dq-v2": [
        "Monitor Current DQ Status",
        "Start DQ Triage",
        "Monitor Worst Freshness Age",
    ],
    "bioetl-incident-v1": [
        "Monitor Incident Status",
        "Start Incident Triage",
        "Inspect Ranked Suspects",
        "Monitor Current Alerts",
    ],
    "bioetl-run-explorer-v1": [
        "Browse Recent Runs",
        "Inspect Run Identity",
        "Inspect Processed Records",
    ],
}


def walk(panels: list[dict[str, Any]] | None, parent_row: str | None = None):
    for p in panels or []:
        yield p, parent_row
        if p.get("type") == "row":
            yield from walk(p.get("panels") or [], str(p.get("title") or ""))
        else:
            yield from walk(p.get("panels") or [], parent_row)


def expr_sig(panel: dict[str, Any]) -> str | None:
    exprs = []
    for t in panel.get("targets") or []:
        if not isinstance(t, dict):
            continue
        e = t.get("expr")
        if isinstance(e, str) and e.strip():
            exprs.append(re.sub(r"\s+", " ", e.strip()))
    if not exprs:
        return None
    blob = "||".join(sorted(exprs))
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def overlaps(a: dict, b: dict) -> bool:
    ga, gb = a.get("gridPos") or {}, b.get("gridPos") or {}
    ax, ay, aw, ah = (
        int(ga.get("x", 0)),
        int(ga.get("y", 0)),
        int(ga.get("w", 0)),
        int(ga.get("h", 0)),
    )
    bx, by, bw, bh = (
        int(gb.get("x", 0)),
        int(gb.get("y", 0)),
        int(gb.get("w", 0)),
        int(gb.get("h", 0)),
    )
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def root_gaps(panels: list[dict]) -> list[tuple[int, int]]:
    spans = []
    for p in panels:
        gp = p.get("gridPos") or {}
        y, h = int(gp.get("y", 0)), int(gp.get("h", 0))
        if h <= 0:
            continue
        spans.append((y, y + h - 1))
    if not spans:
        return []
    occupied: set[int] = set()
    for s, e in spans:
        occupied.update(range(s, e + 1))
    min_y, max_y = min(s for s, _ in spans), max(e for _, e in spans)
    gaps, gap_start = [], None
    for row in range(min_y, max_y + 1):
        if row not in occupied:
            if gap_start is None:
                gap_start = row
        elif gap_start is not None:
            gaps.append((gap_start, row - 1))
            gap_start = None
    if gap_start is not None:
        gaps.append((gap_start, max_y))
    return gaps


def analyze(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    uid = data.get("uid") or path.stem
    title = data.get("title")
    description = data.get("description") or ""
    root = [p for p in data.get("panels") or [] if isinstance(p, dict)]
    all_panels = list(walk(root))

    # Root layout map
    root_map = []
    for p in root:
        gp = p.get("gridPos") or {}
        root_map.append(
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "type": p.get("type"),
                "collapsed": p.get("collapsed") if p.get("type") == "row" else None,
                "x": gp.get("x"),
                "y": gp.get("y"),
                "w": gp.get("w"),
                "h": gp.get("h"),
                "nested": len(p.get("panels") or []) if p.get("type") == "row" else 0,
            }
        )

    # Counts
    type_counts: Counter[str] = Counter()
    query_backed = 0
    empty_title = []
    title_counts: Counter[str] = Counter()
    for p, _ in all_panels:
        t = str(p.get("type") or "?")
        type_counts[t] += 1
        if p.get("targets"):
            query_backed += 1
        title_s = str(p.get("title") or "").strip()
        if not title_s and t != "row":
            empty_title.append(p.get("id"))
        if title_s:
            title_counts[title_s] += 1

    dup_titles = {k: v for k, v in title_counts.items() if v > 1}

    # Exact query signature duplicates across panels
    sig_map: dict[str, list[dict]] = defaultdict(list)
    for p, parent in all_panels:
        if p.get("type") in {"row", "text"}:
            continue
        sig = expr_sig(p)
        if sig:
            sig_map[sig].append(
                {
                    "id": p.get("id"),
                    "title": p.get("title"),
                    "type": p.get("type"),
                    "parent_row": parent,
                    "y": (p.get("gridPos") or {}).get("y"),
                }
            )
    dup_queries = {k: v for k, v in sig_map.items() if len(v) > 1}

    # Variables
    vars_list = []
    for v in (data.get("templating") or {}).get("list") or []:
        if not isinstance(v, dict):
            continue
        vars_list.append(
            {
                "name": v.get("name"),
                "label": v.get("label") or v.get("name"),
                "type": v.get("type"),
                "hide": v.get("hide"),
                "multi": v.get("multi"),
                "includeAll": v.get("includeAll"),
            }
        )
    visible_vars = [v for v in vars_list if v.get("hide") in (0, None, False)]

    # Rows
    rows = []
    for p in root:
        if p.get("type") == "row":
            rows.append(
                {
                    "title": p.get("title"),
                    "collapsed": p.get("collapsed"),
                    "y": (p.get("gridPos") or {}).get("y"),
                    "nested": len(p.get("panels") or []),
                }
            )

    # Overlaps / gaps at root
    ov = []
    for i, left in enumerate(root):
        for right in root[i + 1 :]:
            if overlaps(left, right):
                ov.append(
                    f"{left.get('id')}:{left.get('title')} x {right.get('id')}:{right.get('title')}"
                )
    gaps = root_gaps(root)

    # Above-fold proxy: y+h for root panels with y < 14 (approx first viewport at ~12-14 grid units)
    # Grafana default row height ~30px; 768px viewport ~25 units; chrome+vars ~ reduce to ~18-20.
    # Contract uses y<=10 for answer, y<=12 for L2 status.
    FOLD_Y = 14
    above = [m for m in root_map if m["y"] is not None and int(m["y"]) < FOLD_Y]
    answer_expected = ANSWER_PANELS.get(uid, [])
    answer_found = []
    for name in answer_expected:
        for p, parent in all_panels:
            if p.get("title") == name:
                gp = p.get("gridPos") or {}
                answer_found.append(
                    {
                        "title": name,
                        "id": p.get("id"),
                        "y": gp.get("y"),
                        "h": gp.get("h"),
                        "parent_row": parent,
                        "collapsed_parent": None,
                    }
                )
                break
    # mark collapsed parent
    collapsed_rows = {r["title"] for r in rows if r.get("collapsed") is True}
    for a in answer_found:
        if a["parent_row"] in collapsed_rows:
            a["collapsed_parent"] = a["parent_row"]

    # Max y extent
    max_y = 0
    for p, _ in all_panels:
        gp = p.get("gridPos") or {}
        y, h = int(gp.get("y") or 0), int(gp.get("h") or 0)
        max_y = max(max_y, y + h)

    # Root max y (visible without expand)
    root_max_y = 0
    for p in root:
        gp = p.get("gridPos") or {}
        y, h = int(gp.get("y") or 0), int(gp.get("h") or 0)
        root_max_y = max(root_max_y, y + h)

    # Expanded (non-collapsed) rows below fold
    expanded_rows = [r for r in rows if r.get("collapsed") is False]
    collapsed_rows_list = [r for r in rows if r.get("collapsed") is True]

    # Hover-only risk: tooltip-only is hard from JSON; flag panels with no description and type timeseries as low confidence N/A
    no_desc_query = [
        {"id": p.get("id"), "title": p.get("title"), "type": p.get("type")}
        for p, _ in all_panels
        if p.get("type") not in {"row", "text"}
        and p.get("targets")
        and not str(p.get("description") or "").strip()
    ]

    return {
        "file": path.name,
        "uid": uid,
        "title": title,
        "description_preview": description[:200],
        "panel_total_walk": len(all_panels),
        "root_panel_count": len(root),
        "type_counts": dict(type_counts),
        "query_backed": query_backed,
        "variables": vars_list,
        "visible_variable_count": len(visible_vars),
        "visible_variable_names": [v["name"] for v in visible_vars],
        "rows": rows,
        "expanded_rows": expanded_rows,
        "collapsed_rows": collapsed_rows_list,
        "root_map": root_map,
        "above_fold_root_y_lt_14": above,
        "answer_panels": answer_found,
        "duplicate_titles": dup_titles,
        "duplicate_query_groups": list(dup_queries.values())[:20],
        "duplicate_query_group_count": len(dup_queries),
        "empty_titles": empty_title,
        "root_overlaps": ov,
        "root_gaps": gaps,
        "root_max_y": root_max_y,
        "all_max_y": max_y,
        "no_description_query_panels_count": len(no_desc_query),
        "no_description_query_panels_sample": no_desc_query[:8],
        "refresh": data.get("refresh"),
        "time": data.get("time"),
        "timezone": data.get("timezone"),
    }


def main() -> None:
    results = []
    for name in DASHBOARDS:
        path = DASH_DIR / name
        if not path.exists():
            results.append({"file": name, "error": "missing"})
            continue
        results.append(analyze(path))

    # Cross-dashboard nav consistency
    nav_y0 = []
    for r in results:
        if "error" in r:
            continue
        nav = next((m for m in r["root_map"] if m.get("id") == 1000), None)
        nav_y0.append({"uid": r["uid"], "nav": nav})

    # Cross-dashboard variable sets
    var_sets = {
        r["uid"]: r.get("visible_variable_names", [])
        for r in results
        if "error" not in r
    }

    # Title collisions across dashboards (same title different uid) — informational
    title_to_uids: dict[str, set[str]] = defaultdict(set)
    for r in results:
        if "error" in r:
            continue
        for m in r["root_map"]:
            t = m.get("title")
            if t:
                title_to_uids[str(t)].add(r["uid"])

    summary = {
        "dashboards": results,
        "nav_y0": nav_y0,
        "variable_sets": var_sets,
        "shared_root_titles": {
            t: sorted(uids)
            for t, uids in title_to_uids.items()
            if len(uids) > 1 and t != "Navigate Dashboards"
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "layout-contour-extract.json"
    out_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Compact stdout report
    print(f"Wrote {out_path}")
    for r in results:
        if "error" in r:
            print(f"MISSING {r['file']}")
            continue
        print("=" * 72)
        print(f"{r['uid']} | title={r['title']}")
        print(
            f"  root={r['root_panel_count']} walk={r['panel_total_walk']} query_backed={r['query_backed']}"
        )
        print(f"  types={r['type_counts']}")
        print(
            f"  vars_visible={r['visible_variable_count']}: {r['visible_variable_names']}"
        )
        print(
            f"  rows expanded={len(r['expanded_rows'])} collapsed={len(r['collapsed_rows'])}"
        )
        for row in r["rows"]:
            flag = "COLLAPSED" if row["collapsed"] else "EXPANDED"
            print(
                f"    row y={row['y']} [{flag}] {row['title']} nested={row['nested']}"
            )
        print(f"  root_max_y={r['root_max_y']} all_max_y={r['all_max_y']}")
        print(
            f"  overlaps={r['root_overlaps'] or 'none'} gaps={r['root_gaps'] or 'none'}"
        )
        print(f"  dup_titles={r['duplicate_titles'] or '{}'}")
        print(f"  dup_query_groups={r['duplicate_query_group_count']}")
        if r["duplicate_query_groups"]:
            for g in r["duplicate_query_groups"][:5]:
                print(
                    f"    QDUP: {[(x['id'], x['title'], x['parent_row']) for x in g]}"
                )
        print("  answer panels:")
        for a in r["answer_panels"]:
            print(
                f"    y={a['y']} h={a['h']} id={a['id']} {a['title']} parent={a['parent_row']} collapsed_parent={a['collapsed_parent']}"
            )
        print("  root map (y-order):")
        for m in sorted(r["root_map"], key=lambda x: (x["y"] or 0, x["x"] or 0)):
            col = f" collapsed={m['collapsed']}" if m["type"] == "row" else ""
            print(
                f"    y={m['y']} x={m['x']} w={m['w']} h={m['h']} id={m['id']} [{m['type']}] {m['title']}{col}"
            )


if __name__ == "__main__":
    main()
