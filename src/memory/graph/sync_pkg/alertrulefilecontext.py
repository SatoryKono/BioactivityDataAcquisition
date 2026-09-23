"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.alert_rule_file_payload import (
    _add_alert_rules_artifact,
    _alert_rule_file_payload,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "AlertRuleFileContext",
    "_alert_rule_file_context",
]


@dataclass(frozen=True)
class AlertRuleFileContext:
    payload: dict[str, object]
    artifact: NodeKey


def _alert_rule_file_context(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    rules_path: Path,
) -> AlertRuleFileContext:
    return AlertRuleFileContext(
        payload=_alert_rule_file_payload(rules_path),
        artifact=_add_alert_rules_artifact(snapshot, root, rules_path, today),
    )
