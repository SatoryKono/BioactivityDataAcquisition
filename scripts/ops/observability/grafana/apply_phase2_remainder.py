#!/usr/bin/env python3
"""Apply Phase 2 remainder (rev7 §§2.1–2.3, 2.7) on provisioned Grafana JSON.

Safe to re-run. Does not touch RF/#12708 surfaces. Pair with
``apply_phase25_srs_prr_budget.py`` (already applied) and
``lint_dashboard_phase2.py``.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from scripts.ops.observability.grafana.dashboard_context_links import PATH_BY_UID
from scripts.ops.observability.grafana.render_nav_bus import (
    BUS,
    DASH_DIR,
    FILE_BY_UID,
    NAV_HEIGHT,
    _attach_nav_bus,
    _stamp_nav_panel,
    write_dashboard_source,
)

ROOT = Path(__file__).resolve().parents[4]


def _walk(panels: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack = list(panels)
    while stack:
        panel = stack.pop(0)
        if not isinstance(panel, dict):
            continue
        out.append(panel)
        nested = panel.get("panels")
        if isinstance(nested, list):
            stack[0:0] = [item for item in nested if isinstance(item, dict)]
    return out


def _ensure_nav(payload: dict[str, Any], *, uid: str) -> None:
    panels = payload.setdefault("panels", [])
    if not isinstance(panels, list):
        raise SystemExit(f"{uid}: panels must be a list")
    nav = next((p for p in panels if isinstance(p, dict) and p.get("id") == 1000), None)
    if nav is None:
        nav = {
            "id": 1000,
            "type": "text",
            "title": "",
            "gridPos": {"x": 0, "y": 0, "w": 24, "h": NAV_HEIGHT},
            "options": {"mode": "html", "content": ""},
            "links": [],
            "description": "",
        }
        for panel in panels:
            if not isinstance(panel, dict):
                continue
            grid = panel.get("gridPos")
            if isinstance(grid, dict) and isinstance(grid.get("y"), int):
                grid["y"] = int(grid["y"]) + NAV_HEIGHT
        panels.insert(0, nav)
    _stamp_nav_panel(nav, panels)
    _attach_nav_bus(nav, current_uid=uid)
    # Compact Run Explorer first window after inserting the bus.
    if uid == "bioetl-run-explorer-v1":
        for panel in panels:
            if not isinstance(panel, dict):
                continue
            grid = panel.get("gridPos")
            if not isinstance(grid, dict):
                continue
            if panel.get("id") == 1:
                grid.update({"x": 0, "y": 2, "w": 24, "h": 2})
            elif panel.get("id") == 3010:
                grid.update({"x": 0, "y": 4, "w": 24, "h": 12})


def _move_data_links_to_panel_links(panel: dict[str, Any]) -> None:
    options = panel.get("options")
    if not isinstance(options, dict):
        return
    data_links = options.pop("dataLinks", None)
    if not isinstance(data_links, list) or not data_links:
        return
    existing = panel.get("links")
    links = list(existing) if isinstance(existing, list) else []
    seen = {(link.get("title"), link.get("url")) for link in links if isinstance(link, dict)}
    for link in data_links:
        if not isinstance(link, dict):
            continue
        key = (link.get("title"), link.get("url"))
        if key in seen:
            continue
        links.append(link)
        seen.add(key)
    panel["links"] = links


def _rewrite_url(url: str) -> str:
    if not isinstance(url, str) or not url:
        return url
    original = url

    # F-27 static slug: /d/{uid}/{uid} → /d/{uid}/{canonical-path}
    for uid, path in PATH_BY_UID.items():
        bad = f"/d/{uid}/{uid}"
        good = f"/d/{uid}/{path}"
        if bad in url:
            url = url.replace(bad, good)

    # F-27 dynamic: /d/${action_dashboard_uid}/${action_dashboard_uid}
    url = url.replace(
        "/d/${__data.fields.action_dashboard_uid}/${__data.fields.action_dashboard_uid}",
        "/d/${__data.fields.action_dashboard_uid}/",
    )

    # F-14 action_path glue: /${action_path}&… → /${action_path} (path already has ?)
    url = re.sub(
        r"/\$\{__data\.fields\.action_path\}&",
        "/${__data.fields.action_path}",
        url,
    )
    # Drop Grafana vars glued onto Ops artifact action_path URLs.
    if "${__data.fields.action_path}" in url and "var-pipeline=" in url:
        url = "/${__data.fields.action_path}"

    # F-26: strip Grafana query params from GitHub runbook links.
    if "github.com/" in url and ("blob/main/docs/" in url or "/runbooks/" in url):
        parts = urlsplit(url.replace("&amp;", "&"))
        if parts.query or "${" in url:
            # Keep scheme/netloc/path only; drop query + Grafana templates after ?
            path_only = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
            # Also handle templates that put ${} after ? without urlsplit query
            path_only = re.split(r"\?", path_only, maxsplit=1)[0]
            url = path_only

    # CP broken viewPanel=130 → Review Exact Replay Checks (9423)
    url = url.replace("viewPanel=130", "viewPanel=9423")
    # CP self-link / residual Selected-Run Trust deep-link → lineage/trust sibling 9414
    url = url.replace("viewPanel=9418", "viewPanel=9414")

    # F-12 Incident 9101 → DQ: do not carry page run_id into a different pipeline.
    if (
        "/d/bioetl-dq-v2/" in url
        and "var-pipeline=${__data.fields.pipeline" in url
        and "${run_id:queryparam}" in url
    ):
        url = url.replace("${run_id:queryparam}", "var-run_id=-")

    # Missing :percentencode on mapped __data.fields scalars (when bare).
    for field in ("workflow", "pipeline", "run_type"):
        url = re.sub(
            rf"\$\{{__data\.fields\.{field}\}}(?!:)",
            f"${{__data.fields.{field}:percentencode}}",
            url,
        )

    del original  # rewrite is idempotent; always return current url
    return url


def _rewrite_links_in_obj(value: Any) -> None:
    if isinstance(value, dict):
        if "url" in value and isinstance(value["url"], str):
            value["url"] = _rewrite_url(value["url"])
        for item in value.values():
            _rewrite_links_in_obj(item)
    elif isinstance(value, list):
        for item in value:
            _rewrite_links_in_obj(item)


def _fix_incident_2542(panel: dict[str, Any]) -> None:
    options = panel.setdefault("options", {})
    if not isinstance(options, dict):
        return
    # Provider Health label → Run Overview (canonical destination); drop Incident self-link.
    options["content"] = (
        '<div style="font-size:16px;line-height:1.25;padding:0;white-space:normal;'
        'overflow-wrap:anywhere">Cross-domain action: inspect dependencies in '
        '<a href="/d/bioetl-overview-v2/2-overview?${workflow:queryparam}&amp;'
        "${pipeline:queryparam}&amp;${run_type:queryparam}&amp;${run_id:queryparam}"
        '&amp;${__url_time_range}"><b>Run Overview</b></a>, rejects in '
        '<a href="/d/bioetl-dq-v2/5-data-quality?${workflow:queryparam}&amp;'
        "${pipeline:queryparam}&amp;${run_type:queryparam}&amp;${run_id:queryparam}"
        '&amp;${__url_time_range}"><b>Data Quality</b></a>, replay in '
        '<a href="/d/bioetl-control-plane-v1/1-trust?${workflow:queryparam}&amp;'
        "${pipeline:queryparam}&amp;${run_type:queryparam}&amp;${run_id:queryparam}"
        '&amp;${__url_time_range}"><b>Replay Readiness</b></a>.</div>'
    )


def _named_f13_rule(payload: dict[str, Any]) -> None:
    """Document F-13: omit var-workflow when the row workflow label is empty."""
    note = (
        " F-13 workflow rule: when the row workflow label is empty/missing, "
        "handoffs omit var-workflow (do not emit null/empty workflow)."
    )
    for panel in _walk(payload.get("panels", [])):
        if panel.get("id") not in {3010, 9101}:
            continue
        description = str(panel.get("description") or "")
        if "F-13 workflow rule" not in description:
            panel["description"] = (description + note).strip()


def apply_dashboard(path: Path, *, uid: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    _ensure_nav(payload, uid=uid)
    for panel in _walk(payload.get("panels", [])):
        if panel.get("id") == 9400:
            _move_data_links_to_panel_links(panel)
        if uid == "bioetl-incident-v1" and panel.get("id") == 2542:
            _fix_incident_2542(panel)
    _rewrite_links_in_obj(payload)
    _named_f13_rule(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    ok = True
    for item in BUS:
        uid = item["uid"]
        path = DASH_DIR / FILE_BY_UID[uid]
        before = path.read_bytes()
        payload = apply_dashboard(path, uid=uid)
        serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        after = serialized.encode("utf-8")
        if args.check:
            if before != after:
                print(f"DRIFT {path.name}")
                ok = False
            else:
                print(f"ok {path.name}")
            continue
        write_dashboard_source(path, serialized, root=ROOT)
        print(f"updated {path.name}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
