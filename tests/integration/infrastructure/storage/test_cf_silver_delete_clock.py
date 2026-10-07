"""Real Delta replacement and injected Silver provenance-clock acceptance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pyarrow as pa
import pytest
from deltalake import DeltaTable

from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_result_finalization import (
    _prepare_silver_write_finalization_context,
)
from tests.helpers.clock import StepClock, fixed_test_clock

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_delete_atomically_replaces_real_delta_and_preserves_old_version(
    tmp_path,
):
    writer = SilverWriter(tmp_path, Mock(), clock=fixed_test_clock())
    schema = pa.schema([("id", pa.string()), ("content_hash", pa.string())])
    first = [{"id": "old", "content_hash": "a" * 64}]
    second = [{"id": "new", "content_hash": "b" * 64}]
    await writer.write_silver(
        table_name="test_activity",
        records=first,
        primary_keys=["id"],
        schema=schema,
        mode="append",
    )
    path = str(tmp_path / "test_activity")
    version = DeltaTable(path).version()
    await writer.write_silver(
        table_name="test_activity",
        records=second,
        primary_keys=["id"],
        schema=schema,
        mode="delete",
    )
    current = DeltaTable(path)
    assert current.version() == version + 1
    assert current.to_pyarrow_table().to_pylist() == second
    assert DeltaTable(path, version=version).to_pyarrow_table().to_pylist() == first
    with pytest.raises(ValueError, match="Invalid Silver write mode"):
        await writer.write_silver(
            table_name="test_activity",
            records=first,
            primary_keys=["id"],
            schema=schema,
            mode="overwrite",
        )
    assert DeltaTable(path).version() == version + 1


@pytest.mark.asyncio
async def test_injected_clock_controls_start_and_completion_without_wallclock_patch(
    tmp_path,
):
    start = datetime(2026, 10, 7, tzinfo=UTC)
    writer = SilverWriter(
        tmp_path, Mock(), clock=StepClock(start, timedelta(seconds=2))
    )
    seen = []

    async def capture(*, invocation, ctx):
        seen.append((invocation.started_at, ctx.started_at))
        return None

    writer._execute_silver_write_pipeline = capture
    await writer.write_silver(
        table_name="test_activity",
        records=[{"id": "1"}],
        primary_keys=["id"],
        schema=pa.schema([("id", pa.string())]),
    )
    assert seen == [(start, start)]
    # Real metadata operations carry the exact writer clock even with explicit runtime services.
    request = _SilverWriteFinalizationPreparationRequest(
        "test_activity", [], str(tmp_path), start, 123456.0
    )
    ops = writer._metadata
    from unittest.mock import AsyncMock

    ops._host._compute_dq_metrics = AsyncMock(return_value=Mock())
    ops._host._get_delta_version = AsyncMock(return_value=1)
    context = await _prepare_silver_write_finalization_context(
        ops, request, perf_counter=lambda: 1e9
    )
    assert context.completed_at == start + timedelta(seconds=2)
    explicit = start - timedelta(days=1)
    await writer.write_silver(
        table_name="test_activity",
        records=[{"id": "1"}],
        primary_keys=["id"],
        schema=pa.schema([("id", pa.string())]),
        started_at=explicit,
    )
    assert seen[-1] == (explicit, explicit)


def test_clock_is_required(tmp_path):
    with pytest.raises(TypeError, match="clock"):
        SilverWriter(tmp_path, Mock())


@pytest.mark.asyncio
@pytest.mark.parametrize("explicit_start", [False, True])
async def test_real_delta_metadata_records_injected_clock_provenance(
    tmp_path, explicit_start
):
    from uuid import UUID
    from unittest.mock import AsyncMock
    from bioetl.application.services.lineage import MetadataCoordinator
    from bioetl.domain.value_objects.run_context import RunContext
    from bioetl.domain.types import RunType
    from bioetl.infrastructure.storage.silver.runtime_helpers import (
        SilverWriterRuntimeServicesRequest,
    )

    start = datetime(2026, 10, 7, tzinfo=UTC)
    coordinator = MetadataCoordinator(
        RunContext.create(
            run_id=UUID("00000000-0000-0000-0000-000000012016"),
            run_type=RunType.INCREMENTAL,
            started_at=start - timedelta(days=2),
            provider="test",
            entity="activity",
            manifest_id="manifest-canonical",
            execution_fingerprint="fingerprint-canonical",
            effective_config_hash="effective-config-canonical",
            effective_config_artifact_id="effective-config-artifact-canonical",
            contract_ref="contracts/test/activity",
            contract_version="1.0.0",
            dq_contract_compatibility_hash="dq-compat-canonical",
        )
    )
    metadata_writer = Mock()
    metadata_writer.write_silver_metadata = AsyncMock()
    clock = StepClock(start, timedelta(seconds=2))
    writer = SilverWriter(
        tmp_path,
        Mock(),
        clock=clock,
        runtime_request=SilverWriterRuntimeServicesRequest(
            clock=fixed_test_clock(),
            metadata_writer=metadata_writer,
            metadata_coordinator=coordinator,
        ),
    )
    arguments = {"started_at": start - timedelta(days=1)} if explicit_start else {}
    await writer.write_silver(
        table_name="test_activity",
        records=[{"id": "new", "content_hash": "b" * 64}],
        primary_keys=["id"],
        schema=pa.schema([("id", pa.string()), ("content_hash", pa.string())]),
        mode="delete",
        **arguments,
    )
    metadata_writer.write_silver_metadata.assert_awaited_once()
    metadata = metadata_writer.write_silver_metadata.call_args.kwargs["metadata"]
    assert metadata.runtime.started_at_utc == (
        start - timedelta(days=1) if explicit_start else start
    )
    assert metadata.runtime.completed_at_utc == (
        start if explicit_start else start + timedelta(seconds=2)
    )
    assert metadata.delta.operation == "overwrite"
    assert (
        metadata.output_ext.delta_version_after
        == DeltaTable(str(tmp_path / "test_activity")).version()
    )
