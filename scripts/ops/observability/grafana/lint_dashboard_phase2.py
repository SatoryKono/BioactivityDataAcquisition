#!/usr/bin/env python3
"""Phase-2 profile linter for provisioned BioETL Grafana dashboards (rev7 §4.5).

Checks (phase-2 profile only — not the full phase-4 set):
- viewPanel targets resolve to an existing panel id on the destination board
- navigation bus: five chips, width 19.5%, current chip is <span.bioetl-nav-current>
- indexByName values are unique within each organize transform
- text/stat threshold base step is not green (#73BF69 / green)
- link titles that name a dashboard destination match the URL uid when detectable
- no GitHub runbook URL carries Grafana query templates
- no ``/${action_path}&`` glue

Exit 0 when clean; print findings and exit 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DASH_DIR = ROOT / "grafana" / "dashboards"
FILES = (
    "bioetl-overview-v2.json",
    "bioetl-dq-v2.json",
    "bioetl-incident-v1.json",
    "bioetl-control-plane-v1.json",
    "bioetl-run-explorer-v1.json",
)
UID_BY_FILE = {
    "bioetl-overview-v2.json": "bioetl-overview-v2",
    "bioetl-dq-v2.json": "bioetl-dq-v2",
    "bioetl-incident-v1.json": "bioetl-incident-v1",
    "bioetl-control-plane-v1.json": "bioetl-control-plane-v1",
    "bioetl-run-explorer-v1.json": "bioetl-run-explorer-v1",
}
GREEN = frozenset({"green", "#73BF69", "#73bf69", "#56A64B", "#56a64b"})


def _walk(panels: list[Any]) -> list[dict[str, Any]]:
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


def _ids(panels: list[dict[str, Any]]) -> set[int]:
    result: set[int] = set()
    for panel in panels:
        panel_id = panel.get("id")
        if isinstance(panel_id, int):
            result.add(panel_id)
    return result


def _iter_urls(value: Any) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        title = str(value.get("title") or "")
        url = value.get("url")
        if isinstance(url, str) and url:
            found.append((title, url))
        for item in value.values():
            found.extend(_iter_urls(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_iter_urls(item))
    elif isinstance(value, str) and ("href=" in value or "/d/" in value):
        for match in re.finditer(r'href="([^"]+)"', value):
            found.append(("", match.group(1).replace("&amp;", "&")))
    return found


def lint_dashboard(path: Path) -> list[str]:
    findings: list[str] = []
    payload = json.loads(path.read_text(encoding="utf-8"))
    uid = str(payload.get("uid") or UID_BY_FILE.get(path.name) or "")
    panels = _walk(payload.get("panels", []))
    id_set = _ids(panels)
    id_by_uid = {
        UID_BY_FILE[name]: _ids(
            _walk(json.loads((DASH_DIR / name).read_text(encoding="utf-8")).get("panels", []))
        )
        for name in FILES
    }

    # --- nav bus ---
    nav = next((p for p in panels if p.get("id") == 1000), None)
    if nav is None:
        findings.append(f"{path.name}: missing navigation panel id=1000")
    else:
        content = str((nav.get("options") or {}).get("content") or "")
        if "bioetl-nav" not in content:
            findings.append(f"{path.name}: panel 1000 missing bioetl-nav markup")
        if content.count("19.5%") < 5:
            findings.append(
                f"{path.name}: panel 1000 expected five 19.5% chips, found "
                f"{content.count('19.5%')}"
            )
        if "16.5%" in content:
            findings.append(f"{path.name}: panel 1000 still uses legacy 16.5% chip width")
        if "<span" not in content or "bioetl-nav-current" not in content:
            findings.append(
                f"{path.name}: panel 1000 current chip must be "
                "<span class=\"bioetl-nav-current\">"
            )
        if re.search(r'<a[^>]*class="[^"]*bioetl-nav-current', content):
            findings.append(f"{path.name}: panel 1000 current chip must not be an <a>")
        for title in (
            "Run Explorer",
            "Replay Readiness",
            "Run Overview",
            "Data Quality",
            "6. Incident Workspace",
        ):
            if title not in content:
                findings.append(f"{path.name}: panel 1000 missing chip {title!r}")

    # --- organize indexByName uniqueness ---
    for panel in panels:
        for transform in panel.get("transformations") or []:
            if not isinstance(transform, dict) or transform.get("id") != "organize":
                continue
            index = (transform.get("options") or {}).get("indexByName") or {}
            if not isinstance(index, dict):
                continue
            seen: dict[Any, list[str]] = {}
            for name, position in index.items():
                seen.setdefault(position, []).append(str(name))
            for position, names in seen.items():
                if len(names) > 1:
                    findings.append(
                        f"{path.name}: panel {panel.get('id')} indexByName "
                        f"collision at {position}: {names}"
                    )

    # --- threshold base not green for text/status stats (mappings present) ---
    for panel in panels:
        if panel.get("type") != "stat":
            continue
        defaults = ((panel.get("fieldConfig") or {}).get("defaults") or {})
        mappings = defaults.get("mappings") or []
        if not mappings:
            continue  # numeric gauges may legitimately use green
        steps = (defaults.get("thresholds") or {}).get("steps") or []
        if not steps:
            continue
        base = steps[0] if isinstance(steps[0], dict) else {}
        color = str(base.get("color") or "").strip()
        if color.lower() in GREEN or color == "green":
            findings.append(
                f"{path.name}: panel {panel.get('id')} text-stat base threshold "
                f"is green ({color})"
            )

    # --- URLs ---
    for title, url in _iter_urls(payload):
        if "/${__data.fields.action_path}&" in url or "/${__data.fields.action_path}&amp;" in url:
            findings.append(f"{path.name}: action_path glued with & ({title or url[:60]})")
        if "github.com/" in url and (
            "var-" in url or "${__url_time_range}" in url or "${pipeline" in url
        ):
            findings.append(f"{path.name}: GitHub URL carries Grafana params ({url[:80]})")
        match = re.search(r"/d/([^/?#]+)/[^?]*(?:[?&]viewPanel=(\d+))", url)
        if match:
            dest_uid, view_panel = match.group(1), int(match.group(2))
            if dest_uid.startswith("${"):
                continue
            dest_ids = id_by_uid.get(dest_uid)
            if dest_ids is None and dest_uid in {u for u in id_by_uid}:
                dest_ids = id_by_uid[dest_uid]
            # Map filename-style
            for file_name, file_uid in UID_BY_FILE.items():
                if file_uid == dest_uid:
                    dest_ids = id_by_uid[file_uid]
                    break
            if dest_ids is not None and view_panel not in dest_ids:
                findings.append(
                    f"{path.name}: broken viewPanel={view_panel} on {dest_uid} "
                    f"(title={title!r})"
                )
        # title/destination soft check for Provider Health mislabel
        if title and "Provider Health" in title and "bioetl-overview-v2" in url:
            findings.append(
                f"{path.name}: link title {title!r} points at Overview — "
                "prefer Run Overview wording (F-25)"
            )

    # self-check: no viewPanel to missing local id
    for title, url in _iter_urls(payload):
        local = re.search(rf"/d/{re.escape(uid)}/[^?]*[?&]viewPanel=(\d+)", url)
        if local and int(local.group(1)) not in id_set:
            findings.append(
                f"{path.name}: local viewPanel={local.group(1)} missing (title={title!r})"
            )

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    all_findings: list[str] = []
    for name in FILES:
        path = DASH_DIR / name
        if not path.exists():
            all_findings.append(f"missing {name}")
            continue
        all_findings.extend(lint_dashboard(path))
    if all_findings:
        print("phase-2 dashboard lint FAILED:")
        for item in all_findings:
            print(f" - {item}")
        return 1
    print("phase-2 dashboard lint OK (5 dashboards)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
