"""Unit tests for SilverDQAnalyzer orchestration and API compatibility."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import polars as pl
import pyarrow as pa

from bioetl.application.services.dq.silver_analyzer import SilverDQAnalyzer
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    MedallionLayer,
    SilverDQCheckType,
)


def _config(checks: list[SilverDQCheckType]) -> MagicMock:
    config = MagicMock()
    config.get_checks_enums.return_value = checks
    return config


def test_analyze_preserves_public_api_and_returns_report() -> None:
    analyzer = SilverDQAnalyzer()
    report = analyzer.analyze(
        pl.DataFrame({"id": [1, 2, 3], "_content_hash": ["a", "b", "c"]}),
        run_id="run-1",
        pipeline="p",
        target_table="silver.table",
        source_batch_ids=["batch-1"],
        config=_config(list(SilverDQCheckType)),
        timestamp=datetime.now(UTC),
        primary_keys=["id"],
    )

    assert report.layer == MedallionLayer.SILVER
    assert report.run_id == "run-1"
    assert report.thresholds.threshold_status == DQCheckStatus.PASS


def test_analyze_supports_pyarrow_input() -> None:
    analyzer = SilverDQAnalyzer()
    table = pa.table({"id": [1, 1], "_content_hash": ["h1", "h1"]})
    report = analyzer.analyze(
        table,
        run_id="run-arrow",
        pipeline="p",
        target_table="silver.table",
        source_batch_ids=["batch-1"],
        config=_config(
            [SilverDQCheckType.UNIQUENESS, SilverDQCheckType.CONTENT_HASH_INTEGRITY]
        ),
        timestamp=datetime.now(UTC),
        primary_keys=["id"],
    )

    assert report.checks["uniqueness"]["status"] == DQCheckStatus.WARN.value
    assert report.checks["content_hash_integrity"]["status"] == DQCheckStatus.WARN.value


def test_backwards_compatible_helper_methods_delegate() -> None:
    analyzer = SilverDQAnalyzer()
    df = pl.DataFrame({"id": [1], "_content_hash": ["h"]})

    thresholds = analyzer._calculate_thresholds(1, 1, 0, 0.05, 0.2)
    record_count = analyzer._check_record_count(df, 1, 0)

    assert thresholds.threshold_status == DQCheckStatus.PASS
    assert record_count.output_records == 1
