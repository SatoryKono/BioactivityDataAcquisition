# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Focused unit tests for silver_statistics calculator."""

from __future__ import annotations

import polars as pl
import pytest

from bioetl.application.services.dq.silver_statistics import SilverStatisticsCalculator
from bioetl.domain.value_objects.dq_report import DQCheckStatus


@pytest.mark.unit
class TestSilverStatisticsCalculator:
    """Direct tests for calculator wrapper behavior."""

    def test_check_record_count_warns_above_quarantine_threshold(self) -> None:
        calculator = SilverStatisticsCalculator()
        df = pl.DataFrame({"entity_id": list(range(80))})

        result = calculator.check_record_count(
            df=df,
            input_count=100,
            quarantined_count=20,
        )

        assert result.value == 80
        assert result.input_records == 100
        assert result.quarantined_records == 20
        assert result.quarantine_rate == pytest.approx(0.2)
        assert result.status == DQCheckStatus.WARN

    def test_check_value_distribution_limits_processing_to_first_twenty_columns(
        self,
    ) -> None:
        calculator = SilverStatisticsCalculator()
        df = pl.DataFrame({f"c{i}": [i, i + 1, i + 2] for i in range(22)})

        result = calculator.check_value_distribution(df)

        assert result.status == DQCheckStatus.PASS
        assert len(result.numeric_columns) == 20
        assert "c20" not in result.numeric_columns
        assert "c21" not in result.numeric_columns

    def test_check_deduplication_uses_content_hash_when_available(self) -> None:
        calculator = SilverStatisticsCalculator()
        df = pl.DataFrame(
            {
                "entity_id": ["e1", "e2", "e3"],
                "_content_hash": ["h1", "h1", "h2"],
            }
        )

        result = calculator.check_deduplication(
            df=df,
            primary_keys=["entity_id"],
            input_count=5,
        )

        assert result.input_before_dedupe == 5
        assert result.output_after_dedupe == 3
        assert result.duplicates_by_content_hash == 1
        assert result.duplicates_by_business_key == 1

    def test_check_content_hash_integrity_warns_on_duplicate_hashes(self) -> None:
        calculator = SilverStatisticsCalculator()
        df = pl.DataFrame({"_content_hash": ["h1", "h1", "h2"]})

        result = calculator.check_content_hash_integrity(df)

        assert result.records_checked == 3
        assert result.hash_collisions == 1
        assert result.status == DQCheckStatus.WARN

    def test_distribution_to_dict_serializes_result(self) -> None:
        calculator = SilverStatisticsCalculator()
        df = pl.DataFrame({"score": [1.0, 2.0, 3.0], "category": ["a", "a", "b"]})

        distribution = calculator.check_value_distribution(df)
        result = calculator.distribution_to_dict(distribution)

        assert result["status"] == DQCheckStatus.PASS.value
        assert "score" in result["numeric_columns"]
        assert "category" in result["categorical_columns"]
