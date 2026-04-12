"""Architecture ratchet for normalization fallback business debt."""

from __future__ import annotations

from scripts.qa.report_normalization_fallback_inventory import _build_payload
from scripts.qa.report_normalization_fallback_inventory import _fallback_rows

FALLBACK_BUSINESS_FIELD_BUDGET = 0


def test_fallback_business_field_count_does_not_exceed_budget() -> None:
    """Business fallback normalization debt must not grow above the reviewed baseline."""
    payload = _build_payload(_fallback_rows())
    actual = int(payload["fallback_business_field_count"])

    assert actual <= FALLBACK_BUSINESS_FIELD_BUDGET, (
        "fallback_business_field_count="
        f"{actual} exceeds budget {FALLBACK_BUSINESS_FIELD_BUDGET}. "
        "Reduce fallback business debt or intentionally rebaseline the ratchet."
    )
