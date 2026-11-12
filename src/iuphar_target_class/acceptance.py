"""Acceptance report. A check is PASS only when this run executed it."""

from __future__ import annotations

from collections.abc import Mapping

from .policy import PLAN_VERSION
from .w153 import INTEGRATION_REASON

NOT_RUN_REASONS: dict[str, str] = {
    "api_smoke": "сохранённых ответов API нет",
    "gold_cases": "эталонные случаи не подтверждены",
    "graph_limits_boundary": (
        "graph_limits.max_depth и graph_limits.max_visited_nodes не утверждены"
    ),
    "http_transport": "HTTP timeouts, retries и backoff не утверждены",
    "isoform_policy": "политика изоформ не утверждена",
    "missing_markers_version": "версия missing_markers не утверждена",
    "quality_counts": "эталонный набор этапа 0 пуст, числа качества не измерены",
    "real_data": "происхождение IUPHAR на этапе 0 не установлено",
    "snapshot_coverage": "охват и набор видов снимка не утверждены",
    "volume_scenario": "volume_test_seconds не утверждено",
    "w153_integration": INTEGRATION_REASON,
}


def build_acceptance_report(executed: Mapping[str, str]) -> dict[str, object]:
    """Merge executed results with the checks that cannot be marked PASS."""
    names = set(executed) | set(NOT_RUN_REASONS)
    checks: list[dict[str, str]] = []
    for name in sorted(names):
        if name in NOT_RUN_REASONS:
            checks.append(
                {"name": name, "reason": NOT_RUN_REASONS[name], "status": "NOT_RUN"}
            )
            continue
        status = executed[name]
        if status not in {"PASS", "FAIL"}:
            status = "NOT_RUN"
        checks.append({"name": name, "reason": "", "status": status})
    return {
        "biological_accuracy_accepted": False,
        "checks": checks,
        "mapping_version": None,
        "rules_version": PLAN_VERSION,
        "schema_version": None,
        "snapshot_coverage": "не утверждено",
        "snapshot_id": None,
        "statement": (
            "Без проверенных данных разработка на синтетических fixtures допустима, "
            "биологическая точность не принимается."
        ),
    }
