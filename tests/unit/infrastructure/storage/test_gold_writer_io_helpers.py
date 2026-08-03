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
"""Unit tests for Gold writer IO helper functions."""

from __future__ import annotations

import asyncio
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage.gold.io_helpers import (
    initialize_scd2_records,
    write_scd2_once,
)

TEST_SCD2_PATH = "test-output/gold/scd2"


@pytest.mark.unit
class TestInitializeScd2Records:
    """Tests for SCD2 metadata field initialization."""

    def test_populates_scd2_fields(self) -> None:
        """Should set valid_from, valid_to, current_flag, and version on records."""
        scd_config = MagicMock()
        scd_config.version_col = "_version"
        scd_config.valid_from_col = "_valid_from"
        scd_config.valid_to_col = "_valid_to"
        scd_config.current_flag_col = "_is_current"

        ts = datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC)
        records: list[dict[str, object]] = [{"id": 1}, {"id": 2}]

        initialize_scd2_records(records, scd_config, ts)

        for record in records:
            assert record["_valid_from"] == ts.isoformat()
            assert record["_valid_to"] is None
            assert record["_is_current"] is True
            assert record["_version"] == 1

    def test_preserves_existing_version(self) -> None:
        """Should keep existing version value when already set."""
        scd_config = MagicMock()
        scd_config.version_col = "_version"
        scd_config.valid_from_col = "_valid_from"
        scd_config.valid_to_col = "_valid_to"
        scd_config.current_flag_col = "_is_current"

        ts = datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC)
        records: list[dict[str, object]] = [{"id": 1, "_version": 5}]

        initialize_scd2_records(records, scd_config, ts)
        assert records[0]["_version"] == 5


@pytest.mark.unit
class TestWriteScd2Once:
    """Tests for single SCD2 write attempt."""

    @pytest.mark.asyncio
    async def test_merge_path_when_table_exists(self) -> None:
        """Should load DeltaTable and call _merge_scd2 when table exists."""
        writer = AsyncMock()
        dt_mock = MagicMock()
        writer._run_in_executor = AsyncMock(return_value=dt_mock)
        writer._merge_scd2 = AsyncMock()

        module = MagicMock()
        ts = datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC)
        scd_config = MagicMock()
        scd_config.business_keys = ["id"]

        await write_scd2_once(
            writer,
            module=module,
            table_path=TEST_SCD2_PATH,
            records=[{"id": 1}],
            business_key="id",
            scd_config=scd_config,
            ingestion_ts=ts,
            partition_cols=None,
            column_order=None,
        )
        writer._merge_scd2.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_path_when_table_not_found(self) -> None:
        """Should write fresh table when TableNotFoundError is raised."""
        writer = MagicMock()
        module = MagicMock()
        module.TableNotFoundError = type("TableNotFoundError", (Exception,), {})

        call_count = 0

        async def mock_run_in_executor(func, *args):  # type: ignore[no-untyped-def]
            await asyncio.sleep(0)
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise module.TableNotFoundError()
            return func(*args) if args else func()

        writer._run_in_executor = mock_run_in_executor
        arrow_table = pa.table({"id": [1], "name": ["a"]})
        writer._to_arrow_table = MagicMock(return_value=arrow_table)

        ts = datetime(2025, 6, 1, 10, 0, 0, tzinfo=UTC)
        scd_config = MagicMock()
        scd_config.business_keys = ["id"]

        await write_scd2_once(
            writer,
            module=module,
            table_path=TEST_SCD2_PATH,
            records=[{"id": 1}],
            business_key="id",
            scd_config=scd_config,
            ingestion_ts=ts,
            partition_cols=None,
            column_order=None,
        )
        writer._to_arrow_table.assert_called_once()
