"""Structural DQ validation tests against real check/analyzer outputs.

These tests validate actual behavior from:
- check_referential_integrity
- check_scd_integrity
- GoldDQAnalyzer
- SilverDQAnalyzer key nullability checks
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.services.dq._checks_integrity import (
    check_referential_integrity,
    check_scd_integrity,
)
from bioetl.application.services.dq.gold_analyzer import GoldDQAnalyzer
from bioetl.application.services.dq.silver_check_executor import SilverCheckExecutor
from bioetl.application.services.dq.silver_analyzer import SilverDQAnalyzer
from bioetl.application.services.dq.silver_statistics import SilverStatisticsCalculator
from bioetl.application.services.dq.silver_threshold import SilverThresholdChecker
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    GoldDQCheckType,
    SilverDQCheckType,
)


def _flags_from_status(*, status: DQCheckStatus, reason: str) -> dict[str, str | bool]:
    """Normalize check status to record-level DQ flags for assertions."""
    if status == DQCheckStatus.FAIL:
        return {
            "_dq_error": True,
            "_dq_warn": False,
            "severity": "error",
            "reason": reason,
        }
    if status == DQCheckStatus.WARN:
        return {
            "_dq_error": False,
            "_dq_warn": True,
            "severity": "warn",
            "reason": reason,
        }
    return {
        "_dq_error": False,
        "_dq_warn": False,
        "severity": "pass",
        "reason": "",
    }


def _build_silver_analyzer() -> SilverDQAnalyzer:
    """Create a fully wired SilverDQAnalyzer for structural tests."""
    statistics = SilverStatisticsCalculator()
    threshold_checker = SilverThresholdChecker()
    return SilverDQAnalyzer(
        statistics=statistics,
        threshold_checker=threshold_checker,
        check_executor=SilverCheckExecutor(
            statistics=statistics,
            threshold_checker=threshold_checker,
        ),
    )


@pytest.mark.unit
class TestStructuralIntegrityChecks:
    """Structural rules must assert checker outputs and statuses."""

    def test_referential_integrity_warn_sets_dq_warn(self) -> None:
        # 200 refs, 1 orphan => 0.5% (WARN boundary path <=1%)
        local_values = [*list(range(1, 200)), 9999]
        df = pl.DataFrame({"cat_id": local_values})
        ref = pl.DataFrame({"id": list(range(1, 200))})

        result = check_referential_integrity(df, {"cat_id -> categories.id": ref})
        fk = result.foreign_keys["cat_id -> categories.id"]
        flags = _flags_from_status(
            status=fk.status,
            reason=f"{fk.reference}: orphan_records={fk.orphan_records}",
        )

        assert fk.status == DQCheckStatus.WARN
        assert flags["_dq_error"] is False
        assert flags["_dq_warn"] is True
        assert flags["severity"] == "warn"
        assert "orphan_records=1" in str(flags["reason"])

    def test_referential_integrity_fail_sets_dq_error(self) -> None:
        df = pl.DataFrame({"cat_id": [1, 2, 999, 998]})
        ref = pl.DataFrame({"id": [1, 2]})

        result = check_referential_integrity(df, {"cat_id -> categories.id": ref})
        fk = result.foreign_keys["cat_id -> categories.id"]
        flags = _flags_from_status(
            status=result.status,
            reason=f"{fk.reference}: orphan_records={fk.orphan_records}",
        )

        assert result.status == DQCheckStatus.FAIL
        assert flags["_dq_error"] is True
        assert flags["_dq_warn"] is False
        assert flags["severity"] == "error"
        assert "orphan_records=" in str(flags["reason"])

    def test_referential_integrity_ignores_unparseable_reference_keys(self) -> None:
        df = pl.DataFrame({"cat_id": [1, 2]})
        result = check_referential_integrity(
            df,
            {"bad key format": pl.DataFrame({"id": [1, 2]})},
        )

        assert result.foreign_keys == {}
        assert result.status == DQCheckStatus.PASS

    def test_scd_overlap_sets_warn_with_reason(self) -> None:
        df = pl.DataFrame(
            {
                "entity_id": ["A", "A"],
                "_valid_from": [datetime(2024, 1, 1), datetime(2024, 3, 1)],
                "_valid_to": [datetime(2024, 6, 1), datetime(2024, 12, 1)],
            }
        )
        scd_config = {
            "type": 2,
            "entity_key": "entity_id",
            "valid_from_col": "_valid_from",
            "valid_to_col": "_valid_to",
        }

        result = check_scd_integrity(df, scd_config)
        flags = _flags_from_status(
            status=result.status,
            reason=f"overlapping_validity_periods={result.overlapping_validity_periods}",
        )

        assert result.status == DQCheckStatus.WARN
        assert result.overlapping_validity_periods > 0
        assert flags["_dq_error"] is False
        assert flags["_dq_warn"] is True
        assert flags["severity"] == "warn"
        assert "overlapping_validity_periods=" in str(flags["reason"])

    def test_scd_integrity_defaults_to_pass_when_business_key_missing(self) -> None:
        df = pl.DataFrame(
            {
                "_valid_from": [datetime(2024, 1, 1), datetime(2024, 3, 1)],
                "_valid_to": [datetime(2024, 6, 1), None],
            }
        )

        result = check_scd_integrity(
            df,
            {
                "type": 2,
                "entity_key": "entity_id",
                "valid_from_col": "_valid_from",
                "valid_to_col": "_valid_to",
            },
        )

        assert result.status == DQCheckStatus.PASS
        assert result.total_entities == len(df)
        assert result.overlapping_validity_periods == 0


@pytest.mark.unit
class TestStructuralAnalyzerIntegration:
    """Structural checks should be preserved in analyzer outputs."""

    def test_gold_analyzer_reports_structural_failures(self) -> None:
        analyzer = GoldDQAnalyzer()
        config = MagicMock()
        config.get_checks_enums.return_value = [
            GoldDQCheckType.REFERENTIAL_INTEGRITY,
            GoldDQCheckType.SCD_INTEGRITY,
        ]

        report = analyzer.analyze(
            data=pl.DataFrame(
                {
                    "cat_id": [1, 2, 999],
                    "entity_id": ["A", "A", "A"],
                    "_valid_from": [
                        datetime(2024, 1, 1),
                        datetime(2024, 2, 1),
                        datetime(2024, 3, 1),
                    ],
                    "_valid_to": [
                        datetime(2024, 12, 1),
                        datetime(2024, 6, 1),
                        None,
                    ],
                }
            ),
            run_id="rf01-struct-gold",
            pipeline="test_pipeline",
            target_table="gold.test",
            config=config,
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            reference_tables={"cat_id -> categories.id": pl.DataFrame({"id": [1, 2]})},
            scd_config={
                "type": 2,
                "entity_key": "entity_id",
                "valid_from_col": "_valid_from",
                "valid_to_col": "_valid_to",
            },
        )

        ri = report.checks["referential_integrity"]
        scd = report.checks["scd_integrity"]

        assert ri["status"] in {DQCheckStatus.WARN.value, DQCheckStatus.FAIL.value}
        assert "cat_id -> categories.id" in ri["foreign_keys"]
        assert scd["status"] in {DQCheckStatus.PASS.value, DQCheckStatus.WARN.value}

    def test_silver_key_nullability_fail_maps_to_dq_error(self) -> None:
        analyzer = _build_silver_analyzer()
        config = MagicMock()
        config.get_checks_enums.return_value = [SilverDQCheckType.KEY_NULLABILITY]

        report = analyzer.analyze(
            data=pl.DataFrame(
                {
                    "entity_id": ["e1", None],
                    "partition_date": ["2024-01-01", "2024-01-01"],
                }
            ),
            run_id="rf01-struct-silver",
            pipeline="test_pipeline",
            target_table="silver.test",
            source_batch_ids=["batch-1"],
            config=config,
            timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            primary_keys=["entity_id"],
            key_nullability_rules=[
                {"field": "entity_id", "key_type": "merge", "nullable": False},
                {"field": "partition_date", "key_type": "partition", "nullable": False},
            ],
        )

        kn = report.checks["key_nullability"]
        first_violation = kn["violations"][0]
        flags = _flags_from_status(
            status=DQCheckStatus(kn["status"]),
            reason=(
                f"field={first_violation['field']};"
                f"key_type={first_violation['key_type']};"
                f"null_count={first_violation['null_count']}"
            ),
        )

        assert kn["status"] == DQCheckStatus.FAIL.value
        assert first_violation["field"] == "entity_id"
        assert flags["_dq_error"] is True
        assert flags["_dq_warn"] is False
        assert flags["severity"] == "error"
        assert "field=entity_id" in str(flags["reason"])
