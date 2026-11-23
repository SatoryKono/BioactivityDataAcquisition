"""Separate engineering admission from biological acceptance.

Expectations must exist before the classifier runs. A class-match count, the
historical 633 figure, and the six reviewed receipts do not admit new semantics.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

DIAGNOSTIC_NOT_KPI = (633, 374)
LEGACY_REVIEWED_CASES = 6
BUCKETS = ("verified", "allowable_incompleteness", "unsupported", "unreviewed")


@dataclass(frozen=True, slots=True)
class Admission:
    """Engineering checks can pass while biological acceptance stays false."""

    engineering_acceptance: bool
    biological_accuracy_accepted: bool
    buckets: Mapping[str, int]
    expectation_source: str

    def __post_init__(self) -> None:
        if (
            self.biological_accuracy_accepted
            and self.expectation_source == "classifier"
        ):
            raise ValueError("classifier output cannot certify biological accuracy")
        unknown = set(self.buckets) - set(BUCKETS)
        if unknown:
            raise ValueError("unknown qualification bucket")


def assert_not_self_certified(
    expectation_ids: frozenset[str], classifier_output_ids: frozenset[str]
) -> None:
    """Refuse expectations whose identity is the classifier output."""
    if expectation_ids and expectation_ids <= classifier_output_ids:
        raise ValueError("classifier output cannot certify its own expectations")


def legacy_receipt_does_not_admit(reviewed_cases: int, schema_version: str) -> bool:
    """The six-case receipt does not qualify a newer contract."""
    return reviewed_cases == LEGACY_REVIEWED_CASES and schema_version != "3.1.0"


__all__ = [
    "BUCKETS",
    "DIAGNOSTIC_NOT_KPI",
    "LEGACY_REVIEWED_CASES",
    "Admission",
    "assert_not_self_certified",
    "legacy_receipt_does_not_admit",
]
