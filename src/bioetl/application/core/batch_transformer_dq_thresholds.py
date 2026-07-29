"""DQ threshold classification helpers for batch transformer finalization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from numbers import Real


class ThresholdBreachReason(Enum):
    """Classification of DQ threshold breaches."""
    NONE = "none"
    SOFT = "soft"
    HARD = "hard"


@dataclass(frozen=True, slots=True)
class DQThresholdCheckResult:
    """Result of DQ threshold validation."""
    breach: ThresholdBreachReason
    error_rate: float
    soft_threshold: float | None
    hard_threshold: float | None


ThresholdBreach = ThresholdBreachReason


def check_dq_thresholds(
    *,
    error_count: int,
    record_count: int,
    soft_threshold: float | None,
    hard_threshold: float | None,
) -> DQThresholdCheckResult:
    """Check whether the current error rate breaches configured thresholds."""
    if record_count == 0:
        return DQThresholdCheckResult(
            breach=ThresholdBreachReason.NONE,
            error_rate=0.0,
            soft_threshold=soft_threshold,
            hard_threshold=hard_threshold,
        )
    error_rate = error_count / record_count
    if hard_threshold is not None and error_rate >= float(hard_threshold):
        return DQThresholdCheckResult(
            breach=ThresholdBreachReason.HARD,
            error_rate=error_rate,
            soft_threshold=soft_threshold,
            hard_threshold=hard_threshold,
        )
    if soft_threshold is not None and error_rate >= float(soft_threshold):
        return DQThresholdCheckResult(
            breach=ThresholdBreachReason.SOFT,
            error_rate=error_rate,
            soft_threshold=soft_threshold,
            hard_threshold=hard_threshold,
        )
    return DQThresholdCheckResult(
        breach=ThresholdBreachReason.NONE,
        error_rate=error_rate,
        soft_threshold=soft_threshold,
        hard_threshold=hard_threshold,
    )


def classify_dq_threshold_breach(
    error_rate: float,
    soft_threshold: float | None,
    hard_threshold: float | None,
) -> ThresholdBreachReason:
    """Classify the threshold breach for a concrete error rate."""
    if hard_threshold is not None and error_rate >= hard_threshold:
        return ThresholdBreachReason.HARD
    if soft_threshold is not None and error_rate >= soft_threshold:
        return ThresholdBreachReason.SOFT
    return ThresholdBreachReason.NONE


def compute_error_rate(error_count: int, record_count: int) -> float:
    """Compute the error rate, guarding the zero-record case."""
    return error_count / record_count if record_count > 0 else 0.0


def resolve_threshold_value(
    dq_config: object | None,
    *attribute_names: str,
) -> float | None:
    """Resolve one numeric threshold while ignoring loose mocks."""
    if dq_config is None:
        return None
    for attribute_name in attribute_names:
        value = getattr(dq_config, attribute_name, None)
        if isinstance(value, Real) and not isinstance(value, bool):
            return float(value)
    return None


__all__ = [
    "DQThresholdCheckResult",
    "ThresholdBreach",
    "ThresholdBreachReason",
    "check_dq_thresholds",
    "classify_dq_threshold_breach",
    "compute_error_rate",
    "resolve_threshold_value",
]
