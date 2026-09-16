"""Bounded per-execution observations shared by child tasks, isolated between runs."""

from __future__ import annotations

from contextvars import ContextVar, Token
from copy import deepcopy

from bioetl.domain.value_objects.dq_result import DQResult

_observations: ContextVar[dict[str, object] | None] = ContextVar(
    "run_observations", default=None
)


def bind_run_observations() -> Token[dict[str, object] | None]:
    """Start a fresh evidence scope before runner construction."""
    return _observations.set({})


def reset_run_observations(token: Token[dict[str, object] | None]) -> None:
    """Restore the caller scope even after cancellation or construction failure."""
    _observations.reset(token)


def record_run_observation(
    domain: str,
    *,
    verdict: str,
    reason: str,
    facts: dict[str, object],
    replace_provisional: bool = False,
) -> None:
    """Record an actual executed check, including negative and measured-zero results."""
    target = _observations.get()
    if target is not None:
        previous = target.get(domain)
        priority = {
            "ERROR": 5,
            "INCOMPLETE": 4,
            "UNKNOWN": 3,
            "WARN": 2,
            "OK": 1,
            "N/A": 0,
        }
        # Later successful batches must not erase an earlier failed check.
        if (
            not replace_provisional
            and isinstance(previous, dict)
            and priority.get(str(previous.get("verdict")), 3) > priority.get(verdict, 3)
        ):
            return
        target[domain] = {
            "verdict": verdict,
            "reason": reason,
            "facts": deepcopy(facts),
        }


def run_observations() -> dict[str, object]:
    """Detach report inputs from the mutable execution context."""
    return deepcopy(_observations.get() or {})


def record_dq_observation(result: DQResult) -> DQResult:
    """Persist the executed assessment and return it unchanged to its caller."""
    record_run_observation(
        "Data Quality",
        verdict={"passed": "OK", "warning": "WARN", "failed": "ERROR"}.get(
            result.status.value, "UNKNOWN"
        ),
        reason="run_dq_threshold_evaluation",
        facts={
            "error_rate": result.error_rate,
            "status": result.status.value,
            "has_critical": result.has_critical,
            "rule_outcomes_count": result.rule_outcomes_count,
        },
    )
    return result
