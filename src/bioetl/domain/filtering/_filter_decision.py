"""Shared decision payload for filter evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import JsonDict


@dataclass(frozen=True, slots=True)
class FilterDecision:
    """Structured result of evaluating a record against filter rules.

    The structured fields form the stable analytical identity for a rejection.
    ``message`` remains human-readable display text and should not be used as an
    aggregation key in CLI, quarantine summaries, or observability pipelines.
    """

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

    def analytics_details(self) -> JsonDict:
        """Return stable structured fields used for grouping and drilldown."""
        return {
            "reason_code": self.reason_code,
            "rule_type": self.rule_type,
            "field": self.field,
            "operator": self.operator,
            "expected": self.expected,
            "actual": self.actual,
        }

    def analytics_key(self) -> str | None:
        """Build a stable grouping key from structured reason fields only."""
        parts: list[str] = []
        for value in (
            self.reason_code,
            self.rule_type,
            self.field,
            self.operator,
        ):
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        if not parts:
            return None
        return " | ".join(parts)

    def to_dict(self) -> JsonDict:
        """Convert the decision into JSON-serializable metadata."""
        return {
            "include": self.include,
            **self.analytics_details(),
            "message": self.message,
        }
