#!/usr/bin/env python3
"""Apply Grafana Phase 4.1 dead-variable cleanup (rev7 §4.1 / F-20…F-23).

Removes unused templating variables and dangling ``repeat`` bindings from the
five provisioned BioETL dashboards. Keeps ``read_latency_quantile`` on Incident
(still referenced by PromQL). Safe to re-run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana" / "dashboards"
FILES = (
    "bioetl-overview-v2.json",
    "bioetl-dq-v2.json",
    "bioetl-incident-v1.json",
    "bioetl-control-plane-v1.json",
    "bioetl-run-explorer-v1.json",
)

# Always dead across the five-board set (no $refs).
DEAD_EVERYWHERE = frozenset({"provider_for_pipeline"})
# Dead only where defined without $refs.
DEAD_BY_FILE = {
    "bioetl-dq-v2.json": frozenset({"stage"}),
    "bioetl-control-plane-v1.json": frozenset({"read_latency_quantile"}),
}
# Drop legacy static option left after HTTP options migration.
DROP_PIPELINE_UNKNOWN_ON = frozenset(
    {
        "bioetl-dq-v2.json",
        "bioetl-incident-v1.json",
        "bioetl-control-plane-v1.json",
    }
)


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


def _drop_dead_vars(data: dict[str, Any], *, path_name: str) -> list[str]:
    templating = data.setdefault("templating", {})
    variables = templating.get("list")
    if not isinstance(variables, list):
        return []
    drop = set(DEAD_EVERYWHERE) | set(DEAD_BY_FILE.get(path_name, ()))
    kept: list[Any] = []
    removed: list[str] = []
    for var in variables:
        if not isinstance(var, dict):
            kept.append(var)
            continue
        name = str(var.get("name") or "")
        if name in drop:
            removed.append(name)
            continue
        if path_name in DROP_PIPELINE_UNKNOWN_ON and name == "pipeline":
            options = var.get("options")
            if isinstance(options, list):
                cleaned = [
                    opt
                    for opt in options
                    if not (
                        isinstance(opt, dict)
                        and str(opt.get("value") or "") == "unknown"
                    )
                ]
                if len(cleaned) != len(options):
                    var["options"] = cleaned
                    removed.append("pipeline.options[unknown]")
        kept.append(var)
    templating["list"] = kept
    return removed


def _clear_dangling_repeats(data: dict[str, Any]) -> list[str]:
    """Clear ``repeat`` when the target variable is no longer defined."""
    defined = {
        str(var.get("name") or "")
        for var in (data.get("templating") or {}).get("list") or []
        if isinstance(var, dict)
    }
    cleared: list[str] = []
    for panel in _walk(data.get("panels", [])):
        repeat = panel.get("repeat")
        if not isinstance(repeat, str) or not repeat or repeat in defined:
            continue
        panel_id = panel.get("id")
        cleared.append(f"panel:{panel_id}:repeat={repeat}")
        panel.pop("repeat", None)
        panel.pop("repeatDirection", None)
        panel.pop("maxPerRow", None)
    return cleared


def apply_file(path: Path) -> tuple[list[str], list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    removed = _drop_dead_vars(data, path_name=path.name)
    cleared = _clear_dangling_repeats(data)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return removed, cleared


def main() -> int:
    print("Phase 4.1 dead-variable cleanup")
    for name in FILES:
        path = DASH / name
        if not path.exists():
            print(f"  missing {name}")
            continue
        removed, cleared = apply_file(path)
        print(f"  {name}: removed={removed or '-'} cleared_repeats={cleared or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
