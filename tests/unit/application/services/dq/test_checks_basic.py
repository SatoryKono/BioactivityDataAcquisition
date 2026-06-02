"""Direct unit tests for the ``_checks_basic`` Gold DQ helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from bioetl.application.services.dq._checks_basic import (
    check_completeness,
    check_data_freshness,
    check_record_count,
)
from bioetl.domain.value_objects.dq_report import DQCheckStatus


pytestmark = pytest.mark.unit


class TestCheckRecordCountDirect:
    """Direct ownership tests for ``check_record_count``."""

    def test_non_numeric_baseline_falls_back_to_current_count(self) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_record_count(df, {"record_count_ma30": "not-a-number"})

        assert result.value == 3
        assert result.delta_from_last_run == 0
        assert result.status == DQCheckStatus.PASS

    def test_zero_baseline_avoids_division_and_delta(self) -> None:
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_record_count(df, {"record_count_ma30": 0})

        assert result.value == 3
        assert result.delta_from_last_run is None
        assert result.status == DQCheckStatus.PASS


class TestCheckCompletenessDirect:
    """Direct ownership tests for ``check_completeness``."""

    def test_empty_dataframe_fails_when_required_field_exists(self) -> None:
        df = pl.DataFrame({"id": pl.Series([], dtype=pl.Int64)})

        result = check_completeness(df, ["id"], 0.9)

        assert result.required_fields["id"] == pytest.approx(0.0)
        assert result.overall_completeness_score == pytest.approx(0.0)
        assert result.status == DQCheckStatus.FAIL

    def test_all_missing_required_fields_fail_with_zero_score(self) -> None:
        df = pl.DataFrame({"present": [1, 2, 3]})

        result = check_completeness(df, ["missing_a", "missing_b"], 0.8)

        assert result.required_fields == pytest.approx(
            {"missing_a": 0.0, "missing_b": 0.0}
        )
        assert result.overall_completeness_score == pytest.approx(0.0)
        assert result.status == DQCheckStatus.FAIL


class TestCheckDataFreshnessDirect:
    """Direct ownership tests for ``check_data_freshness``."""

    def test_falls_back_to_next_timestamp_column(self) -> None:
        current_time = datetime(2024, 5, 20, 12, 0, tzinfo=UTC)
        df = pl.DataFrame(
            {
                "_updated_at": [None, None],
                "updated_at": [
                    current_time - timedelta(hours=48),
                    current_time - timedelta(hours=36),
                ],
            }
        )

        result = check_data_freshness(df, current_time)

        assert result.max_updated_at == current_time - timedelta(hours=36)
        assert result.freshness_lag_hours == pytest.approx(36.0)
        assert result.status == DQCheckStatus.WARN

    def test_no_timestamp_columns_returns_default_pass(self) -> None:
        current_time = datetime(2024, 5, 20, 12, 0, tzinfo=UTC)
        df = pl.DataFrame({"id": [1, 2, 3]})

        result = check_data_freshness(df, current_time)

        assert result.max_updated_at is None
        assert result.freshness_lag_seconds == pytest.approx(0.0)
        assert result.status == DQCheckStatus.PASS
