"""Dashboard PromQL metric probes extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import re
from pathlib import Path

from memory.graph.sync_pkg._core_convert import _read_text
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.mapping_io import _read_json

__all__ = [
    "BIOETL_METRIC_PATTERN",
    "_dashboard_metric_index",
    "_dashboard_metrics_from_payload",
    "_dashboard_panel_stack",
    "_dashboard_panel_target_metrics",
    "_extract_bioetl_metrics",
    "_nested_dashboard_panels",
    "_path_contains_any_token",
]

BIOETL_METRIC_PATTERN = re.compile(r"\bbioetl_[a-zA-Z0-9_:]+")


def _path_contains_any_token(path: Path, tokens: list[str]) -> bool:
    normalized = _read_text(path).lower()
    return any(token.lower() in normalized for token in tokens)


def _extract_bioetl_metrics(text: str) -> set[str]:
    return set(BIOETL_METRIC_PATTERN.findall(text))


def _dashboard_metric_index(root: Path) -> dict[NodeKey, set[str]]:
    dashboards_root = root / "grafana" / "dashboards"
    if not dashboards_root.is_dir():
        return {}
    metric_index: dict[NodeKey, set[str]] = {}
    for dashboard_path in sorted(dashboards_root.glob("*.json")):
        try:
            payload = _read_json(dashboard_path)
        except Exception:
            # Snapshot building should stay resilient to malformed or
            # partially edited dashboard files.
            payload = {}
        metrics = _dashboard_metrics_from_payload(payload)
        metric_index[NodeKey("dashboard_surface", dashboard_path.stem)] = metrics
    return metric_index


def _dashboard_metrics_from_payload(payload: dict[str, object]) -> set[str]:
    metrics: set[str] = set()
    stack = _dashboard_panel_stack(payload)
    while stack:
        panel = stack.pop()
        if not isinstance(panel, dict):
            continue
        stack.extend(_nested_dashboard_panels(panel))
        metrics.update(_dashboard_panel_target_metrics(panel))
    return metrics


def _dashboard_panel_stack(payload: dict[str, object]) -> list[object]:
    panels = payload.get("panels")
    return list(panels) if isinstance(panels, list) else []


def _nested_dashboard_panels(panel: dict[str, object]) -> list[object]:
    nested = panel.get("panels")
    return list(nested) if isinstance(nested, list) else []


def _dashboard_panel_target_metrics(panel: dict[str, object]) -> set[str]:
    targets = panel.get("targets")
    if not isinstance(targets, list):
        return set()
    metrics: set[str] = set()
    for target in targets:
        if not isinstance(target, dict):
            continue
        expr = target.get("expr")
        if isinstance(expr, str):
            metrics.update(_extract_bioetl_metrics(expr))
    return metrics
