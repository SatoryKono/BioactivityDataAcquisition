"""Bounded reconciliation mutates only pinned producer rows, preserving history."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest
from deltalake import DeltaTable, write_deltalake

from bioetl.domain.workflow.foreign_key_reconciliation_models import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    StorageForeignKeyReconciliationAdapter,
)

pytestmark = pytest.mark.integration

SCHEMA = pa.schema(
    [
        ("id", pa.string()),
        ("fk", pa.string()),
        ("_run_id", pa.string()),
        ("_is_current", pa.bool_()),
        ("_valid_to", pa.string()),
    ]
)
WORKFLOW_ID = "00000000-0000-0000-0000-000000000001"


class Writer:
    def __init__(self, root):
        self.root = root

    def _resolve_table_path(self, name):
        return str(self.root / name)

    async def _run_in_executor(self, fn, *args):
        return await asyncio.to_thread(fn, *args)

    async def read_gold(self, name, columns=None, current_only=True):
        rows = DeltaTable(self._resolve_table_path(name)).to_pyarrow_table().to_pylist()
        return [r for r in rows if not current_only or r["_is_current"]]


def row(id, fk, run_id="producer", current=True):
    return {
        "id": id,
        "fk": fk,
        "_run_id": run_id,
        "_is_current": current,
        "_valid_to": "",
    }


@pytest.fixture
def storage(tmp_path):
    writer = Writer(tmp_path / "gold")
    quarantine = SimpleNamespace(write_many=AsyncMock())
    clock = SimpleNamespace(now=lambda: datetime(2026, 10, 2, tzinfo=UTC))
    return StorageForeignKeyReconciliationAdapter(
        silver_writer=Writer(tmp_path / "silver"),
        gold_writer=writer,
        logger=MagicMock(),
        clock=clock,
        quarantine=quarantine,
    )


def write(storage, name, rows):
    write_deltalake(
        storage.gold_writer._resolve_table_path(name),
        pa.Table.from_pylist(rows, schema=SCHEMA),
        mode="overwrite",
    )


async def request(storage, *, reference=(), source=None, dry_run=False):
    write(storage, "test.source", source if source is not None else [row("a", "x")])
    write(storage, "test.reference", list(reference))
    snapshots = await storage.capture_pipeline_snapshots("test_source", "producer")
    snapshots.update(
        await storage.capture_pipeline_snapshots("test_reference", "producer")
    )
    return ForeignKeyReconciliationRequest(
        source_table="test.source",
        reference_table="test.reference",
        source_key="fk",
        reference_key="id",
        primary_keys=("id",),
        source_layer="gold",
        reference_layer="gold",
        source_scope="current_run",
        source_run_ids=("producer",),
        workflow_run_id=WORKFLOW_ID,
        reconciliation_mode="selected-snapshot",
        selected_snapshots=snapshots,
        dry_run=dry_run,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("matched", [False, True])
async def test_partial_and_total_deletion_preserve_other_runs_and_history(
    storage, matched
):
    selected = [row("a", "x"), row("b", "y")]
    untouched = [row("old", "absent", "history"), row("a", "z", "history", False)]
    req = await request(
        storage,
        source=selected + untouched,
        reference=[row("x", "", "producer")] if matched else [],
    )
    result = await storage.reconcile_foreign_keys(req)
    assert result.scanned_rows == 2
    assert result.retained_rows == int(matched)
    assert result.orphan_rows_deleted == 2 - int(matched)
    assert result.reference_completeness == "unproven"
    assert result.reconciliation_mode == "selected-snapshot"
    actual = (
        DeltaTable(storage.gold_writer._resolve_table_path("test.source"))
        .to_pyarrow_table()
        .to_pylist()
    )
    assert len(actual) == 4
    assert sorted(
        [r for r in actual if r["_run_id"] == "history"], key=lambda r: r["id"]
    ) == sorted(untouched, key=lambda r: r["id"])
    current = [r for r in actual if r["_run_id"] == "producer" and r["_is_current"]]
    assert len(current) == int(matched)
    assert result.input_snapshots["gold:test.source"]["version"] == 0
    assert result.selected_snapshots["gold:test.source"]["version"] == 1
    assert storage.quarantine.write_many.await_count == 1


@pytest.mark.asyncio
async def test_reference_is_scoped_to_its_producer(storage):
    req = await request(storage, reference=[row("x", "", "unrelated")])
    result = await storage.reconcile_foreign_keys(req)
    assert result.orphan_rows_deleted == 1


@pytest.mark.asyncio
async def test_dry_run_does_not_change_version_or_quarantine(storage):
    req = await request(storage, dry_run=True)
    result = await storage.reconcile_foreign_keys(req)
    assert result.would_mutate and not result.mutated
    assert result.selected_snapshots == req.selected_snapshots
    storage.quarantine.write_many.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("table", ["test.source", "test.reference"])
async def test_drift_blocks_before_quarantine_or_mutation(storage, table):
    req = await request(storage)
    write(storage, table, [row("new", "new")])
    with pytest.raises(ValueError, match="snapshot drift"):
        await storage.reconcile_foreign_keys(req)
    storage.quarantine.write_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_reference_pin_is_an_error_even_with_empty_source(storage):
    req = await request(storage, source=[])
    pins = dict(req.selected_snapshots)
    pins.pop("gold:test.reference")
    with pytest.raises(ValueError, match="missing pinned producer"):
        await storage.reconcile_foreign_keys(replace(req, selected_snapshots=pins))


@pytest.mark.asyncio
async def test_chain_uses_previous_mutation_snapshot(storage):
    req = await request(storage)
    first = await storage.reconcile_foreign_keys(req)
    second = await storage.reconcile_foreign_keys(
        replace(req, selected_snapshots=first.selected_snapshots)
    )
    assert second.scanned_rows == 0 and not second.mutated
    assert second.input_snapshots["gold:test.source"]["version"] == 1
    with pytest.raises(ValueError, match="snapshot drift"):
        await storage.reconcile_foreign_keys(req)


@pytest.mark.asyncio
async def test_complete_reference_default_still_blocks_unproven(storage):
    req = await request(storage)
    result = await storage.reconcile_foreign_keys(
        replace(req, reconciliation_mode="complete-reference")
    )
    assert result.mutation_mode == "blocked"
    assert (
        DeltaTable(storage.gold_writer._resolve_table_path("test.source")).version()
        == 0
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("nulls_equal,deleted", [(False, 0), (True, 0)])
async def test_null_semantics_are_preserved(storage, nulls_equal, deleted):
    req = await request(storage, source=[row("a", None)], reference=[row(None, "")])
    result = await storage.reconcile_foreign_keys(replace(req, nulls_equal=nulls_equal))
    assert result.orphan_rows_deleted == deleted


@pytest.mark.asyncio
async def test_composite_key_comparison(storage):
    req = await request(
        storage, source=[row("a", "x"), row("b", "x")], reference=[row("a", "x")]
    )
    req = replace(
        req, source_key="id", source_keys=("id", "fk"), reference_keys=("id", "fk")
    )
    result = await storage.reconcile_foreign_keys(req)
    assert result.scanned_rows == 2 and result.orphan_rows_deleted == 1


@pytest.mark.asyncio
async def test_quarantine_failure_never_commits(storage):
    req = await request(storage)
    storage.quarantine.write_many.side_effect = RuntimeError("quarantine unavailable")
    with pytest.raises(RuntimeError, match="quarantine unavailable"):
        await storage.reconcile_foreign_keys(req)
    assert (
        DeltaTable(storage.gold_writer._resolve_table_path("test.source")).version()
        == 0
    )


@pytest.mark.asyncio
async def test_reference_drift_during_quarantine_never_commits(storage):
    req = await request(storage)

    async def drift(_rows):
        write(storage, "test.reference", [row("new", "")])

    storage.quarantine.write_many.side_effect = drift
    with pytest.raises(ValueError, match="snapshot drift"):
        await storage.reconcile_foreign_keys(req)
    assert (
        DeltaTable(storage.gold_writer._resolve_table_path("test.source")).version()
        == 0
    )


@pytest.mark.asyncio
async def test_missing_table_is_error_and_never_an_empty_reference(storage):
    req = await request(storage)
    missing = {
        **req.selected_snapshots,
        "gold:test.missing": req.selected_snapshots["gold:test.reference"],
    }
    from deltalake.exceptions import TableNotFoundError

    with pytest.raises(TableNotFoundError):
        await storage.reconcile_foreign_keys(
            replace(req, reference_table="test.missing", selected_snapshots=missing)
        )
    storage.quarantine.write_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_silver_deletion_preserves_other_producers(storage):
    writer = storage.silver_writer
    for name, rows in (
        ("test.source", [row("a", "absent"), row("b", "absent", "other")]),
        ("test.reference", []),
    ):
        write_deltalake(
            writer._resolve_table_path(name), pa.Table.from_pylist(rows, schema=SCHEMA)
        )
    pins = await storage.capture_pipeline_snapshots("test_source", "producer")
    pins.update(await storage.capture_pipeline_snapshots("test_reference", "producer"))
    req = ForeignKeyReconciliationRequest(
        source_table="test.source",
        reference_table="test.reference",
        source_key="fk",
        reference_key="id",
        primary_keys=("id",),
        source_scope="current_run",
        source_run_ids=("producer",),
        workflow_run_id=WORKFLOW_ID,
        reconciliation_mode="selected-snapshot",
        selected_snapshots=pins,
    )
    result = await storage.reconcile_foreign_keys(req)
    assert result.orphan_rows_deleted == 1 and result.mutation_mode == "silver_rewrite"
    assert DeltaTable(
        writer._resolve_table_path("test.source")
    ).to_pyarrow_table().to_pylist() == [row("b", "absent", "other")]


@pytest.mark.asyncio
async def test_unconfirmed_post_commit_returns_destructive_ambiguity(storage):
    req = await request(storage)
    original = storage.gold_writer._run_in_executor

    async def concurrent_commit(fn, *args):
        result = await original(fn, *args)
        write(storage, "test.source", [row("external", "x", "external")])
        return result

    storage.gold_writer._run_in_executor = concurrent_commit
    result = await storage.reconcile_foreign_keys(req)
    assert result.mutated
    assert result.mutation_blocked_reason == "selected_snapshot_commit_ambiguous"
    assert result.selected_snapshots is None
    assert result.input_snapshots == req.selected_snapshots


@pytest.mark.asyncio
@pytest.mark.parametrize("matched", [False, True])
async def test_analytical_tables_use_persisted_producer_entities_and_preserve_history(
    storage, matched
):
    schema = pa.schema(
        [(c.name, c.type) for c in SCHEMA if c.name != "_run_id"]
        + [("entity_id", pa.string()), ("content_hash", pa.string())]
    )

    def analytical(id, fk, current=True):
        return {
            "id": id,
            "fk": fk,
            "entity_id": id,
            "content_hash": f"hash-{id}",
            "_is_current": current,
            "_valid_to": "",
        }

    def persist(name, rows, mode="append"):
        write_deltalake(
            storage.gold_writer._resolve_table_path(name),
            pa.Table.from_pylist(rows, schema=schema),
            mode=mode,
        )

    untouched = [analytical("old", "absent"), analytical("historical", "absent", False)]
    persist("test.source", untouched)
    persist("test.reference", [])
    await storage.capture_pipeline_snapshots("test_source", "")
    await storage.capture_pipeline_snapshots("test_reference", "")
    persist("test.source", [analytical("a", "x"), analytical("b", "y")])
    if matched:
        persist("test.reference", [analytical("x", "")])
    pins = await storage.capture_pipeline_snapshots("test_source", "producer")
    pins.update(await storage.capture_pipeline_snapshots("test_reference", "producer"))
    assert set(pins["gold:test.source"]["owned_entities"]) == {"a", "b"}
    req = ForeignKeyReconciliationRequest(
        source_table="test.source",
        reference_table="test.reference",
        source_key="fk",
        reference_key="id",
        primary_keys=("id",),
        source_layer="gold",
        reference_layer="gold",
        source_scope="current_run",
        source_run_ids=("producer",),
        workflow_run_id=WORKFLOW_ID,
        reconciliation_mode="selected-snapshot",
        selected_snapshots=pins,
    )
    result = await storage.reconcile_foreign_keys(req)
    assert result.scanned_rows == 2 and result.orphan_rows_deleted == 2 - int(matched)
    rows = (
        DeltaTable(storage.gold_writer._resolve_table_path("test.source"))
        .to_pyarrow_table()
        .to_pylist()
    )
    assert [r for r in rows if r["id"] == "old"] == [untouched[0]]
    assert [r for r in rows if r["id"] == "historical"] == [untouched[1]]
    assert result.source_snapshot["physical_rows"] == 4
    assert result.source_snapshot["current_rows"] == 1 + int(matched)


@pytest.mark.asyncio
async def test_table_identity_drift_blocks_even_when_version_matches(storage):
    req = await request(storage)
    pins = {key: dict(value) for key, value in req.selected_snapshots.items()}
    pins["gold:test.source"]["table_id"] = "foreign-table"
    with pytest.raises(ValueError, match="snapshot drift"):
        await storage.reconcile_foreign_keys(replace(req, selected_snapshots=pins))
    storage.quarantine.write_many.assert_not_awaited()
