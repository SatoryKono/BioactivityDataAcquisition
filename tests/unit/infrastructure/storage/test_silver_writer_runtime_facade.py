"""Unit tests for Silver writer runtime facade helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.infrastructure.storage.silver.pipeline_helpers import (
    _SilverWriteExecutionContext,
)
from bioetl.infrastructure.storage.silver.writer_runtime_facade import (
    SilverWriterRuntimeFacade,
)


@dataclass(frozen=True, slots=True)
class _Payload:
    """Minimal prepared payload for facade delegation tests."""

    records: list[dict[str, object]]


class _Facade(SilverWriterRuntimeFacade):
    """Concrete runtime facade for isolated testing."""

    def __init__(self) -> None:
        self._delta = None
        self._postwrite = None
        self._merged = None
        self._host = None
        self._validation = None
        self._should_dual_write = MagicMock(return_value=False)
        self._write_single_target = AsyncMock(return_value="single")
        self._write_dual_targets = AsyncMock(return_value="dual")
        self._prepare_silver_write_payload = AsyncMock(
            return_value=_Payload(records=[])
        )


@pytest.mark.unit
class TestSilverWriterRuntimeFacade:
    """Focused coverage for runtime facade delegation and guard rails."""

    @pytest.mark.asyncio
    async def test_dispatch_write_requires_delta_operations(self) -> None:
        facade = _Facade()
        with pytest.raises(RuntimeError, match="Silver Delta operations are required"):
            await facade._dispatch_write_with_domain_errors(
                table_name="chembl.activity",
                request=MagicMock(),
            )

    @pytest.mark.asyncio
    async def test_complete_pipeline_requires_postwrite_operations(self) -> None:
        facade = _Facade()
        ctx = MagicMock(spec=_SilverWriteExecutionContext)
        with pytest.raises(
            RuntimeError, match="Silver postwrite operations are required"
        ):
            await facade._complete_silver_write_pipeline(
                ctx=ctx,
                payload=_Payload(records=[]),
            )

    @pytest.mark.asyncio
    async def test_write_merged_requires_merged_operations(self) -> None:
        facade = _Facade()
        with pytest.raises(RuntimeError, match="Silver merged operations are required"):
            await facade.write_silver_merged("chembl.activity", [{"entity_id": "1"}])

    @pytest.mark.asyncio
    async def test_write_silver_routes_to_single_or_dual_target(self) -> None:
        facade = _Facade()
        invocation = MagicMock(
            table_name="chembl.activity",
            run_id="run-1",
            run_type="incremental",
            source_batch_id="batch-1",
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        )

        with patch(
            "bioetl.infrastructure.storage.silver.writer_runtime_facade._coerce_silver_write_invocation",
            return_value=invocation,
        ):
            assert await facade.write_silver(table_name="chembl.activity") == "single"

        facade._should_dual_write.return_value = True
        with patch(
            "bioetl.infrastructure.storage.silver.writer_runtime_facade._coerce_silver_write_invocation",
            return_value=invocation,
        ):
            assert await facade.write_silver(table_name="chembl.activity") == "dual"

    @pytest.mark.asyncio
    async def test_write_merged_metadata_and_pipeline_delegate_to_helpers(self) -> None:
        facade = _Facade()
        invocation = MagicMock()
        ctx = MagicMock(spec=_SilverWriteExecutionContext)

        with (
            patch(
                "bioetl.infrastructure.storage.silver.writer_runtime_facade._write_merged_metadata_via_operations",
                new=AsyncMock(),
            ) as write_merged,
            patch(
                "bioetl.infrastructure.storage.silver.writer_runtime_facade.execute_silver_write_pipeline",
                new=AsyncMock(return_value="done"),
            ) as execute_pipeline,
        ):
            await facade._write_silver_merged_metadata(
                table_path="/tmp/silver/chembl/activity",
                table_name="chembl.activity",
                records=[{"entity_id": "1"}],
                primary_keys=["entity_id"],
            )
            result = await facade._execute_silver_write_pipeline(
                invocation=invocation,
                ctx=ctx,
            )

        write_merged.assert_awaited_once()
        execute_pipeline.assert_awaited_once()
        assert result == "done"
