#!/usr/bin/env python3
"""Apply Grafana simplification epic #6570 (phases 1a–4) to shipped dashboards.

Preserves nested coordinates inside pre-existing collapsed rows. Newly collapsed
panels receive local (relative) gridPos packing only.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

DASH = Path("grafana/dashboards")
FIRST_Y = 28

SURFACE_TITLES = {
    "bioetl-control-plane-v1": "0. Trust",
    "bioetl-overview-v2": "1. Overview",
    "bioetl-runtime": "2. Pipeline Diagnostics",
    "bioetl-provider-health-v2": "3. Provider Health",
    "bioetl-dq-v2": "4. Data Quality",
}

NAV_ORDER = [
    ("bioetl-control-plane-v1", "0. Trust"),
    ("bioetl-overview-v2", "1. Overview"),
    ("bioetl-runtime", "2. Pipeline Diagnostics"),
    ("bioetl-dq-v2", "4. Data Quality"),
]

NAV_HREFS = {
    "bioetl-control-plane-v1": (
        "/d/bioetl-control-plane-v1/bioetl-control-plane-v1"
        "?var-pipeline=$pipeline&amp;var-run_type=$run_type"
        "&amp;${__url_time_range}&amp;var-workflow=$workflow&amp;var-run_id=$run_id"
    ),
    "bioetl-overview-v2": (
        "/d/bioetl-overview-v2/bioetl-overview-v2"
        "?var-pipeline=$pipeline&amp;var-run_type=$run_type"
        "&amp;${__url_time_range}&amp;var-workflow=$workflow&amp;var-run_id=$run_id"
    ),
    "bioetl-runtime": (
        "/d/bioetl-runtime/bioetl-runtime"
        "?var-pipeline=$pipeline&amp;var-run_type=$run_type&amp;var-stage=unknown"
        "&amp;${__url_time_range}&amp;var-workflow=$workflow&amp;var-run_id=$run_id"
    ),
    "bioetl-dq-v2": (
        "/d/bioetl-dq-v2/bioetl-dq-v2"
        "?var-pipeline=$pipeline&amp;var-run_type=$run_type&amp;var-stage=unknown"
        "&amp;${__url_time_range}&amp;var-workflow=$workflow&amp;var-run_id=$run_id"
    ),
}

THIN_EXPR: dict[tuple[str, str], str] = {
    ("bioetl-overview-v2", "Status"): (
        'max(bioetl_l0_status{pipeline=~"$pipeline",run_type=~"$run_type"})'
    ),
    ("bioetl-overview-v2", "First Action"): (
        'topk(1, bioetl_l0_next_action_route{pipeline=~"$pipeline",run_type=~"$run_type"})'
    ),
    ("bioetl-overview-v2", "Inputs"): (
        "max by (input) (bioetl_l0_input_status_selected"
        '{pipeline=~"$pipeline",run_type=~"$run_type"})'
    ),
    ("bioetl-overview-v2", "Triage Alert State"): (
        'count by (alertname, severity) (ALERTS{alertstate="firing",service="bioetl"})'
    ),
    ("bioetl-control-plane-v1", "Status"): (
        "max(bioetl_control_plane_current_status_trusted"
        '{pipeline=~"$pipeline",run_type=~"$run_type"})'
    ),
    ("bioetl-control-plane-v1", "Monitor: Replay Safety State"): (
        'max(bioetl_replay_safety_blockers_15m{pipeline=~"$pipeline"})'
    ),
    ("bioetl-control-plane-v1", "Monitor: Manifest / Ledger Integrity"): (
        'max(bioetl_manifest_ledger_failures_15m{pipeline=~"$pipeline"})'
    ),
    ("bioetl-control-plane-v1", "Inspect: Telemetry Missing"): (
        'max(bioetl_control_plane_telemetry_missing_5m{pipeline=~"$pipeline"})'
    ),
    ("bioetl-runtime", "Runtime Error Rate"): (
        'max(bioetl_runtime_error_rate_30m{pipeline=~"$pipeline"})'
    ),
    ("bioetl-dq-v2", "Monitor DQ Threshold State"): (
        '(max(bioetl_dq_current_reason{pipeline=~"$pipeline",severity="crit"}>0)*2) '
        'or max(bioetl_dq_current_status{pipeline=~"$pipeline"})'
    ),
    ("bioetl-provider-health-v2", "Status"): (
        'max(bioetl_provider_current_status{provider=~"$provider"})'
    ),
    ("bioetl-provider-health-v2", "Monitor GLOBAL Provider Severity Matrix"): (
        "max by (provider) (bioetl_provider_current_status)"
    ),
    ("bioetl-provider-health-v2", "Inspect Critical Providers"): (
        "max by (provider) (bioetl_provider_current_status) >= 1"
    ),
    ("bioetl-provider-health-v2", "Inspect Provider Top Causes"): (
        "topk(5, max by (provider, cause) (bioetl_provider_current_cause) > 0)"
    ),
    ("bioetl-provider-health-v2", "Monitor Provider Telemetry Freshness"): (
        'count(bioetl_provider_current_status{provider=~"$provider"}) > bool 0'
    ),
}

REMOVE_TITLES: dict[str, set[str]] = {
    "bioetl-runtime": {"Runtime Status"},
    "bioetl-dq-v2": {"Monitor DQ Current Status"},
}

COLLAPSE: dict[str, dict[str, set[str]]] = {
    "bioetl-provider-health-v2": {
        "Range / debug evidence": {
            "Review Raw Provider Health Enum",
            "Monitor Healthy Checks (Selected Range)",
            "Monitor Degraded Checks (Selected Range)",
            "Monitor Total Checks (Selected Range)",
            "Track Health Check Latency by Provider (p95)",
            "Monitor Provider Failure Rate (Selected Range)",
        }
    },
    "bioetl-dq-v2": {
        "Range / debug evidence": {
            "Track: Records Quarantined in Range",
            "Track: Silver Validation Failures in Range",
            "Track: Silver Filter Rejects in Range",
            "Track: Source Records in Range (Bronze)",
            "Track: Clean Records in Range (Gold)",
            "Monitor: Data Quality Score (Volume-weighted)",
            "Monitor: Worst-Entity DQ Score",
        }
    },
    "bioetl-runtime": {
        "Runtime secondary KPIs": {
            "Worst Stage Lag",
            "Monitor Runtime Blockers",
            "Failed Runs",
        }
    },
    "bioetl-workflow-overview": {
        "Range / debug evidence": {
            "Failed Workflow Runs / Range",
            "Failed Pipeline Steps / Range",
            "Failed Transform Steps / Range",
            "Skipped Step Events / Range",
        }
    },
}

SHELL = {"ID", "Processed Records"}
IDENTITY = {
    "Inspect: Overview Identity Anchors",
    "Inspect: Copyable Identity Handoffs",
    "Inspect: Identity Gaps",
}


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _save(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _walk(panels: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack = list(panels or [])
    while stack:
        panel = stack.pop(0)
        if not isinstance(panel, dict):
            continue
        out.append(panel)
        nested = panel.get("panels")
        if isinstance(nested, list):
            stack[0:0] = [item for item in nested if isinstance(item, dict)]
    return out


def _next_id(payload: dict[str, Any]) -> int:
    max_id = 0
    for panel in _walk(payload.get("panels")):
        pid = panel.get("id")
        if isinstance(pid, int):
            max_id = max(max_id, pid)
    return max_id + 1


def _make_nav(uid: str) -> str:
    link = (
        "box-sizing:border-box;flex:1 1 145px;text-align:center;padding:3px 7px;"
        "border-radius:3px;font-weight:600;line-height:1.35;color:#f8fafc;"
        "background:#334155;border:1px solid #94a3b8;text-decoration:none"
    )
    current = (
        "box-sizing:border-box;flex:1 1 145px;text-align:center;padding:3px 7px;"
        "border-radius:3px;font-weight:600;line-height:1.35;color:#fff;"
        "background:#1d4ed8;border:2px solid #7dd3fc;cursor:default"
    )
    parts = [
        '<div class="bioetl-nav" role="navigation" aria-label="BioETL dashboards" '
        'style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;'
        'padding:4px 6px;overflow:visible;white-space:normal;font-size:11px">'
    ]
    for peer_uid, title in NAV_ORDER:
        if peer_uid == uid:
            parts.append(f'<span aria-current="page" style="{current}">{title}</span>')
        else:
            href = NAV_HREFS[peer_uid]
            parts.append(f'<a style="{link}" href="{href}">{title}</a>')
    parts.append("</div>")
    return "".join(parts)


def _set_expr(panel: dict[str, Any], expr: str) -> None:
    targets = panel.get("targets")
    if not isinstance(targets, list) or not targets:
        panel["targets"] = [{"expr": expr, "refId": "A"}]
        return
    for target in targets:
        if isinstance(target, dict):
            target["expr"] = expr
            return


def _remove_root(payload: dict[str, Any], titles: set[str]) -> list[dict[str, Any]]:
    removed: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for panel in payload.get("panels") or []:
        if isinstance(panel, dict) and panel.get("title") in titles:
            removed.append(panel)
        else:
            kept.append(panel)
    payload["panels"] = kept
    return removed


def _max_root_y(payload: dict[str, Any]) -> int:
    values = [
        int((panel.get("gridPos") or {}).get("y", 0))
        for panel in payload.get("panels") or []
        if isinstance(panel, dict)
    ]
    return max(values) if values else 0


def _append_collapsed_row(
    payload: dict[str, Any],
    title: str,
    panels: list[dict[str, Any]],
    y: int,
) -> None:
    if not panels:
        return
    nested: list[dict[str, Any]] = []
    cursor_y = 0
    index = 0
    while index < len(panels):
        left = copy.deepcopy(panels[index])
        left_grid = left.setdefault("gridPos", {})
        left_h = int(left_grid.get("h", 4))
        if index + 1 < len(panels):
            right = copy.deepcopy(panels[index + 1])
            right_grid = right.setdefault("gridPos", {})
            right_h = int(right_grid.get("h", 4))
            height = max(left_h, right_h)
            left_grid.update({"x": 0, "y": cursor_y, "w": 12, "h": left_h})
            right_grid.update({"x": 12, "y": cursor_y, "w": 12, "h": right_h})
            nested.extend([left, right])
            cursor_y += height
            index += 2
        else:
            width = int(left_grid.get("w", 24)) or 24
            left_grid.update({"x": 0, "y": cursor_y, "w": min(24, width), "h": left_h})
            nested.append(left)
            cursor_y += left_h
            index += 1

    row = {
        "type": "row",
        "title": title,
        "collapsed": True,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
        "id": _next_id(payload),
        "panels": nested,
    }
    payload.setdefault("panels", []).append(row)


def transform(path: Path) -> None:
    payload = _load(path)
    uid = str(payload.get("uid") or path.stem)
    payload["refresh"] = "60s"
    if uid in SURFACE_TITLES:
        payload["title"] = SURFACE_TITLES[uid]

    for panel in _walk(payload.get("panels")):
        if panel.get("id") == 1000:
            options = panel.setdefault("options", {})
            options["content"] = _make_nav(uid)
            options["mode"] = options.get("mode") or "html"

    banned = REMOVE_TITLES.get(uid)
    if banned:
        _remove_root(payload, banned)
        for panel in _walk(payload.get("panels")):
            if panel.get("title") != "Status":
                continue
            description = str(panel.get("description") or "")
            if "sole first-screen status" not in description.lower():
                panel["description"] = (
                    description + " Sole first-screen status (dual twin removed #6572)."
                ).strip()

    for row_title, titles in (COLLAPSE.get(uid) or {}).items():
        removed = _remove_root(payload, set(titles))
        if removed:
            _append_collapsed_row(
                payload,
                row_title,
                removed,
                max(_max_root_y(payload) + 1, FIRST_Y),
            )

    shell = _remove_root(payload, SHELL)
    if shell:
        for panel in payload.get("panels") or []:
            if not isinstance(panel, dict):
                continue
            if panel.get("title") not in {
                "First Action",
                "Review: First Action",
                "Next Action: Replay Diagnostics",
                "Pipeline Status",
            }:
                continue
            grid = panel.setdefault("gridPos", {})
            if int(grid.get("y", 99)) < 7:
                continue
            if panel.get("title") == "Pipeline Status":
                grid["y"] = 7
            else:
                grid.update({"x": 0, "y": 7, "w": max(int(grid.get("w", 8)), 14)})
        _append_collapsed_row(
            payload,
            "Run context (identity / processed records)",
            shell,
            max(_max_root_y(payload) + 1, FIRST_Y),
        )

    if uid == "bioetl-control-plane-v1":
        identity = _remove_root(payload, IDENTITY)
        if identity:
            target = None
            for panel in payload.get("panels") or []:
                if (
                    isinstance(panel, dict)
                    and panel.get("type") == "row"
                    and panel.get("title")
                    == "Identity evidence and remaining replay-safety signals"
                ):
                    target = panel
                    break
            if target is not None:
                target["collapsed"] = True
                nested = target.setdefault("panels", [])
                if not isinstance(nested, list):
                    nested = []
                    target["panels"] = nested
                cursor = 0
                for panel in identity:
                    clone = copy.deepcopy(panel)
                    grid = clone.setdefault("gridPos", {})
                    height = int(grid.get("h", 8))
                    grid.update({"x": 0, "y": cursor, "w": 24, "h": height})
                    nested.insert(0, clone)
                    cursor += height
            else:
                _append_collapsed_row(
                    payload,
                    "Identity evidence",
                    identity,
                    max(_max_root_y(payload) + 1, FIRST_Y),
                )

        for title, x in (
            ("Monitor: Replay Safety State", 0),
            ("Monitor: Checkpoint Freshness Lag (seconds)", 6),
            ("Monitor: Manifest / Ledger Integrity", 12),
            ("Inspect: Telemetry Missing", 18),
        ):
            for panel in payload.get("panels") or []:
                if isinstance(panel, dict) and panel.get("title") == title:
                    panel.setdefault("gridPos", {}).update(
                        {"x": x, "y": 13, "w": 6, "h": 4}
                    )

        for panel in _walk(payload.get("panels")):
            if panel.get("title") != "Monitor: Checkpoint Freshness Lag (seconds)":
                continue
            panel["datasource"] = "Prometheus"
            panel["targets"] = [
                {
                    "expr": 'max(bioetl_checkpoint_age_seconds{pipeline=~"$pipeline"})',
                    "refId": "A",
                }
            ]

        # Keep FA from overlapping safety cards.
        for panel in payload.get("panels") or []:
            if (
                isinstance(panel, dict)
                and panel.get("title") == "Next Action: Replay Diagnostics"
            ):
                panel.setdefault("gridPos", {}).update(
                    {"x": 0, "y": 7, "w": 24, "h": 6}
                )

        row_y = 17
        for panel in payload.get("panels") or []:
            if isinstance(panel, dict) and panel.get("type") == "row":
                panel.setdefault("gridPos", {})["y"] = row_y
                row_y += 1

    if uid == "bioetl-overview-v2":
        triage = None
        kept: list[dict[str, Any]] = []
        for panel in payload.get("panels") or []:
            if isinstance(panel, dict) and panel.get("title") == "Triage Alert State":
                triage = panel
                continue
            kept.append(panel)
        payload["panels"] = kept
        for panel in payload.get("panels") or []:
            if not (
                isinstance(panel, dict)
                and panel.get("type") == "row"
                and panel.get("title") == "Alert/SLO Triage"
            ):
                continue
            panel["collapsed"] = True
            if triage is None:
                break
            nested = panel.setdefault("panels", [])
            if not isinstance(nested, list):
                nested = []
                panel["panels"] = nested
            clone = copy.deepcopy(triage)
            height = int((triage.get("gridPos") or {}).get("h", 8))
            clone.setdefault("gridPos", {}).update(
                {"x": 0, "y": 0, "w": 24, "h": height}
            )
            nested.insert(0, clone)
            break

    if uid == "bioetl-dq-v2":
        max_answer = 0
        for panel in payload.get("panels") or []:
            if not isinstance(panel, dict) or panel.get("type") == "row":
                continue
            grid = panel.get("gridPos") or {}
            max_answer = max(max_answer, int(grid.get("y", 0)) + int(grid.get("h", 0)))
        row_y = max(max_answer, 23)
        for panel in payload.get("panels") or []:
            if isinstance(panel, dict) and panel.get("type") == "row":
                panel.setdefault("gridPos", {})["y"] = row_y
                row_y += 1

    for panel in _walk(payload.get("panels")):
        key = (uid, str(panel.get("title")))
        if key in THIN_EXPR:
            _set_expr(panel, THIN_EXPR[key])
        if panel.get("type") == "timeseries":
            panel.setdefault("maxDataPoints", 400)
            panel.setdefault("interval", "1m")

    _save(path, payload)
    print(f"updated {path.name} title={payload.get('title')!r}")


def _merge_workflow_band() -> None:
    runtime_path = DASH / "bioetl-runtime.json"
    workflow_path = DASH / "bioetl-workflow-overview.json"
    if not runtime_path.exists() or not workflow_path.exists():
        return
    runtime = _load(runtime_path)
    workflow = _load(workflow_path)
    borrowed: list[dict[str, Any]] = []
    wanted = {
        "Failed Workflow Runs / Range",
        "Failed Pipeline Steps / Range",
        "Pipeline Status",
        "First Action",
    }
    for panel in _walk(workflow.get("panels")):
        title = panel.get("title")
        if title not in wanted:
            continue
        clone = copy.deepcopy(panel)
        clone["id"] = _next_id(runtime) + len(borrowed)
        if title == "First Action":
            clone["title"] = "Workflow First Action"
        if title == "Pipeline Status":
            clone["title"] = "Workflow Pipeline Status"
        borrowed.append(clone)
    if borrowed:
        _append_collapsed_row(
            runtime,
            "Workflow band (merged from bioetl-workflow-overview)",
            borrowed,
            max(_max_root_y(runtime) + 1, FIRST_Y),
        )
        _save(runtime_path, runtime)
        print("merged workflow band into runtime")


def main() -> int:
    for path in sorted(DASH.glob("bioetl-*.json")):
        transform(path)
    _merge_workflow_band()
    for name in ("bioetl-workflow-overview.json", "bioetl-alerts-slo.json"):
        path = DASH / name
        if path.exists():
            path.unlink()
            print(f"deleted {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
