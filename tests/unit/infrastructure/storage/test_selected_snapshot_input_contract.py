"""Pinned reads reject unbound producer identity instead of reading latest data."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.workflow.foreign_key_reconciliation_models import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage import workflow_selected_snapshots as snapshots

pytestmark = pytest.mark.unit


def _request(entry):
    return ForeignKeyReconciliationRequest(
        source_table="provider.source",
        reference_table="provider.reference",
        source_key="id",
        reference_key="id",
        primary_keys=("id",),
        source_run_ids=("run",),
        selected_snapshots={"silver:provider.source": entry},
    )


@pytest.mark.parametrize(
    "entry, reason",
    [
        ({"version": 1, "run_ids": ["run"]}, "missing pinned table identity"),
        (
            {"version": 1, "table_id": "table", "run_ids": ["other"]},
            "outside current workflow",
        ),
        (
            {"version": 1, "table_id": "table", "run_ids": []},
            "unbound pinned producer snapshot",
        ),
        (
            {"version": 1, "table_id": "table", "run_ids": [None]},
            "unbound pinned producer snapshot",
        ),
    ],
)
@pytest.mark.asyncio
async def test_unbound_snapshot_is_rejected_before_resolving_storage(entry, reason):
    host = Mock()
    with pytest.raises(ValueError, match=reason):
        await snapshots.read_selected_rows(host, _request(entry), reference=False)
    host.silver_writer._resolve_table_path.assert_not_called()


@pytest.mark.asyncio
async def test_plain_reconciliation_does_not_require_selected_snapshot_versions():
    host = Mock()
    await snapshots.validate_snapshot_versions(host, _request({}))
    host.silver_writer._resolve_table_path.assert_not_called()


@pytest.mark.asyncio
async def test_missing_producer_name_fails_before_table_resolution():
    host = Mock()
    with pytest.raises(ValueError, match="producer identity is missing"):
        await snapshots.capture_pipeline_snapshots(host, "unqualified", "run")
    host.silver_writer._resolve_table_path.assert_not_called()


@pytest.mark.asyncio
async def test_non_delta_writer_cannot_capture_selected_snapshot():
    with pytest.raises(ValueError, match="requires a Delta silver writer"):
        await snapshots.capture_pipeline_snapshots(
            SimpleNamespace(silver_writer=object()), "provider_entity", "run"
        )


@pytest.mark.asyncio
async def test_absent_producer_tables_cannot_certify_completed_run(monkeypatch):
    def missing(path):
        raise TableNotFoundError("producer table missing")

    monkeypatch.setattr(snapshots, "_snapshot_identity", missing)
    writer = SimpleNamespace(_resolve_table_path=lambda name: name)
    with pytest.raises(ValueError, match="persisted no Delta snapshots"):
        await snapshots.capture_pipeline_snapshots(
            SimpleNamespace(silver_writer=writer, gold_writer=writer),
            "provider_entity",
            "run",
        )


@pytest.mark.asyncio
async def test_nonmutating_result_rejects_concurrent_table_change(monkeypatch):
    from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
        build_reconciliation_result,
    )

    request = _request({"version": 1, "table_id": "table", "run_ids": ["run"]})
    result = build_reconciliation_result(
        request,
        scanned_rows=0,
        retained_rows=0,
        orphan_rows_deleted=0,
        mutated=False,
        would_mutate=False,
    )
    monkeypatch.setattr(
        snapshots, "DeltaTable", lambda path: SimpleNamespace(version=lambda: 2)
    )
    writer = SimpleNamespace(_resolve_table_path=lambda name: name)
    with pytest.raises(ValueError, match="changed during non-mutating"):
        await snapshots.selected_result(
            SimpleNamespace(silver_writer=writer), request, result
        )
    assert request.selected_snapshots["silver:provider.source"]["version"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"source_scope": "all_current"},
        {"workflow_run_id": None},
        {"source_run_ids": ()},
        {"selected_snapshots": None},
    ],
)
def test_selected_mode_requires_complete_request_binding(changes):
    request = _request({"version": 1, "table_id": "table", "run_ids": ["run"]})
    bound = replace(request, source_scope="current_run", workflow_run_id="workflow")
    with pytest.raises(ValueError, match="selected-snapshot requires"):
        replace(bound, reconciliation_mode="selected-snapshot", **changes)


@pytest.mark.asyncio
async def test_pinned_table_with_inconsistent_row_identity_cannot_fall_back_to_whole_table(
    monkeypatch,
):
    table = SimpleNamespace(
        column_names=["run_id", "id"],
        to_pylist=lambda: [{"id": "entity"}],
    )
    opened = Mock(return_value=SimpleNamespace(to_pyarrow_table=lambda: table))
    monkeypatch.setattr(snapshots, "DeltaTable", opened)
    writer = SimpleNamespace(_resolve_table_path=lambda name: name)
    request = _request({"version": 1, "table_id": "table", "run_ids": ["run"]})
    with pytest.raises(ValueError, match="selected snapshot row scope unbound"):
        await snapshots.read_selected_rows(
            SimpleNamespace(silver_writer=writer), request, reference=False
        )
    opened.assert_called_once_with("provider.source", version=1)
