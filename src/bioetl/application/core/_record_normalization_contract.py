"""Shared record-normalization runtime contracts."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["NormalizationContractError", "_NormalizationFinding"]


@dataclass(frozen=True, slots=True)
class _NormalizationFinding:
    field_name: str
    reason_code: str
    action_taken: str
    dq_warn: bool = True


class NormalizationContractError(ValueError):
    """Raised when profile-backed runtime normalization would fall back implicitly."""
