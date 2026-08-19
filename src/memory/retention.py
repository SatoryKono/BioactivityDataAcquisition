"""Deterministic retention enforcement for governed memory records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True, slots=True)
class RetentionRecord:
    """Explicit lifecycle metadata required for a governed record."""

    record_id: str
    created_at: str
    ttl_days: int | None = None
    retain_until: str | None = None
    legal_hold: bool = False
    legal_hold_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RetentionViolation:
    """Machine-readable retention violation."""

    record_id: str
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class RetentionReport:
    """Check result suitable for CLI exit-code propagation."""

    checked_count: int
    held_count: int
    violations: tuple[RetentionViolation, ...]

    @property
    def ok(self) -> bool:
        """Whether every record satisfies the governed retention policy."""
        return not self.violations

    @property
    def exit_code(self) -> int:
        """Return zero for success and nonzero-equivalent one for violations."""
        return 0 if self.ok else 1

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic JSON-compatible report data."""
        return {
            "ok": self.ok,
            "exit_code": self.exit_code,
            "checked_count": self.checked_count,
            "held_count": self.held_count,
            "violation_count": len(self.violations),
            "violations": [
                {
                    "record_id": violation.record_id,
                    "code": violation.code,
                    "detail": violation.detail,
                }
                for violation in self.violations
            ],
        }


def _parse_utc(value: str, *, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed.astimezone(UTC)


def check_retention(
    records: list[RetentionRecord] | tuple[RetentionRecord, ...],
    *,
    now: datetime,
) -> RetentionReport:
    """Evaluate explicit lifecycle metadata without filesystem-time fallback."""
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    current_time = now.astimezone(UTC)
    violations: list[RetentionViolation] = []
    held_count = 0

    for record in records:
        held, record_violations = _evaluate_retention_record(record, current_time)
        held_count += int(held)
        violations.extend(record_violations)

    return RetentionReport(
        checked_count=len(records),
        held_count=held_count,
        violations=tuple(violations),
    )


def _evaluate_retention_record(
    record: RetentionRecord,
    current_time: datetime,
) -> tuple[bool, list[RetentionViolation]]:
    """Evaluate one record and return its hold state and violations."""
    if not record.record_id:
        return False, [
            RetentionViolation("", "missing_record_id", "record_id is required")
        ]
    try:
        created_at = _parse_utc(record.created_at, field_name="created_at")
    except ValueError as exc:
        return False, [
            RetentionViolation(record.record_id, "invalid_created_at", str(exc))
        ]
    if record.legal_hold:
        return _evaluate_legal_hold(record)
    return False, _retention_boundary_violations(record, created_at, current_time)


def _evaluate_legal_hold(
    record: RetentionRecord,
) -> tuple[bool, list[RetentionViolation]]:
    if record.legal_hold_reason and record.legal_hold_reason.strip():
        return True, []
    return False, [
        RetentionViolation(
            record.record_id,
            "missing_legal_hold_reason",
            "active legal hold requires an explicit reason",
        )
    ]


def _retention_boundary_violations(
    record: RetentionRecord,
    created_at: datetime,
    current_time: datetime,
) -> list[RetentionViolation]:
    """Validate explicit TTL/retain-until boundaries for one record."""
    if record.ttl_days is not None and record.ttl_days <= 0:
        return [
            RetentionViolation(
                record.record_id, "invalid_ttl", "ttl_days must be greater than zero"
            )
        ]
    expiries = (
        [created_at + timedelta(days=record.ttl_days)]
        if record.ttl_days is not None
        else []
    )
    if record.retain_until is not None:
        try:
            expiries.append(_parse_utc(record.retain_until, field_name="retain_until"))
        except ValueError as exc:
            return [
                RetentionViolation(record.record_id, "invalid_retain_until", str(exc))
            ]
    if not expiries:
        return [
            RetentionViolation(
                record.record_id,
                "missing_retention_policy",
                "ttl_days or retain_until is required",
            )
        ]
    if current_time >= max(expiries):
        return [
            RetentionViolation(
                record.record_id,
                "retention_expired",
                "record exceeded its explicit retention boundary",
            )
        ]
    return []
