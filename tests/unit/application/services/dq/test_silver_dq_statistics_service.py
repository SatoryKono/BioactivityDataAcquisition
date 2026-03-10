"""Unit tests for SilverDQStatisticsService."""

from __future__ import annotations

import polars as pl

from bioetl.application.services.dq.silver_dq_statistics_service import (
    SilverDQStatisticsService,
)
from bioetl.domain.value_objects.dq_report import DQCheckStatus


def test_check_value_distribution_profiles_numeric_and_categorical() -> None:
    service = SilverDQStatisticsService()
    df = pl.DataFrame({"score": [1.0, 2.0, 3.0], "category": ["a", "b", "a"]})

    result = service.check_value_distribution(df)

    assert "score" in result.numeric_columns
    assert "category" in result.categorical_columns
    assert result.status == DQCheckStatus.PASS


def test_distribution_to_dict_serializes_distributions() -> None:
    service = SilverDQStatisticsService()
    df = pl.DataFrame({"score": [1.0, 2.0, 3.0]})

    result = service.check_value_distribution(df)
    output = service.distribution_to_dict(result)

    assert "score" in output["numeric_columns"]
    assert output["status"] == DQCheckStatus.PASS.value
