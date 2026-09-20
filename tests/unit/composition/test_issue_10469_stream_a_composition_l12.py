"""Stream A L12 composition residuals for #10469 / #10516."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.providers._chembl_target_protein_classification_data_source import (
    TargetProteinClassificationSnapshotDataSource,
)


pytestmark = pytest.mark.unit


class _Issue:
    component_id = 10
    error_code = "missing_leaf"
    message = "no classification path"


@pytest.mark.asyncio
async def test_snapshot_loader_double_checked_lock_returns_when_already_loaded() -> (
    None
):
    data_source = TargetProteinClassificationSnapshotDataSource(
        delta_reader=MagicMock(),
        logger=MagicMock(),
    )
    data_source._loaded = False
    await data_source._load_lock.acquire()
    task = asyncio.create_task(data_source._ensure_loaded())
    for _ in range(32):
        await asyncio.sleep(0)
        if not task.done():
            break
    data_source._loaded = True
    data_source._load_lock.release()
    await task
    assert data_source._loaded is True


def test_relation_rows_log_dq_issues_for_unresolved_target() -> None:
    data_source = TargetProteinClassificationSnapshotDataSource(
        delta_reader=MagicMock(),
        logger=MagicMock(),
    )
    data_source._loaded = True
    data_source._source_manifest = {"source_url": "https://example.test"}
    data_source._target_component_ids = {"CHEMBL_T1": (10,)}
    data_source._resolution_service = SimpleNamespace(
        resolve_target=lambda **_kwargs: SimpleNamespace(dq_issues=[_Issue()], rows=())
    )

    rows = data_source._relation_rows_for_target("CHEMBL_T1")

    assert rows == ()
    data_source._logger.warning.assert_called_once()
    assert data_source._logger.warning.call_args.kwargs["target_id"] == "CHEMBL_T1"
