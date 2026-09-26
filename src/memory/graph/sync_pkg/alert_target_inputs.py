"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import AlertTargetInputs
from memory.graph.sync_pkg.alert_annotations import (
    _alert_annotations,
    _alert_dimension_text,
)
from memory.graph.sync_pkg.alert_targets import _runtime_dimensions

__all__ = [
    "_alert_target_inputs",
]


def _alert_target_inputs(rule: dict[str, object]) -> tuple[str, set[str]]:
    annotations = _alert_annotations(rule)
    expr = str(rule.get("expr", ""))
    context = AlertTargetInputs(
        expr=expr,
        dimensions=_runtime_dimensions(expr, _alert_dimension_text(annotations)),
    )
    return context.expr, context.dimensions
