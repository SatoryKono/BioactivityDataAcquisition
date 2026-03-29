"""Shared decision payload for filter evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import JsonDict


@dataclass(frozen=True, slots=True)
class FilterDecision:
    """Structured result of evaluating a record against filter rules."""

    include: bool
    reason_code: str | None = None
    rule_type: str | None = None
    field: str | None = None
    operator: str | None = None
    expected: object | None = None
    actual: object | None = None
    message: str | None = None

    @classmethod
    def allowed(cls) -> FilterDecision:
        """Build an allow decision."""
        return cls(include=True)

    @classmethod
    def rejected(
        cls,
        *,
        reason_code: str,
        rule_type: str,
        field: str,
        message: str,
        operator: str | None = None,
        expected: object | None = None,
        actual: object | None = None,
    ) -> FilterDecision:
        """Build a reject decision."""
        return cls(
            include=False,
            reason_code=reason_code,
            rule_type=rule_type,
            field=field,
            operator=operator,
            expected=expected,
            actual=actual,
            message=message,
        )

    def to_dict(self) -> JsonDict:
        """Convert the decision into JSON-serializable metadata."""
        return {
            "include": self.include,
            "reason_code": self.reason_code,
            "rule_type": self.rule_type,
            "field": self.field,
            "operator": self.operator,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
        }
