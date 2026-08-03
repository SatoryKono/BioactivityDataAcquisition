"""Circuit-breaker configuration value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CircuitBreakerConfig:
    """Configure failure threshold and OPEN-state recovery timeout."""

    failure_threshold: int = 5
    recovery_timeout: int = 300
