"""Missing-artifact and path contracts for metadata writer coordination."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.storage import metadata_writer_operations_impl as operations
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy
from bioetl.infrastructure.storage.metadata.writer_operations import (
    _MetadataWriteRequest,
)
from bioetl.infrastructure.storage.metadata_writer_helpers import (
    _load_existing_metadata_model,
    _resolve_existing_metadata_path,
)
from bioetl.infrastructure.storage.metadata_writer_operations_impl import (
    _MetadataWriterOperations,
)

pytestmark = pytest.mark.unit


def _metadata_operations() -> _MetadataWriterOperations:
    return _MetadataWriterOperations(
        logger=MagicMock(name="logger"),
        metrics=None,
        retry_policy=AdaptiveRetryPolicy(
            enabled=False,
            max_retries=0,
            base_delay_seconds=0.0,
            max_delay_seconds=0.0,
        ),
        artifact_recorder_provider=lambda: None,
    )


def test_load_existing_metadata_returns_none_for_missing_or_non_mapping_payload(
    tmp_path: Path,
) -> None:
    """Absent and structurally invalid sidecars are not treated as metadata models."""
    missing_path = tmp_path / "missing.yaml"
    sequence_path = tmp_path / "sequence.yaml"
    sequence_path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    assert _load_existing_metadata_model(missing_path, layer="silver") is None
    assert _load_existing_metadata_model(sequence_path, layer="silver") is None


def test_existing_metadata_path_honors_scoped_and_flat_layouts(
    tmp_path: Path,
) -> None:
    """Reader lookup mirrors both writer filename conventions."""
    scoped = _resolve_existing_metadata_path(
        base_path=tmp_path,
        layer="bronze",
        provider="chembl",
        entity="activity",
    )
    flat = _resolve_existing_metadata_path(
        base_path=tmp_path,
        layer="silver",
        table_name="chembl_activity",
        flat_structure=True,
    )

    assert scoped == tmp_path / "chembl_activity_metadata.yaml"
    assert flat == tmp_path / "chembl_activity_metadata.yaml"


@pytest.mark.asyncio
async def test_finalize_existing_metadata_is_noop_when_sidecar_is_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finalization does not create a sidecar when there is nothing to patch."""
    metadata_path = tmp_path / "_metadata.yaml"
    load = AsyncMock(return_value=None)
    monkeypatch.setattr(
        operations,
        "_resolve_existing_metadata_path",
        MagicMock(return_value=metadata_path),
    )
    monkeypatch.setattr(operations, "load_existing_metadata_model", load)
    apply_finalization = MagicMock()

    result = await _metadata_operations().finalize_existing_layer_metadata(
        base_path=tmp_path,
        layer="silver",
        apply_finalization=apply_finalization,
    )

    assert result is None
    load.assert_awaited_once_with(metadata_path, layer="silver")
    apply_finalization.assert_not_called()


@pytest.mark.asyncio
async def test_write_metadata_prepares_and_executes_one_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The coordinator passes the normalized request to the atomic executor."""
    metadata = cast(Any, MagicMock(name="metadata"))
    request = _MetadataWriteRequest(
        base_path=tmp_path,
        metadata=metadata,
        layer="silver",
    )
    prepared = cast(Any, MagicMock(name="prepared_operation"))
    prepare = MagicMock(return_value=prepared)
    execute = AsyncMock(return_value=str(tmp_path / "_metadata.yaml"))
    monkeypatch.setattr(operations, "_prepare_metadata_write_operation", prepare)
    monkeypatch.setattr(
        operations,
        "_execute_prepared_metadata_write_operation",
        execute,
    )
    writer = _metadata_operations()

    result = await writer.write_metadata(request)

    assert result == str(tmp_path / "_metadata.yaml")
    prepare.assert_called_once_with(request)
    execute.assert_awaited_once_with(
        logger=writer._logger,
        metrics=writer._metrics,
        retry_policy=writer._retry_policy,
        operation=prepared,
        metadata=metadata,
    )
