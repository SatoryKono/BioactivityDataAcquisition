"""Unit tests for the domain time helpers that guard completion ordering.

``utc_instant`` and ``validate_completion_order`` reject naive timestamps and
completion instants that precede the start of the run. Only the "earlier
completion" branch was covered indirectly through the PipelineRun aggregate;
the timezone-awareness and cross-offset comparison branches had no test.

The assertions compare the returned UTC offset as well as the instant: an
implementation that returns the original aware datetime unchanged would pass
instant-only equality checks.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone, tzinfo

import pytest

from bioetl.domain.context_time import utc_instant, validate_completion_order

_OFFSET_TWO_HOURS = timezone(timedelta(hours=2))


class _AmbiguousZone(tzinfo):
    """A DST-like zone where ``fold`` selects between two UTC offsets.

    ``fold=0`` means the earlier (+02:00) occurrence of an ambiguous wall
    clock time, ``fold=1`` the later (+01:00) one. The helper is used instead
    of a real IANA zone so the case stays deterministic and does not depend on
    a ``tzdata`` package being installed.
    """

    def utcoffset(self, dt: datetime | None) -> timedelta:
        if dt is None:
            return timedelta(hours=2)
        return timedelta(hours=2 if dt.fold == 0 else 1)

    def dst(self, dt: datetime | None) -> timedelta:
        if dt is None:
            return timedelta(hours=1)
        return timedelta(hours=1 if dt.fold == 0 else 0)

    def tzname(self, dt: datetime | None) -> str:
        if dt is None:
            return "AMB+02"
        return "AMB+02" if dt.fold == 0 else "AMB+01"


@pytest.mark.unit
class TestUtcInstant:
    """Aware instant normalization."""

    def test_utc_instant__aware_timestamp__converts_to_utc(self) -> None:
        value = datetime(2026, 11, 24, 14, 0, 0, tzinfo=_OFFSET_TWO_HOURS)

        result = utc_instant(value)

        assert result == datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)
        assert result.tzinfo is UTC
        assert result.utcoffset() == timedelta(0)
        assert result.hour == 12

    def test_utc_instant__already_utc_timestamp__keeps_same_instant(self) -> None:
        value = datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)

        result = utc_instant(value)

        assert result == value
        assert result.tzinfo is UTC
        assert result.utcoffset() == timedelta(0)

    def test_utc_instant__naive_timestamp__raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="timestamp must be timezone-aware"):
            utc_instant(datetime(2026, 11, 24, 12, 0, 0))

    def test_utc_instant__ambiguous_local_time__resolves_fold_to_utc(self) -> None:
        zone = _AmbiguousZone()
        earlier = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0)
        later = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=1)

        earlier_utc = utc_instant(earlier)
        later_utc = utc_instant(later)

        assert earlier_utc.utcoffset() == timedelta(0)
        assert later_utc.utcoffset() == timedelta(0)
        assert earlier_utc == datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
        assert later_utc == datetime(2026, 10, 25, 1, 30, tzinfo=UTC)
        assert earlier_utc < later_utc


@pytest.mark.unit
class TestValidateCompletionOrder:
    """Completion must not precede the start of the run."""

    def test_validate_completion_order__missing_completion__returns_none(self) -> None:
        result = validate_completion_order(
            None, datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)
        )

        assert result is None

    def test_validate_completion_order__completion_equal_to_start__returns_none(
        self,
    ) -> None:
        started = datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)

        result = validate_completion_order(started, started)

        assert result is None

    def test_validate_completion_order__completion_after_start__returns_none(
        self,
    ) -> None:
        result = validate_completion_order(
            datetime(2026, 11, 24, 12, 0, 1, tzinfo=UTC),
            datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC),
        )

        assert result is None

    def test_validate_completion_order__completion_before_start__raises_value_error(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="completed_at cannot be earlier"):
            validate_completion_order(
                datetime(2026, 11, 24, 11, 59, 59, tzinfo=UTC),
                datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC),
            )

    def test_validate_completion_order__same_instant_in_different_offsets__returns_none(
        self,
    ) -> None:
        started = datetime(2026, 11, 24, 14, 0, 0, tzinfo=_OFFSET_TWO_HOURS)
        completed = datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)

        result = validate_completion_order(completed, started)

        assert result is None

    def test_validate_completion_order__earlier_instant_in_different_offsets__raises_value_error(
        self,
    ) -> None:
        started = datetime(2026, 11, 24, 14, 0, 0, tzinfo=_OFFSET_TWO_HOURS)
        completed = datetime(2026, 11, 24, 11, 59, 59, tzinfo=UTC)

        with pytest.raises(ValueError, match="completed_at cannot be earlier"):
            validate_completion_order(completed, started)

    def test_validate_completion_order__ambiguous_local_time__orders_by_instant(
        self,
    ) -> None:
        zone = _AmbiguousZone()
        started = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0)
        completed = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=1)

        assert validate_completion_order(completed, started) is None

        with pytest.raises(ValueError, match="completed_at cannot be earlier"):
            validate_completion_order(started, completed)

    def test_validate_completion_order__naive_started_at__raises_value_error(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="timestamp must be timezone-aware"):
            validate_completion_order(
                datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC),
                datetime(2026, 11, 24, 12, 0, 0),
            )

    def test_validate_completion_order__naive_completed_at__raises_value_error(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="timestamp must be timezone-aware"):
            validate_completion_order(
                datetime(2026, 11, 24, 12, 0, 0),
                datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC),
            )
