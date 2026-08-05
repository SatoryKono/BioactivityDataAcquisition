#!/usr/bin/env python3
"""Render the canonical BioETL dashboard navigation bus (panel id=1000).

Generates sanitizer-safe HTML + machine-readable panel.links for every shipped
dashboard. Run from repo root:

    python scripts/ops/observability/grafana/render_nav_bus.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DASH_DIR = ROOT / "grafana" / "dashboards"

# Full portfolio bus (order is normative).
BUS: list[dict[str, str]] = [
    {
        "uid": "bioetl-control-plane-v1",
        "title": "0. Trust",
        "path": "bioetl-control-plane-v1",
    },
    {
        "uid": "bioetl-overview-v2",
        "title": "1. Overview",
        "path": "bioetl-overview-v2",
    },
    {
        "uid": "bioetl-runtime",
        "title": "2. Pipeline Diagnostics",
        "path": "bioetl-runtime",
    },
    {
        "uid": "bioetl-provider-health-v2",
        "title": "3. Provider Health",
        "path": "bioetl-provider-health-v2",
    },
    {
        "uid": "bioetl-dq-v2",
        "title": "4. Data Quality",
        "path": "bioetl-dq-v2",
    },
    {
        "uid": "bioetl-incident-v1",
        "title": "5. Incident Workspace",
        "path": "bioetl-incident-v1",
    },
    {
        "uid": "bioetl-run-explorer-v1",
        "title": "6. Run Explorer",
        "path": "bioetl-run-explorer-v1",
    },
]

FILE_BY_UID = {
    "bioetl-control-plane-v1": "bioetl-control-plane-v1.json",
    "bioetl-overview-v2": "bioetl-overview-v2.json",
    "bioetl-runtime": "bioetl-runtime.json",
    "bioetl-provider-health-v2": "bioetl-provider-health-v2.json",
    "bioetl-dq-v2": "bioetl-dq-v2.json",
    "bioetl-incident-v1": "bioetl-incident-v1.json",
    "bioetl-run-explorer-v1": "bioetl-run-explorer-v1.json",
}

CHIP_BASE = (
    "box-sizing:border-box;flex:1 1 120px;text-align:center;padding:3px 7px;"
    "border-radius:3px;font-weight:600;line-height:1.35"
)
# Theme-safe chips: slate link surface works on dark and light Grafana themes.
LINK_STYLE = (
    f"{CHIP_BASE};color:#f8fafc;background:#334155;"
    "border:1px solid #94a3b8;text-decoration:none"
)
# Current chip: blue fill + cyan border + underline (not color-only).
# Rendered as <a aria-disabled> so Grafana HTML sanitizer keeps styles
# (bare <span aria-current> may lose attributes/styles in text panels).
CURRENT_STYLE = (
    f"{CHIP_BASE};color:#ffffff;background:#1d4ed8;border:2px solid #7dd3fc;"
    "cursor:default;text-decoration:underline;pointer-events:none"
)
CONTAINER_STYLE = (
    "display:flex;gap:6px;flex-wrap:wrap;align-items:center;"
    "padding:4px 6px;overflow:visible;white-space:normal;font-size:12px"
)

NAV_DESCRIPTION = (
    "Sanitizer-compatible navigation bus with native keyboard focus. "
    "Primary bus 0–4: Trust / Overview / Pipeline Diagnostics / Provider Health / "
    "Data Quality. Adjunct 5–6: Incident Workspace / Run Explorer. "
    "Current workspace is a non-interactive chip (aria-disabled + data-current=page, "
    "underlined) so active state is not color-only. Handoffs open same-tab, "
    "preserve current time range, and document scope reset or context mapping "
    "on cross-scope transitions. Chip colors are theme-safe for dark and light."
)


def _pipeline_var(source_uid: str) -> str:
    """Provider board scopes outbound pipeline via pipeline_context."""
    if source_uid == "bioetl-provider-health-v2":
        return "$pipeline_context"
    return "$pipeline"


def _url_for(target: dict[str, str], *, source_uid: str) -> str:
    dollar = "$"
    pipe = _pipeline_var(source_uid)
    base = f"/d/{target['uid']}/{target['path']}"
    uid = target["uid"]
    if uid == "bioetl-runtime":
        # Stage is multi/includeAll on Runtime + DQ; $__all preserves all-stage
        # evidence. Literal "unknown" is not a stage label and empties panels.
        return (
            f"{base}?var-pipeline={pipe}&var-run_type={dollar}run_type"
            f"&var-stage={dollar}__all&{dollar}{{__url_time_range}}"
            f"&var-workflow={dollar}workflow&var-run_id={dollar}run_id"
        )
    if uid == "bioetl-dq-v2":
        return (
            f"{base}?var-pipeline={pipe}&var-run_type={dollar}run_type"
            f"&var-stage={dollar}__all&{dollar}{{__url_time_range}}"
            f"&var-workflow={dollar}workflow&var-run_id={dollar}run_id"
        )

    if uid == "bioetl-provider-health-v2":
        # Fail-closed context mapping from non-provider sources.
        return (
            f"{base}?var-pipeline={pipe}&var-run_type={dollar}run_type"
            f"&var-provider=unknown&var-pipeline_context={pipe}"
            f"&var-adapter=unknown&{dollar}{{__url_time_range}}"
            f"&var-workflow={dollar}workflow&var-run_id={dollar}run_id"
        )
    if uid in {"bioetl-incident-v1", "bioetl-run-explorer-v1"}:
        return (
            f"{base}?var-pipeline={pipe}&var-run_type={dollar}run_type"
            f"&{dollar}{{__url_time_range}}&var-workflow={dollar}workflow"
            f"&var-run_id={dollar}run_id"
        )
    # Trust / Overview
    return (
        f"{base}?var-pipeline={pipe}&var-run_type={dollar}run_type"
        f"&{dollar}{{__url_time_range}}&var-workflow={dollar}workflow"
        f"&var-run_id={dollar}run_id"
    )


def _html_href(url: str) -> str:
    return (
        url.replace("&", "&amp;").replace("$", "$")  # keep template vars
    )


def _chip_html(item: dict[str, str], *, current_uid: str, source_uid: str) -> str:
    short = item["title"].split(". ", 1)[-1]
    title_attr = f"{item['title']} ({short})"
    if item["uid"] == current_uid:
        # Anchor keeps inline styles under Grafana sanitizer; not in tab order.
        return (
            f'<a class="bioetl-nav-current" href="#{item["uid"]}" '
            f'aria-disabled="true" aria-current="page" data-current="page" '
            f'tabindex="-1" title="{title_attr}" style="{CURRENT_STYLE}">'
            f"{item['title']} (current)</a>"
        )
    href = _html_href(_url_for(item, source_uid=source_uid))
    return (
        f'<a class="bioetl-nav-link" style="{LINK_STYLE}" title="{title_attr}" '
        f'href="{href}">{item["title"]}</a>'
    )


def render_html(*, current_uid: str) -> str:
    """Single bioetl-nav container; primary 0–4 then full-width break then adjunct 5–6."""
    primary = BUS[:5]
    adjunct = BUS[5:]
    parts: list[str] = [
        f'<div class="bioetl-nav" role="navigation" '
        f'aria-label="BioETL dashboards" style="{CONTAINER_STYLE}">'
    ]
    for item in primary:
        parts.append(_chip_html(item, current_uid=current_uid, source_uid=current_uid))
    # Force second row for adjunct workspaces (readability at 1024px).
    parts.append(
        '<span style="flex:1 1 100%;height:0;overflow:hidden;margin:0;padding:0;'
        'border:0" aria-hidden="true"></span>'
    )
    for item in adjunct:
        parts.append(_chip_html(item, current_uid=current_uid, source_uid=current_uid))
    parts.append("</div>")
    return "".join(parts)


def render_links(*, current_uid: str) -> list[dict[str, object]]:
    links: list[dict[str, object]] = []
    for item in BUS:
        if item["uid"] == current_uid:
            continue
        links.append(
            {
                "title": item["title"],
                "url": _url_for(item, source_uid=current_uid),
                "type": "link",
                "icon": "dashboard",
                "targetBlank": False,
                "keepTime": False,
                "includeVars": False,
                "asDropdown": False,
                "tags": [],
            }
        )
    return links


def apply_to_dashboard(path: Path, *, current_uid: str) -> None:
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    safe_path = ensure_path_within_root(path, DASH_DIR)
    payload = json.loads(
        safe_path.read_text(encoding="utf-8")  # NOSONAR - confined under DASH_DIR
    )
    panels = payload.get("panels") or []
    nav = next((p for p in panels if p.get("id") == 1000), None)
    if nav is None:
        raise SystemExit(f"{safe_path.name}: missing panel id=1000")

    nav["title"] = "Navigation"
    nav["type"] = "text"
    nav["description"] = NAV_DESCRIPTION
    nav.setdefault("gridPos", {})
    nav["gridPos"].update({"h": 3, "w": 24, "x": 0, "y": 0})
    nav["options"] = {
        "mode": "html",
        "content": render_html(current_uid=current_uid),
    }
    nav["links"] = render_links(current_uid=current_uid)
    # Drop stale transparent fields that confuse some exporters.
    nav.pop("transparent", None)

    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    write_path = ensure_path_within_root(safe_path, DASH_DIR)
    write_path.write_text(  # NOSONAR - write_path confined under DASH_DIR
        serialized,
        encoding="utf-8",
    )


def main() -> None:
    from scripts.engineering.common.repo_paths import ensure_path_within_root

    for item in BUS:
        uid = item["uid"]
        filename = FILE_BY_UID[uid]
        path = ensure_path_within_root(DASH_DIR / filename, DASH_DIR)
        if not path.exists():
            raise SystemExit(f"missing dashboard file: {path}")
        apply_to_dashboard(path, current_uid=uid)
        print(f"updated {filename} current={item['title']!r}")


if __name__ == "__main__":
    main()
