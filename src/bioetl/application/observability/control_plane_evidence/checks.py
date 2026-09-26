"""Shared result types for bounded operator-facing control-plane evidence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, cast

from bioetl.application.observability.reason_aliases import display_reason

EvidenceStatus = Literal["OK", "WARNING", "ERROR", "UNKNOWN"]
TrustStatus = Literal["OK", "WARNING", "ERROR", "INCOMPLETE"]
ProcessingStatus = Literal["success", "failed", "shutdown", "unknown"]
ScopeKind = Literal["exact_run", "pipeline_current", "unresolved"]
EvidenceFreshness = Literal["observed", "unknown"]

_TRUST_RANK: dict[TrustStatus, int] = {
    "OK": 0,
    "WARNING": 1,
    "INCOMPLETE": 2,
    "ERROR": 3,
}


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
            "reason_display": display_reason(self.reason),
            "detail": self.detail,
        }


def component_checks(
    components: Iterable[dict[str, object]],
) -> tuple[EvidenceCheckResult, ...]:
    """Normalize component evidence without turning missing or invalid statuses into OK."""
    checks: list[EvidenceCheckResult] = []
    for component in components:
        name = str(component["endpoint"])
        rows = component.get("rows")
        if not isinstance(rows, list) or not rows:
            checks.append(
                EvidenceCheckResult(name, "UNKNOWN", "evidence_missing", name)
            )
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            status = row.get("status", "UNKNOWN")
            checks.append(
                EvidenceCheckResult(
                    f"{name}.{row.get('check', 'unknown')}",
                    cast(EvidenceStatus, status)
                    if status in {"OK", "WARNING", "ERROR", "UNKNOWN"}
                    else "UNKNOWN",
                    str(row.get("reason", "evidence_missing")),
                    str(row.get("detail", "")),
                )
            )
    return tuple(checks)


def aggregate_trust_status(checks: Iterable[EvidenceCheckResult]) -> TrustStatus:
    """Fold per-check statuses with fail-closed precedence.

    ``ERROR`` wins. Missing evidence (``UNKNOWN``) becomes ``INCOMPLETE``.
    ``UNKNOWN`` is never mapped to ``OK``.
    """
    trust: TrustStatus = "OK"
    saw_check = False
    for check in checks:
        saw_check = True
        mapped: TrustStatus = (
            "INCOMPLETE" if check.status == "UNKNOWN" else check.status
        )
        if _TRUST_RANK[mapped] > _TRUST_RANK[trust]:
            trust = mapped
    return "INCOMPLETE" if not saw_check else trust


__all__ = [
    "EvidenceCheckResult",
    "EvidenceFreshness",
    "EvidenceStatus",
    "ProcessingStatus",
    "ScopeKind",
    "TrustStatus",
    "aggregate_trust_status",
    "component_checks",
]
