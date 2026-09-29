"""Bind the shipped panel inventory in dashboard guides to dashboard JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DASHBOARDS = ROOT / "grafana" / "dashboards"
GUIDES = ROOT / "docs" / "03-guides" / "dashboards" / "panels"
BEGIN = "<!-- BEGIN SHIPPED PANEL INVENTORY -->"
END = "<!-- END SHIPPED PANEL INVENTORY -->"


def _panels(items: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result.append(item)
        nested = item.get("panels")
        if isinstance(nested, list):
            result.extend(_panels(nested))
    return result


def _display_title(panel: dict[str, Any]) -> str:
    options = panel.get("options")
    if isinstance(options, dict):
        custom = options.get("bioetlDisplayTitle")
        if isinstance(custom, str) and custom.strip():
            return custom.strip()
    title = panel.get("title")
    return title.strip() if isinstance(title, str) else ""


def _inventory(dashboard: Path) -> str:
    payload = json.loads(dashboard.read_text(encoding="utf-8"))
    rows = [
        "## Current shipped panel inventory",
        "",
        "Generated from the dashboard JSON. Earlier sections explain panel semantics; "
        "this table identifies the panels shipped in the current dashboard.",
        "",
        "| ID | Title | Type |",
        "| --- | --- | --- |",
    ]
    for panel in _panels(payload.get("panels", [])):
        if panel.get("id") == 1000:
            continue
        title = _display_title(panel)
        if not title:
            continue
        panel_id = panel.get("id")
        if not isinstance(panel_id, int):
            raise ValueError(f"{dashboard}: panel title without numeric ID: {title}")
        kind = panel.get("type")
        kind = kind if isinstance(kind, str) else "unknown"
        rows.append(f"| {panel_id} | {title} | {kind} |")
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale: list[Path] = []
    for dashboard in sorted(DASHBOARDS.glob("*.json")):
        guide = GUIDES / f"{dashboard.stem}-panels.md"
        if not guide.is_file():
            raise FileNotFoundError(guide)
        content = guide.read_text(encoding="utf-8")
        if (BEGIN in content) != (END in content):
            raise ValueError(f"unpaired inventory markers: {guide}")
        block = f"{BEGIN}\n{_inventory(dashboard)}{END}"
        if BEGIN in content:
            prefix, rest = content.split(BEGIN, 1)
            _, suffix = rest.split(END, 1)
            updated = f"{prefix}{block}{suffix}"
        else:
            updated = content.rstrip() + "\n\n" + block + "\n"
        if updated != content:
            stale.append(guide)
            if not args.check:
                guide.write_text(updated, encoding="utf-8", newline="\n")
    if stale:
        print("stale panel inventories: " + ", ".join(str(path) for path in stale))
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
