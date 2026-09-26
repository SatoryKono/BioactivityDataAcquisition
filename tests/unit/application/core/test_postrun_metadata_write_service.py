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
"""Focused tests for the postrun metadata write service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.postrun.metadata_write_service import (
    PostrunMetadataWriteService,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.types import RunType
from tests.helpers.clock import FixedClock


def _make_config() -> PipelineConfig:
    return PipelineConfig(
        pipeline_name="test_postrun_pipeline",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(
            primary_keys=("activity_id",),
            silver_table="silver_table",
            gold_table="gold_table",
        ),
    )


def _make_runtime() -> RuntimeConfig:
    return RuntimeConfig(run_type=RunType.INCREMENTAL, skip_gold=True)


def _make_context() -> MagicMock:
    context = MagicMock()
    context.started_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return context


FIXED_COMPLETED_AT = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)


@pytest.mark.unit
class TestPostrunMetadataWriteService:
    """Tests for final metadata-write orchestration."""

    @pytest.mark.asyncio
    async def test_write_final_metadata_if_available_skips_without_targets(
        self,
    ) -> None:
        """Missing metadata ports should short-circuit the write flow."""
        storage = MagicMock()
        metadata_version_resolver = MagicMock()
        service = PostrunMetadataWriteService(
            config=_make_config(),
            runtime=_make_runtime(),
            context=_make_context(),
            storage=storage,
            metadata_coordinator=None,
            metadata_writer=None,
            metadata_version_resolver=metadata_version_resolver,
        )

        wrote_metadata = await service.write_final_metadata_if_available(
            MagicMock(),
            dq_reports=None,
        )

        storage.get_table_path.assert_not_called()
        metadata_version_resolver.resolve_delta_version.assert_not_called()
        assert wrote_metadata is False

    @pytest.mark.asyncio
    async def test_write_final_metadata_if_available_writes_silver_outputs(
        self,
    ) -> None:
        """Configured metadata writer should finalize Silver sidecars."""
        storage = MagicMock()
        storage.get_table_path = MagicMock(return_value="test-output/test_silver")
        storage.is_table_initialized = MagicMock(return_value=True)

        metadata_coordinator = MagicMock()
        metadata_writer = MagicMock()
        metadata_writer.finalize_silver_metadata = AsyncMock(return_value="silver.yaml")
        metadata_writer.finalize_gold_metadata = AsyncMock(return_value="gold.yaml")
        metadata_version_resolver = MagicMock()
        metadata_version_resolver.resolve_delta_version = MagicMock(return_value=7)

        service = PostrunMetadataWriteService(
            config=_make_config(),
            runtime=_make_runtime(),
            context=_make_context(),
            storage=storage,
            metadata_coordinator=metadata_coordinator,
            metadata_writer=metadata_writer,
            metadata_version_resolver=metadata_version_resolver,
            clock=FixedClock(FIXED_COMPLETED_AT),
        )
        executor = MagicMock()
        executor.get_run_statistics = MagicMock(
            return_value={"records_silver": 5, "source_batch_ids": ["batch-1"]}
        )

        wrote_metadata = await service.write_final_metadata_if_available(
            executor,
            dq_reports=None,
        )

        metadata_coordinator.create_silver_metadata.assert_not_called()
        metadata_writer.finalize_silver_metadata.assert_awaited_once()
        metadata_writer.finalize_gold_metadata.assert_not_awaited()
        metadata_version_resolver.resolve_delta_version.assert_called_once()
        assert wrote_metadata is True

    @pytest.mark.asyncio
    async def test_write_final_metadata_without_clock_uses_deterministic_sentinel(
        self,
    ) -> None:
        storage = MagicMock()
        storage.get_table_path = MagicMock(return_value="test-output/test_silver")
        storage.is_table_initialized = MagicMock(return_value=True)

        metadata_coordinator = MagicMock()
        metadata_writer = MagicMock()
        metadata_writer.finalize_silver_metadata = AsyncMock(return_value="silver.yaml")
        metadata_version_resolver = MagicMock()
        metadata_version_resolver.resolve_delta_version = MagicMock(return_value=7)

        service = PostrunMetadataWriteService(
            config=_make_config(),
            runtime=_make_runtime(),
            context=_make_context(),
            storage=storage,
            metadata_coordinator=metadata_coordinator,
            metadata_writer=metadata_writer,
            metadata_version_resolver=metadata_version_resolver,
        )
        executor = MagicMock()
        executor.get_run_statistics = MagicMock(
            return_value={"records_silver": 5, "source_batch_ids": ["batch-1"]}
        )

        await service.write_final_metadata_if_available(executor, dq_reports=None)

        silver_call = metadata_writer.finalize_silver_metadata.await_args
        assert silver_call.kwargs["completed_at"] == MISSING_RUNTIME_TIMESTAMP
