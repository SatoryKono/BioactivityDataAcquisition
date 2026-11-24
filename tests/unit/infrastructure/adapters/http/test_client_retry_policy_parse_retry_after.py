"""Unit tests for the shared Retry-After parser of the HTTP retry policy.

``parse_retry_after`` feeds three production paths: the retry flow that guards
the wait budget (``_client_retry_flow``), the provider cooldown in request
timing, and the PubChem fetch flow. No test exercised the parser directly, so
a regression could silently change retry timing (negative waits, unbounded
waits, or a mis-parsed HTTP date) without any failing test.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest

from bioetl.infrastructure.adapters.http.client_retry_policy import parse_retry_after

_BASE_INSTANT = datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)


@pytest.mark.unit
class TestParseRetryAfterDelaySeconds:
    """Retry-After delay-seconds form."""

    def test_parse_retry_after__integer_seconds__returns_exact_delay(self) -> None:
        assert parse_retry_after("120") == pytest.approx(120.0)

    def test_parse_retry_after__zero_seconds__returns_zero_delay(self) -> None:
        assert parse_retry_after("0") == pytest.approx(0.0)

    def test_parse_retry_after__fractional_seconds__returns_fractional_delay(
        self,
    ) -> None:
        assert parse_retry_after("1.5") == pytest.approx(1.5)

    def test_parse_retry_after__padded_seconds__ignores_surrounding_whitespace(
        self,
    ) -> None:
        assert parse_retry_after("  30  ") == pytest.approx(30.0)


@pytest.mark.unit
class TestParseRetryAfterRejectedValues:
    """Values that must never become a wait duration."""

    def test_parse_retry_after__empty_value__returns_none(self) -> None:
        assert parse_retry_after("") is None

    def test_parse_retry_after__whitespace_only_value__returns_none(self) -> None:
        assert parse_retry_after("   ") is None

    def test_parse_retry_after__negative_delay__returns_none(self) -> None:
        assert parse_retry_after("-5") is None

    def test_parse_retry_after__infinite_delay__returns_none(self) -> None:
        assert parse_retry_after("inf") is None

    def test_parse_retry_after__not_a_number_delay__returns_none(self) -> None:
        assert parse_retry_after("nan") is None

    def test_parse_retry_after__non_date_text__returns_none(self) -> None:
        assert parse_retry_after("not-a-timestamp") is None


@pytest.mark.unit
class TestParseRetryAfterHttpDate:
    """Retry-After HTTP-date form."""

    def test_parse_retry_after__future_http_date__returns_seconds_until_target(
        self,
    ) -> None:
        header = format_datetime(_BASE_INSTANT + timedelta(hours=1), usegmt=True)

        assert parse_retry_after(
            header, now=_BASE_INSTANT.timestamp()
        ) == pytest.approx(3600.0)

    def test_parse_retry_after__past_http_date__returns_zero_delay(self) -> None:
        header = format_datetime(_BASE_INSTANT - timedelta(minutes=5), usegmt=True)

        assert parse_retry_after(
            header, now=_BASE_INSTANT.timestamp()
        ) == pytest.approx(0.0)

    def test_parse_retry_after__http_date_without_timezone__returns_none(self) -> None:
        header = "Wed, 24 Nov 2026 12:00:00"

        assert parse_retry_after(header, now=_BASE_INSTANT.timestamp()) is None

    def test_parse_retry_after__http_date_with_offset__returns_seconds_until_target(
        self,
    ) -> None:
        # 16:00 at +0300 is 13:00 UTC, one hour after the reference instant.
        header = "Wed, 24 Nov 2026 16:00:00 +0300"

        assert parse_retry_after(
            header, now=_BASE_INSTANT.timestamp()
        ) == pytest.approx(3600.0)
