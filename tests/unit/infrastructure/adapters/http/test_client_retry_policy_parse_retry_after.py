"""Unit tests for the HTTP ``Retry-After`` header parser.

``parse_retry_after`` converts a provider ``Retry-After`` header into a wait
value that the retry flow compares against the wait budget. Neither the
HTTP-date form nor the rejection of non-finite, negative and naive values had a
direct test, so a parsing regression could silently change retry timing or
bypass the wait-budget guard.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.infrastructure.adapters.http import client_retry_policy
from bioetl.infrastructure.adapters.http.client_retry_policy import parse_retry_after

_HTTP_DATE_TARGET = "Wed, 21 Oct 2026 07:28:00 GMT"
_HTTP_DATE_TARGET_WITH_OFFSET = "Wed, 21 Oct 2026 09:28:00 +0200"
_TARGET_EPOCH = datetime(2026, 10, 21, 7, 28, 0, tzinfo=UTC).timestamp()


class _FrozenClock:
    """Deterministic wall clock used to resolve the ``now=None`` branch."""

    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


@pytest.mark.unit
class TestParseRetryAfterDelaySeconds:
    """Delay-seconds form of the header."""

    def test_parse_retry_after__integer_seconds__returns_exact_delay(self) -> None:
        assert parse_retry_after("120") == 120.0

    def test_parse_retry_after__zero_seconds__returns_zero_delay(self) -> None:
        assert parse_retry_after("0") == 0.0

    def test_parse_retry_after__fractional_seconds__returns_fractional_delay(
        self,
    ) -> None:
        assert parse_retry_after("1.5") == 1.5

    def test_parse_retry_after__padded_seconds__ignores_surrounding_whitespace(
        self,
    ) -> None:
        assert parse_retry_after("  30  ") == 30.0


@pytest.mark.unit
class TestParseRetryAfterRejectedValues:
    """Values that must never become a wait."""

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
        assert parse_retry_after("later") is None


@pytest.mark.unit
class TestParseRetryAfterHttpDate:
    """HTTP-date form of the header."""

    def test_parse_retry_after__future_http_date__returns_seconds_until_target(
        self,
    ) -> None:
        assert parse_retry_after(_HTTP_DATE_TARGET, now=_TARGET_EPOCH - 60) == 60.0

    def test_parse_retry_after__past_http_date__returns_zero_delay(self) -> None:
        assert parse_retry_after(_HTTP_DATE_TARGET, now=_TARGET_EPOCH + 60) == 0.0

    def test_parse_retry_after__http_date_without_timezone__returns_none(self) -> None:
        assert parse_retry_after("Wed, 21 Oct 2026 07:28:00") is None

    def test_parse_retry_after__http_date_with_offset__returns_seconds_until_target(
        self,
    ) -> None:
        assert (
            parse_retry_after(_HTTP_DATE_TARGET_WITH_OFFSET, now=_TARGET_EPOCH - 120)
            == 120.0
        )

    def test_parse_retry_after__http_date_with_frozen_system_clock__returns_delay(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The ``now=None`` branch resolves the reference instant via SystemClock."""
        reference = datetime(2026, 10, 21, 7, 27, 0, tzinfo=UTC)
        monkeypatch.setattr(
            client_retry_policy,
            "SystemClock",
            lambda: _FrozenClock(reference),
        )

        assert parse_retry_after(_HTTP_DATE_TARGET) == 60.0
