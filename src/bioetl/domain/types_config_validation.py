"""Config validation value objects for domain preflight checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfigValidationError:
    """Single configuration validation error."""

    field: str
    expected: str
    actual: str
    rule: str


__all__ = ["ConfigValidationError"]
