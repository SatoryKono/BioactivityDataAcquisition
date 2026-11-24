"""Explicit target-table contract transitions. Main tables stay put."""

from __future__ import annotations

from collections.abc import Mapping

SUPPORTED_TRANSITIONS = frozenset(
    {
        ("3.0.0", "3.1.0"),
        ("3.1.0", "3.0.0"),
        ("3.0.0", "3.2.0"),
        ("3.2.0", "3.0.0"),
        ("3.1.0", "3.2.0"),
        ("3.2.0", "3.1.0"),
    }
)


def plan_target_contract_transition(source: str, destination: str) -> dict[str, str]:
    """Record a supported pair. This planner does not switch live tables."""
    if (source, destination) not in SUPPORTED_TRANSITIONS:
        raise ValueError("unsupported target contract transition")
    return {
        "source_contract": source,
        "destination_contract": destination,
        "main_tables": "unchanged",
    }


def assert_live_promotion_allowed(plan: Mapping[str, object]) -> None:
    """Keep 3.2.0 off the live contour until every gate is explicit.

    Plans without ``table_contract`` keep the existing V31 promotion path.
    Biological acceptance is never inferred from a class-match count.
    """
    if plan.get("table_contract") != "3.2.0":
        return
    required = (
        "rehearsal_rollback_passed",
        "fk_closure",
        "biological_accuracy_accepted",
        "live_promotion",
    )
    if any(plan.get(key) is not True for key in required):
        raise ValueError("live 3.2.0 target promotion is refused")


__all__ = [
    "SUPPORTED_TRANSITIONS",
    "assert_live_promotion_allowed",
    "plan_target_contract_transition",
]
