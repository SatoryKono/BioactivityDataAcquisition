"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import AlertRuleContext
from memory.graph.sync_pkg.alert_annotations import _alert_annotations, _alert_labels

__all__ = [
    "_alert_rule_context",
]


def _alert_rule_context(rule: dict[str, object]) -> AlertRuleContext | None:
    alert_name = rule.get("alert")
    if not isinstance(alert_name, str):
        return None
    return AlertRuleContext(
        alert_name=alert_name,
        annotations=_alert_annotations(rule),
        labels=_alert_labels(rule),
    )
