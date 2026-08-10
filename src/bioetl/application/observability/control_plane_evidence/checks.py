"""Shared result types for bounded operator-facing control-plane evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EvidenceStatus = Literal["OK", "WARNING", "ERROR", "UNKNOWN"]


@dataclass(frozen=True, slots=True)
class EvidenceCheckResult:
    """One bounded validation result suitable for an operator table."""

    check: str
    status: EvidenceStatus
    reason: str
    detail: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe table row."""
        return {
            "check": self.check,
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
        }


__all__ = ["EvidenceCheckResult", "EvidenceStatus"]
