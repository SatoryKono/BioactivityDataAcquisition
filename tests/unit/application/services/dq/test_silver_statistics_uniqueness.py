# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Focused unit tests for silver_statistics_uniqueness."""

from __future__ import annotations

import polars as pl
import pytest

from bioetl.application.services.dq.silver_statistics_uniqueness import (
    _profile_column_cardinality,
    check_uniqueness_stats,
)
from bioetl.domain.value_objects.dq_report import DQCheckStatus

pytestmark = [
    pytest.mark.unit,
    pytest.mark.require_silver_validator,
]


class TestSilverStatisticsUniqueness:
    """Direct tests for uniqueness statistics helpers."""

    def test_warns_when_primary_keys_missing(self) -> None:
        df = pl.DataFrame({"entity_id": ["e1", "e2"]})

        result = check_uniqueness_stats(df, ["missing_id"], (RuntimeError,))

        assert result.status == DQCheckStatus.WARN
        assert result.primary_key == "missing_id"
        assert (
            result.column_stats["_note"]["message"] == "Primary key columns not found"
        )

    def test_calculates_duplicate_rate_and_column_stats(self) -> None:
        df = pl.DataFrame({"entity_id": ["e1", "e1", "e2"], "source": ["a", "a", "b"]})

        result = check_uniqueness_stats(df, ["entity_id"], (RuntimeError,))

        assert result.status == DQCheckStatus.WARN
        assert result.unique_count == 2
        assert result.total_count == 3
        assert result.duplicate_rate == round(1 / 3, 4)
        assert "entity_id" in result.column_stats

    def test_passes_when_primary_keys_empty(self) -> None:
        df = pl.DataFrame({"entity_id": ["e1", "e2"]})

        result = check_uniqueness_stats(df, [], (RuntimeError,))

        assert result.status == DQCheckStatus.PASS
        assert result.primary_key == ""
        assert result.unique_count == 2
        assert result.duplicate_rate == pytest.approx(0.0)

    def test_handles_empty_frame_with_key(self) -> None:
        df = pl.DataFrame({"entity_id": []}, schema={"entity_id": pl.String})

        result = check_uniqueness_stats(df, ["entity_id"], (RuntimeError,))

        assert result.status == DQCheckStatus.PASS
        assert result.total_count == 0
        assert result.duplicate_rate == pytest.approx(0.0)
        assert result.column_stats["entity_id"]["uniqueness_ratio"] == pytest.approx(
            0.0
        )

    def test_profile_column_cardinality_empty_column_list(self) -> None:
        df = pl.DataFrame({"entity_id": ["e1"]})
        assert _profile_column_cardinality(df, [], 1, (RuntimeError,)) == {}

    def test_profile_column_cardinality_uses_fallback_and_skips_errors(self) -> None:
        df = pl.DataFrame({"entity_id": ["e1", "e2"]})

        class _BoomFrame:
            def __init__(self, inner: pl.DataFrame) -> None:
                self._inner = inner

            def select(self, *_args: object, **_kwargs: object) -> pl.DataFrame:
                raise RuntimeError("vectorized n_unique failed")

            def __getitem__(self, key: str) -> object:
                if key == "skip_me":
                    raise RuntimeError("column profile failed")
                return self._inner[key]

        stats = _profile_column_cardinality(
            _BoomFrame(df),  # type: ignore[arg-type]
            ["entity_id", "skip_me"],
            2,
            (RuntimeError,),
        )
        assert stats["entity_id"]["cardinality"] == 2
        assert "skip_me" not in stats
