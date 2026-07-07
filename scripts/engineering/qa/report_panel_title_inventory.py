#!/usr/bin/env python3
"""Regenerate docs/03-guides/dashboards/panel-title-inventory.md from shipped JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DASHBOARDS_DIR = ROOT / "grafana" / "dashboards"
DEFAULT_OUTPUT = ROOT / "docs" / "03-guides" / "dashboards" / "panel-title-inventory.md"

HEADER = """# Panel Title Inventory

Generated from `grafana/dashboards/*.json`.

## KPI ownership contract anchors

Machine-readable SSOT: `docs/03-guides/dashboards/contracts/navigation-links.yaml` (`kpi_ownership`).

| KPI key | Canonical UID | Mirror panel(s) |
|---|---|---|
| `failed_runs_in_range` | `bioetl-overview-v2` | `bioetl-runtime#205` |
| `worst_lag_stage` | `bioetl-overview-v2` | `bioetl-runtime#237` |
| `worst_backlog_stage` | `bioetl-overview-v2` | `bioetl-runtime#238` |

| Dashboard | Panel ID | Title |
| --- | ---: | --- |
"""


def _iter_panels(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    stack = list(panels)
    while stack:
        panel = stack.pop(0)
        if not isinstance(panel, dict):
            continue
        discovered.append(panel)
        nested = panel.get("panels", [])
        if isinstance(nested, list):
            stack[0:0] = [item for item in nested if isinstance(item, dict)]
    return discovered


def _collect_rows() -> list[str]:
    rows: list[str] = []
    for path in sorted(DASHBOARDS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for panel in _iter_panels(list(payload.get("panels", []))):
            panel_id = panel.get("id")
            title = panel.get("title")
            if panel_id is None or not title:
                continue
            rows.append(f"| {path.name} | {panel_id} | {title} |")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Markdown output path (default: docs panel-title-inventory.md)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when output would change",
    )
    args = parser.parse_args(argv)

    rows = _collect_rows()
    content = HEADER + "\n".join(rows) + "\n"

    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if current != content:
            print(f"panel-title-inventory drift: {args.output}", file=sys.stderr)
            return 1
        print(f"panel-title-inventory OK ({len(rows)} rows)")
        return 0

    args.output.write_text(content, encoding="utf-8")
    print(f"wrote {len(rows)} panel rows -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
