#!/usr/bin/env python3
"""Apply Grafana Phase 4.1 dead-variable cleanup (rev7 §4.1 / F-20…F-23).

Removes unused templating variables and dangling ``repeat`` bindings from the
five provisioned BioETL dashboards. Keeps ``read_latency_quantile`` on Incident
(still referenced by PromQL). Safe to re-run.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
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
# selected_* are A2 helpers used on Overview/DQ targets; unused on the other three.
_DEAD_SELECTED = frozenset({"selected_run_id", "selected_pipeline"})
DEAD_BY_FILE = {
    FILE_DQ: frozenset({"stage"}),
    FILE_CONTROL_PLANE: frozenset({"read_latency_quantile"}) | _DEAD_SELECTED,
    FILE_INCIDENT: frozenset(_DEAD_SELECTED),
    FILE_RUN_EXPLORER: frozenset(_DEAD_SELECTED),
}
DROP_PIPELINE_UNKNOWN_ON = frozenset({FILE_DQ, FILE_INCIDENT, FILE_CONTROL_PLANE})
_PIPELINE = "pipeline"
_UNKNOWN = "unknown"
_REPEAT_KEYS = ("repeat", "repeatDirection", "maxPerRow")
# Phase 4.4: shared timepicker surface across the five provisioned boards.
_REFRESH_INTERVALS = (
    "5s",
    "10s",
    "30s",
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "1d",
)


def _iter_panels(panels: list[Any] | None) -> Iterator[dict[str, Any]]:
    """Depth-first yield of dict panels (including nested row children)."""
    for panel in panels or []:
        if not isinstance(panel, dict):
            continue
        yield panel
        nested = panel.get("panels")
        if isinstance(nested, list):
            yield from _iter_panels(nested)


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
    for panel in _iter_panels(data.get("panels")):
        note = _clear_panel_repeat(panel, defined=defined)
        if note is not None:
            cleared.append(note)
    return cleared


def _prune_organize_rename(transform: dict[str, Any]) -> int:
    """Prune one organize transform; return number of dropped rename keys."""
    if transform.get("id") != "organize":
        return 0
    options = transform.setdefault("options", {})
    index = options.get("indexByName")
    rename = options.get("renameByName")
    if not isinstance(index, dict) or not isinstance(rename, dict) or not index:
        return 0
    keep = {key: value for key, value in rename.items() if key in index}
    dropped = len(rename) - len(keep)
    if dropped:
        options["renameByName"] = keep
    return dropped


def _prune_dead_renames(data: dict[str, Any]) -> int:
    """Drop ``renameByName`` keys absent from the same organize ``indexByName``."""
    pruned = 0
    for panel in _iter_panels(data.get("panels")):
        for transform in panel.get("transformations") or []:
            if isinstance(transform, dict):
                pruned += _prune_organize_rename(transform)
    return pruned


def _ensure_timepicker(data: dict[str, Any]) -> bool:
    """Align ``timepicker.refresh_intervals`` to the shared Phase 4.4 list."""
    timepicker = data.setdefault("timepicker", {})
    if not isinstance(timepicker, dict):
        data["timepicker"] = {"refresh_intervals": list(_REFRESH_INTERVALS)}
        return True
    current = timepicker.get("refresh_intervals")
    desired = list(_REFRESH_INTERVALS)
    if current == desired:
        return False
    timepicker["refresh_intervals"] = desired
    return True


def apply_dashboard_data(
    data: dict[str, Any], *, path_name: str
) -> tuple[list[str], list[str]]:
    """Mutate dashboard JSON in memory. No filesystem I/O (S2083-safe)."""
    if path_name not in FILES:
        raise ValueError(f"refusing unexpected dashboard file: {path_name}")
    removed = _drop_dead_vars(data, path_name=path_name)
    cleared = _clear_dangling_repeats(data)
    pruned = _prune_dead_renames(data)
    if pruned:
        cleared.append(f"renameByName:pruned={pruned}")
    if _ensure_timepicker(data):
        cleared.append("timepicker.refresh_intervals")
    return removed, cleared


# Literal (path, basename) pairs — paths are never built from a function argument
# so pythonsecurity:S2083 cannot treat write targets as tainted joins.
_DASHBOARD_TARGETS: tuple[tuple[Path, str], ...] = (
    (DASH / FILE_OVERVIEW, FILE_OVERVIEW),
    (DASH / FILE_DQ, FILE_DQ),
    (DASH / FILE_INCIDENT, FILE_INCIDENT),
    (DASH / FILE_CONTROL_PLANE, FILE_CONTROL_PLANE),
    (DASH / FILE_RUN_EXPLORER, FILE_RUN_EXPLORER),
)


def _write_dashboard(target: Path, data: dict[str, Any]) -> None:
    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    print("Phase 4.1 dead-variable cleanup")
    for target, path_name in _DASHBOARD_TARGETS:
        if not target.exists():
            print(f"  missing {path_name}")
            continue
        data = json.loads(target.read_text(encoding="utf-8"))
        removed, cleared = apply_dashboard_data(data, path_name=path_name)
        _write_dashboard(target, data)
        print(
            f"  {path_name}: removed={removed or '-'} cleared_repeats={cleared or '-'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
