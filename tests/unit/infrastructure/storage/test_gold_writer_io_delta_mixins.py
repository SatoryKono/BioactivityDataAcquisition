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
"""Unit tests for Gold writer IO Delta mixins and helpers."""

from __future__ import annotations

from tests.helpers.synthetic_paths import synthetic_test_root
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage.gold.io_delta_mixins import (
    _GoldWriterExecutorArrowMixin,
    _SimpleGoldWriteRequest,
    _build_simple_gold_write,
    _gold_write_retry_delay,
    _prepare_scd2_gold_write,
    _run_gold_write_with_retry,
)
from datetime import UTC

TEST_ROOT = synthetic_test_root("bioetl-gold-io-delta")
GOLD_TEST_PATH = str(TEST_ROOT / "gold" / "test")
GOLD_SCD2_PATH = str(TEST_ROOT / "gold" / "scd2")


class _ArrowHost(_GoldWriterExecutorArrowMixin):
    """Minimal concrete host for `_to_arrow_table` regression tests."""

    def __init__(self) -> None:
        self.logger = MagicMock()


@pytest.mark.unit
class TestBuildSimpleGoldWrite:
    """Tests for simple Gold write preparation."""

    def test_build_simple_gold_write_creates_arrow_table(self) -> None:
        """Should convert records to Arrow and wrap in prepared payload."""
        host = MagicMock()
        arrow_table = pa.table({"id": [1, 2], "name": ["a", "b"]})
        host._to_arrow_table.return_value = arrow_table

        request = _SimpleGoldWriteRequest(
            table_path=GOLD_TEST_PATH,
            table_name="test_table",
            records=[{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
            mode="overwrite",
            partition_cols=None,
        )
        prepared = _build_simple_gold_write(host, request)
        assert prepared.arrow_data.num_rows == 2
        assert prepared.schema_mode == "overwrite"

    def test_build_simple_gold_write_append_mode_no_schema_mode(self) -> None:
        """Append mode should set schema_mode to None."""
        host = MagicMock()
        host._to_arrow_table.return_value = pa.table({"id": [1]})

        request = _SimpleGoldWriteRequest(
            table_path=GOLD_TEST_PATH,
            table_name="test_table",
            records=[{"id": 1}],
            mode="append",
            partition_cols=None,
        )
        prepared = _build_simple_gold_write(host, request)
        assert prepared.schema_mode is None

    def test_build_simple_gold_write_sorts_by_primary_keys(self) -> None:
        """Should sort Arrow table by primary keys when specified."""
        host = MagicMock()
        arrow_table = pa.table({"id": [3, 1, 2], "val": ["c", "a", "b"]})
        host._to_arrow_table.return_value = arrow_table

        request = _SimpleGoldWriteRequest(
            table_path=GOLD_TEST_PATH,
            table_name="test_table",
            records=[{"id": 3}, {"id": 1}, {"id": 2}],
            mode="overwrite",
            partition_cols=None,
            primary_keys=["id"],
        )
        prepared = _build_simple_gold_write(host, request)
        assert prepared.arrow_data.column("id").to_pylist() == [1, 2, 3]

    def test_executor_arrow_table_strips_runtime_occurrence_fields(self) -> None:
        """Physical Gold rows should exclude run-scoped provenance columns."""
        host = _ArrowHost()

        arrow_table = host._to_arrow_table(
            [
                {
                    "id": 1,
                    "name": "a",
                    "_run_id": "run-1",
                    "_run_type": "rebuild",
                    "_ingestion_ts": "2024-01-01T00:00:00Z",
                    "_lineage_created_at": "2024-01-01T00:00:00Z",
                }
            ]
        )

        assert arrow_table.column_names == ["id", "name"]


@pytest.mark.unit
class TestGoldWriteRetryDelay:
    """Tests for deterministic retry delay calculation."""

    def test_retry_delay_attempt_0(self) -> None:
        """First retry delay should be 0.5 * 2^0 + 0.05 = 0.55."""
        assert _gold_write_retry_delay(0) == pytest.approx(0.55)

    def test_retry_delay_attempt_1(self) -> None:
        """Second retry delay should be 0.5 * 2^1 + 0.05 = 1.05."""
        assert _gold_write_retry_delay(1) == pytest.approx(1.05)

    def test_retry_delay_attempt_2(self) -> None:
        """Third retry delay should be 0.5 * 2^2 + 0.05 = 2.05."""
        assert _gold_write_retry_delay(2) == pytest.approx(2.05)


@pytest.mark.unit
class TestRunGoldWriteWithRetry:
    """Tests for Gold write retry logic."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self) -> None:
        """Should complete without retry when operation succeeds."""
        module = MagicMock()
        module.GOLD_WRITE_RETRY_ERRORS = (OSError,)
        operation = AsyncMock()

        await _run_gold_write_with_retry(module, operation)
        operation.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(self) -> None:
        """Should retry on retryable errors up to 3 attempts."""
        module = MagicMock()
        module.GOLD_WRITE_RETRY_ERRORS = (OSError,)
        module.asyncio = AsyncMock()
        module.asyncio.sleep = AsyncMock()

        operation = AsyncMock(side_effect=[OSError("fail"), OSError("fail"), None])
        await _run_gold_write_with_retry(module, operation)
        assert operation.await_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        """Should raise the error after 3 failed attempts."""
        module = MagicMock()
        module.GOLD_WRITE_RETRY_ERRORS = (OSError,)
        module.asyncio = AsyncMock()
        module.asyncio.sleep = AsyncMock()

        operation = AsyncMock(side_effect=OSError("persistent failure"))
        with pytest.raises(OSError, match="persistent failure"):
            await _run_gold_write_with_retry(module, operation)


@pytest.mark.unit
class TestPrepareScd2GoldWrite:
    """Tests for SCD2 write preparation."""

    def test_prepare_scd2_gold_write_sorts_by_business_keys(self) -> None:
        """Should sort records by business keys and populate SCD2 fields."""
        from datetime import datetime

        scd_config = MagicMock()
        scd_config.business_keys = ["compound_id"]
        scd_config.entity_key = None
        scd_config.version_col = "_version"
        scd_config.valid_from_col = "_valid_from"
        scd_config.valid_to_col = "_valid_to"
        scd_config.current_flag_col = "_is_current"

        records: list[dict[str, object]] = [
            {"compound_id": "C3", "name": "c"},
            {"compound_id": "C1", "name": "a"},
            {"compound_id": "C2", "name": "b"},
        ]
        ts = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        prepared = _prepare_scd2_gold_write(
            table_path=GOLD_SCD2_PATH,
            records=records,
            scd_config=scd_config,
            partition_cols=None,
            ingestion_ts=ts,
            column_order=None,
        )
        assert [r["compound_id"] for r in prepared.records] == ["C1", "C2", "C3"]
        assert prepared.records[0]["_is_current"] is True
        assert prepared.records[0]["_valid_to"] is None
