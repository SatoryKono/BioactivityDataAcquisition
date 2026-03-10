"""Integration-style tests for SilverDQAnalyzer facade."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import polars as pl
import pyarrow as pa
import pytest

from bioetl.application.services.dq.silver_analyzer import SilverDQAnalyzer
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    MedallionLayer,
    SilverDQCheckType,
)


@pytest.fixture()
def analyzer() -> SilverDQAnalyzer:
    return SilverDQAnalyzer()


@pytest.fixture()
def mock_config_all_checks() -> MagicMock:
    config = MagicMock()
    config.get_checks_enums.return_value = list(SilverDQCheckType)
    return config


@pytest.fixture()
def mock_config_empty() -> MagicMock:
    config = MagicMock()
    config.get_checks_enums.return_value = []
    return config


def test_analyze_pyarrow_table_input(
    analyzer: SilverDQAnalyzer,
    mock_config_all_checks: MagicMock,
) -> None:
    table = pa.table(
        {
            "id": [1, 2, 3],
            "name": ["a", "b", "c"],
            "_content_hash": ["h1", "h2", "h3"],
        }
    )

    report = analyzer.analyze(
        data=table,
        run_id="arrow-run",
        pipeline="test",
        target_table="silver/test",
        source_batch_ids=["batch-arrow"],
        config=mock_config_all_checks,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        primary_keys=["id"],
    )

    assert report.layer == MedallionLayer.SILVER
    assert "record_count" in report.checks


def test_analyze_no_checks_enabled(
    analyzer: SilverDQAnalyzer,
    mock_config_empty: MagicMock,
) -> None:
    report = analyzer.analyze(
        data=pl.DataFrame({"id": [1, 2, 3]}),
        run_id="empty-checks",
        pipeline="test",
        target_table="silver/test",
        source_batch_ids=[],
        config=mock_config_empty,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        primary_keys=[],
    )

    assert report.checks == {}
    assert report.summary.passed == 0
    assert report.summary.failed == 0


def test_analyze_with_key_nullability_rules(
    analyzer: SilverDQAnalyzer,
    mock_config_all_checks: MagicMock,
) -> None:
    report = analyzer.analyze(
        data=pl.DataFrame({"merge_key": [1, None, 3]}),
        run_id="key-null-test",
        pipeline="test",
        target_table="silver/test",
        source_batch_ids=[],
        config=mock_config_all_checks,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        primary_keys=["merge_key"],
        key_nullability_rules=[
            {"field": "merge_key", "key_type": "merge", "nullable": False}
        ],
    )

    assert report.checks["key_nullability"]["violations"]


def test_analyze_threshold_hard_fail(
    analyzer: SilverDQAnalyzer,
    mock_config_empty: MagicMock,
) -> None:
    report = analyzer.analyze(
        data=pl.DataFrame({"id": [1, 2]}),
        run_id="hard-fail",
        pipeline="test",
        target_table="silver/test",
        source_batch_ids=[],
        config=mock_config_empty,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        primary_keys=[],
        input_record_count=10,
        quarantined_count=3,
    )

    assert report.thresholds.threshold_status == DQCheckStatus.FAIL
