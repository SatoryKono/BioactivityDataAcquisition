"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import AlertRuleGroupContext

__all__ = [
    "_alert_group_name",
    "_alert_group_rules",
    "_alert_rule_group_context",
]


def _alert_group_name(group: dict[str, object], rules_path: Path) -> str:
    return str(group.get("name", rules_path.stem))


def _alert_group_rules(group: dict[str, object]) -> tuple[dict[str, object], ...]:
    rules = group.get("rules")
    if not isinstance(rules, list):
        return ()
    return tuple(rule for rule in rules if isinstance(rule, dict))


def _alert_rule_group_context(
    group: dict[str, object],
    rules_path: Path,
) -> AlertRuleGroupContext:
    return AlertRuleGroupContext(
        group_name=_alert_group_name(group, rules_path),
        rules=_alert_group_rules(group),
    )
