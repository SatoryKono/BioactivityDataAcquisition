#!/usr/bin/env python3
"""Apply Grafana Phase 4.2–4.3 layout reflow (rev7 §4.2 / §4.3).

- Incident collapsed row 8808: fill each y-band so panel widths sum to 24
  (F-24). Keeps existing 1–3 panel groupings; expands widths in place.
- Incident panel 9451: height 12 → 8 at limitField 6 (F-30 / residual №10).
- Documents the width-fill rule on the 8808 row description.

Does not start Docker, touch ``.env``, or inflate tech-debt budgets.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"
INCIDENT = DASH / "bioetl-incident-v1.json"
FLEET_ROW_ID = 8808
DOMAINS_PANEL_ID = 9451
TARGET_WIDTH = 24
DOMAINS_HEIGHT = 8

_ROW_DESCRIPTION = (
    "Pipeline fleet and range diagnostics (not this Run ID). "
    "Collapsed forensic shell: panels keep 1–3 per y-band; each band's "
    "gridPos widths sum to 24 (rev7 §4.2 / F-24). Domain table 9451 uses "
    f"h={DOMAINS_HEIGHT} at limitField 6 (rev7 §4.3)."
)


def _walk(panels: list[Any] | None):
    for panel in panels or []:
        if isinstance(panel, dict):
            yield panel
            nested = panel.get("panels")
            if isinstance(nested, list):
                yield from _walk(nested)


def _by_id(data: dict[str, Any], panel_id: int) -> dict[str, Any]:
    for panel in _walk(data.get("panels")):
        if panel.get("id") == panel_id:
            return panel
    raise KeyError(panel_id)


def _ordered_band(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[int]]:
    ordered = sorted(items, key=lambda p: int((p.get("gridPos") or {}).get("x") or 0))
    widths = [max(1, int((p.get("gridPos") or {}).get("w") or 1)) for p in ordered]
    return ordered, widths


def _apply_widths(ordered: list[dict[str, Any]], widths: list[int]) -> bool:
    """Write packed ``x``/``w`` values; return whether any panel changed."""
    changed = False
    cursor = 0
    for panel, width in zip(ordered, widths, strict=True):
        gp = panel.setdefault("gridPos", {})
        if gp.get("x") != cursor or gp.get("w") != width:
            gp["x"] = cursor
            gp["w"] = width
            changed = True
        cursor += width
    return changed


def _scaled_widths(widths: list[int]) -> list[int]:
    """Proportionally expand ``widths`` so they sum to ``TARGET_WIDTH``."""
    if len(widths) == 1:
        return [TARGET_WIDTH]
    total = sum(widths)
    scaled = [max(1, round(width * TARGET_WIDTH / total)) for width in widths]
    drift = TARGET_WIDTH - sum(scaled)
    scaled[-1] = max(1, scaled[-1] + drift)
    while sum(scaled) > TARGET_WIDTH and scaled[-1] > 1:
        scaled[-1] -= 1
    while sum(scaled) < TARGET_WIDTH:
        scaled[-1] += 1
    return scaled


def _redistribute_widths(items: list[dict[str, Any]]) -> bool:
    """Scale/fill ``gridPos.w`` so the band sums to 24. Returns True if changed."""
    if not items:
        return False
    ordered, widths = _ordered_band(items)
    if sum(widths) == TARGET_WIDTH:
        return _apply_widths(ordered, widths)
    return _apply_widths(ordered, _scaled_widths(widths))


def reflow_fleet_row(row: dict[str, Any]) -> int:
    """Reflow collapsed 8808 children; return number of y-bands adjusted."""
    children = [p for p in (row.get("panels") or []) if isinstance(p, dict)]
    by_y: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for panel in children:
        y = int((panel.get("gridPos") or {}).get("y") or 0)
        by_y[y].append(panel)
    adjusted = 0
    for y in sorted(by_y):
        if _redistribute_widths(by_y[y]):
            adjusted += 1
    row["description"] = _ROW_DESCRIPTION
    return adjusted


def apply_incident(data: dict[str, Any]) -> dict[str, int]:
    row = _by_id(data, FLEET_ROW_ID)
    bands = reflow_fleet_row(row)
    domains = _by_id(data, DOMAINS_PANEL_ID)
    height_before = int((domains.get("gridPos") or {}).get("h") or 0)
    domains.setdefault("gridPos", {})["h"] = DOMAINS_HEIGHT
    return {
        "fleet_bands_adjusted": bands,
        "domains_height_before": height_before,
        "domains_height_after": DOMAINS_HEIGHT,
    }


def incomplete_bands(data: dict[str, Any]) -> list[tuple[int, int]]:
    row = _by_id(data, FLEET_ROW_ID)
    by_y: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for panel in row.get("panels") or []:
        if isinstance(panel, dict):
            y = int((panel.get("gridPos") or {}).get("y") or 0)
            by_y[y].append(panel)
    out: list[tuple[int, int]] = []
    for y in sorted(by_y):
        width = sum(int((p.get("gridPos") or {}).get("w") or 0) for p in by_y[y])
        if width != TARGET_WIDTH:
            out.append((y, width))
    return out


def main() -> int:
    data = json.loads(INCIDENT.read_text(encoding="utf-8"))
    before = incomplete_bands(data)
    stats = apply_incident(data)
    after = incomplete_bands(data)
    INCIDENT.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Phase 4.2/4.3 Incident reflow")
    print(f"  incomplete bands before: {len(before)} {before[:8]}...")
    print(f"  stats: {stats}")
    print(f"  incomplete bands after: {len(after)} {after}")
    return 0 if not after else 1


if __name__ == "__main__":
    raise SystemExit(main())
