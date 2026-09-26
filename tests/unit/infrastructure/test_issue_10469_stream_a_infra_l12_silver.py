"""L12 residuals for silver/* modules only. Do not import gold_writer."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage.silver.operations.merged_operations import (
    _MergedWriteFacade,
)
from bioetl.infrastructure.storage.silver.operations.metadata_context_facade import (
    _SilverMetadataContextFacade,
)
from bioetl.infrastructure.storage.silver.operations.metadata_dq_operations import (
    resolve_silver_manifest_id,
    resolve_version_after_operation,
)
from bioetl.infrastructure.storage.silver.operations.metadata_runtime_support import (
    write_silver_metadata_file,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_facade import (
    _SilverMetadataWriteFacade,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_operations import (
    write_silver_merged_metadata_operation,
)
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
    _build_validation_operations,
)
from bioetl.infrastructure.storage.silver.schema_drift_operations import (
    _detect_schema_drift,
)
from bioetl.infrastructure.storage.silver.writer_metadata_facade import (
    SilverWriterMetadataFacade,
)
from bioetl.infrastructure.storage.silver.writer_runtime_invocation import (
    _validate_single_target_compat,
    _write_merged_metadata_via_operations,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_merged_write_facade_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    executed = AsyncMock()
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.operations.merged_operations._execute_merged_silver_write_flow",
        executed,
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.operations.merged_operations._build_merged_silver_write_request",
        lambda **kwargs: kwargs,
    )

    class _Host(_MergedWriteFacade):
        pass

    await _Host().write_silver_merged("activity", [{"id": "1"}], ["id"])
    executed.assert_awaited()


def test_resolve_manifest_and_version_wrappers() -> None:
    ops = SimpleNamespace(_host=None, _metadata_coordinator=None, _logger=MagicMock())
    assert resolve_silver_manifest_id(ops, records=[]) is None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_resolve_version_after_wrapper() -> None:
    ops = SimpleNamespace(_host=None, _get_delta_version=None, _logger=MagicMock())
    monkeypatch_result = AsyncMock(return_value=7)
    from bioetl.infrastructure.storage.silver.operations import (
        metadata_dq_operations as dq,
    )

    original = dq.resolve_version_after
    dq.resolve_version_after = monkeypatch_result  # type: ignore[assignment]
    try:
        assert await resolve_version_after_operation(ops, "path") == 7  # type: ignore[arg-type]
    finally:
        dq.resolve_version_after = original  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_write_silver_metadata_file_unknown_writer() -> None:
    ops = SimpleNamespace(
        _metadata_writer=SimpleNamespace(write_silver_metadata=None),
        _logger=MagicMock(),
        _flat_structure=False,
    )
    with pytest.raises(TypeError, match="write_silver_metadata"):
        await write_silver_metadata_file(
            ops,  # type: ignore[arg-type]
            table_path="p",
            metadata=MagicMock(),
            table_name="activity",
            provider_name="chembl",
            entity_name="activity",
        )


@pytest.mark.asyncio
async def test_metadata_write_facade_finalize(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.operations.metadata_write_facade.finalize_silver_write_result_operation",
        AsyncMock(return_value=None),
    )
    facade = _SilverMetadataWriteFacade()
    assert await facade._finalize_silver_write_result(MagicMock()) is None


@pytest.mark.asyncio
async def test_merged_metadata_skip_return() -> None:
    ops = SimpleNamespace(
        _should_skip_silver_metadata_write=lambda **_kwargs: True,
    )
    execute = AsyncMock()
    await write_silver_merged_metadata_operation(
        ops,  # type: ignore[arg-type]
        table_path="p",
        table_name="activity",
        records=[{"id": "1"}],
        primary_keys=["id"],
        execute_silver_metadata_write=execute,
    )
    execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_context_facade_manifest_and_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.operations.metadata_context_facade.resolve_silver_manifest_id",
        lambda *_args, **_kwargs: "manifest-1",
    )
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.operations.metadata_context_facade.resolve_version_after_operation",
        AsyncMock(return_value=3),
    )
    facade = _SilverMetadataContextFacade()
    assert facade._resolve_manifest_id(records=[]) == "manifest-1"
    assert await facade._resolve_version_after("path") == 3


def test_build_validation_operations_without_base_path() -> None:
    request = SilverWriterRuntimeServicesRequest(base_path=None)
    assert (
        _build_validation_operations(
            request,
            write_policy=MagicMock(),
            silver_validator=MagicMock(),
        )
        is None
    )


@pytest.mark.asyncio
async def test_detect_schema_drift_no_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.schema_drift_operations._build_silver_schema_drift_diff",
        lambda *_args, **_kwargs: None,
    )

    class _Host:
        async def _get_table_schema(self, _table_name: str) -> pa.Schema:
            return pa.schema([("id", pa.string())])

    assert await _detect_schema_drift(_Host(), "activity", [{"id": "1"}]) is None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_writer_metadata_facade_skip_and_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = SilverWriterMetadataFacade()
    facade._metadata = SimpleNamespace()  # type: ignore[assignment]
    facade._should_skip_silver_metadata_write = lambda **_kwargs: True  # type: ignore[method-assign]
    await facade._write_silver_metadata(MagicMock(records=[{"id": "1"}]))

    written = AsyncMock()
    facade._metadata = SimpleNamespace(_write_silver_metadata_file=written)  # type: ignore[assignment]
    await facade._write_silver_metadata_file(
        table_path="p",
        metadata=MagicMock(),
        table_name="activity",
        provider_name="chembl",
        entity_name="activity",
    )
    written.assert_awaited()


def test_validate_single_target_ingestion_mismatch() -> None:
    invocation = SimpleNamespace(
        table_name="activity",
        run_id="r1",
        run_type="incremental",
        source_batch_id="b1",
        ingestion_ts="ts-1",
    )
    with pytest.raises(TypeError, match="ingestion_ts"):
        _validate_single_target_compat(
            invocation=invocation,  # type: ignore[arg-type]
            table_name=None,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts="ts-other",
        )


@pytest.mark.asyncio
async def test_write_merged_metadata_skips_when_flagged() -> None:
    writer = SimpleNamespace(
        _metadata=object(),
        _should_skip_silver_metadata_write=lambda **_kwargs: True,
    )
    await _write_merged_metadata_via_operations(
        writer,
        table_path="p",
        table_name="activity",
        records=[{"id": "1"}],
        primary_keys=["id"],
    )
