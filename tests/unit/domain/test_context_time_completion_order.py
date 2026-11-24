"""Unit tests for the domain time helpers that guard completion ordering.

``utc_instant`` and ``validate_completion_order`` reject naive timestamps and
completion instants that precede the start of the run. Only the "earlier
completion" branch was covered indirectly through the PipelineRun aggregate;
the timezone-awareness and cross-offset comparison branches had no test.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from bioetl.domain.context_time import utc_instant, validate_completion_order

_OFFSET_TWO_HOURS = timezone(timedelta(hours=2))


@pytest.mark.unit
class TestUtcInstant:
    """Aware instant normalization."""

    def test_utc_instant__aware_timestamp__converts_to_utc(self) -> None:
        value = datetime(2026, 11, 24, 14, 0, 0, tzinfo=_OFFSET_TWO_HOURS)

        result = utc_instant(value)

        assert result == datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)
        assert result.tzinfo is UTC

    def test_utc_instant__already_utc_timestamp__keeps_same_instant(self) -> None:
        value = datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)

        assert utc_instant(value) == value

    def test_utc_instant__naive_timestamp__raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="timestamp must be timezone-aware"):
            utc_instant(datetime(2026, 11, 24, 12, 0, 0))


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
