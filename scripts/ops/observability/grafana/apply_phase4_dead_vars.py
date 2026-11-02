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

FILE_OVERVIEW = "bioetl-overview-v2.json"
FILE_DQ = "bioetl-dq-v2.json"
FILE_INCIDENT = "bioetl-incident-v1.json"
FILE_CONTROL_PLANE = "bioetl-control-plane-v1.json"
FILE_RUN_EXPLORER = "bioetl-run-explorer-v1.json"
FILES = (
    FILE_OVERVIEW,
    FILE_DQ,
    FILE_INCIDENT,
    FILE_CONTROL_PLANE,
    FILE_RUN_EXPLORER,
)

DEAD_EVERYWHERE = frozenset({"provider_for_pipeline"})
DEAD_BY_FILE = {
    FILE_DQ: frozenset({"stage"}),
    FILE_CONTROL_PLANE: frozenset({"read_latency_quantile"}),
}
DROP_PIPELINE_UNKNOWN_ON = frozenset({FILE_DQ, FILE_INCIDENT, FILE_CONTROL_PLANE})
_PIPELINE = "pipeline"
_UNKNOWN = "unknown"
_REPEAT_KEYS = ("repeat", "repeatDirection", "maxPerRow")


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


def _clean_pipeline_unknown_options(var: dict[str, Any]) -> bool:
    options = var.get("options")
    if not isinstance(options, list):
        return False
    cleaned = [
        opt
        for opt in options
        if not (isinstance(opt, dict) and str(opt.get("value") or "") == _UNKNOWN)
    ]
    if len(cleaned) == len(options):
        return False
    var["options"] = cleaned
    return True


def _should_drop_var(name: str, *, path_name: str) -> bool:
    return name in DEAD_EVERYWHERE or name in DEAD_BY_FILE.get(path_name, ())


def _drop_dead_vars(data: dict[str, Any], *, path_name: str) -> list[str]:
    templating = data.setdefault("templating", {})
    variables = templating.get("list")
    if not isinstance(variables, list):
        return []
    kept: list[Any] = []
    removed: list[str] = []
    drop_unknown = path_name in DROP_PIPELINE_UNKNOWN_ON
    for var in variables:
        if not isinstance(var, dict):
            kept.append(var)
            continue
        name = str(var.get("name") or "")
        if _should_drop_var(name, path_name=path_name):
            removed.append(name)
            continue
        if drop_unknown and name == _PIPELINE and _clean_pipeline_unknown_options(var):
            removed.append("pipeline.options[unknown]")
        kept.append(var)
    templating["list"] = kept
    return removed


def _defined_variable_names(data: dict[str, Any]) -> set[str]:
    return {
        str(var.get("name") or "")
        for var in (data.get("templating") or {}).get("list") or []
        if isinstance(var, dict)
    }


def _clear_panel_repeat(panel: dict[str, Any], *, defined: set[str]) -> str | None:
    repeat = panel.get("repeat")
    if not isinstance(repeat, str) or not repeat or repeat in defined:
        return None
    for key in _REPEAT_KEYS:
        panel.pop(key, None)
    return f"panel:{panel.get('id')}:repeat={repeat}"


def _clear_dangling_repeats(data: dict[str, Any]) -> list[str]:
    """Clear ``repeat`` when the target variable is no longer defined."""
    defined = _defined_variable_names(data)
    cleared: list[str] = []
    for panel in _walk(data.get("panels", [])):
        note = _clear_panel_repeat(panel, defined=defined)
        if note is not None:
            cleared.append(note)
    return cleared


def _resolve_dashboard_path(path: Path, *, dashboard_root: Path) -> Path:
    """Allow only known dashboard basenames under ``dashboard_root``."""
    root = dashboard_root.resolve()
    name = path.name
    if name not in FILES:
        raise ValueError(f"refusing unexpected dashboard file: {name}")
    target = (root / name).resolve()
    if target.parent != root:
        raise ValueError(f"refusing path outside {root}: {path}")
    return target


def apply_file(
    path: Path, *, dashboard_root: Path | None = None
) -> tuple[list[str], list[str]]:
    target = _resolve_dashboard_path(path, dashboard_root=dashboard_root or DASH)
    data = json.loads(target.read_text(encoding="utf-8"))
    removed = _drop_dead_vars(data, path_name=target.name)
    cleared = _clear_dangling_repeats(data)
    target.write_text(
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
