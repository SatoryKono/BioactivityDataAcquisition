"""Pinned Delta reads and fail-closed drift guards for bounded FK comparison."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import replace
from typing import Protocol, cast

from deltalake import DeltaTable
from deltalake.exceptions import DeltaError, TableNotFoundError

from bioetl.domain.workflow.foreign_key_reconciliation_models import (
    ForeignKeyReconciliationRequest,
    ForeignKeyReconciliationResult,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_reads import (
    filter_current_rows,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    filter_source_rows_to_current_run,
)


class SelectedSnapshotHost(Protocol):
    """Only table resolvers are needed for snapshot reads and version checks."""

    @property
    def silver_writer(self) -> object: ...

    @property
    def gold_writer(self) -> object | None: ...


def _path(host: SelectedSnapshotHost, layer: str, name: str) -> str:
    writer = host.gold_writer if layer == "gold" else host.silver_writer
    resolver = getattr(writer, "_resolve_table_path", None)
    if not callable(resolver):
        raise ValueError(f"selected-snapshot requires a Delta {layer} writer")
    return str(cast(Callable[[str], str], resolver)(name))


def _version(path: str) -> int:
    return DeltaTable(path).version()


async def capture_pipeline_snapshots(
    host: SelectedSnapshotHost, pipeline_name: str, run_id: str
) -> dict[str, dict[str, object]]:
    """Pin producer tables immediately after successful pipeline completion."""
    provider, separator, entity = pipeline_name.partition("_")
    if not separator or not run_id:
        raise ValueError("selected-snapshot producer identity is missing")
    table_name = f"{provider}.{entity}"
    snapshots: dict[str, dict[str, object]] = {}
    for layer in ("silver", "gold"):
        path = _path(host, layer, table_name)
        try:
            version = await asyncio.to_thread(_version, path)
        except TableNotFoundError:
            continue
        snapshots[f"{layer}:{table_name}"] = {
            "version": version,
            "run_ids": [run_id],
            "producer_pipeline": pipeline_name,
            "ancestor_versions": [],
        }
    if not snapshots:
        raise ValueError(f"producer persisted no Delta snapshots: {pipeline_name}")
    return snapshots


def _entry(
    request: ForeignKeyReconciliationRequest, layer: str, name: str
) -> dict[str, object]:
    entry = (request.selected_snapshots or {}).get(f"{layer}:{name}")
    if not entry or type(entry.get("version")) is not int:
        raise ValueError(f"missing pinned producer snapshot: {layer}:{name}")
    run_ids = entry.get("run_ids")
    if (
        not isinstance(run_ids, list)
        or not run_ids
        or any(not isinstance(r, str) or not r for r in run_ids)
    ):
        raise ValueError(f"unbound pinned producer snapshot: {layer}:{name}")
    if not set(run_ids).issubset(request.source_run_ids):
        raise ValueError(
            "selected snapshot is outside current workflow producer identities"
        )
    return entry


async def validate_snapshot_versions(
    host: SelectedSnapshotHost, request: ForeignKeyReconciliationRequest
) -> None:
    """Reject source or reference changes instead of silently selecting latest."""
    if request.reconciliation_mode != "selected-snapshot":
        return
    for layer, name in (
        (request.source_layer, request.source_table),
        (request.reference_layer, request.reference_table),
    ):
        entry = _entry(request, layer, name)
        path = _path(host, layer, name)
        actual = await asyncio.to_thread(_version, path)
        if actual != entry["version"]:
            raise ValueError(f"selected snapshot drift: {layer}:{name}")


async def read_selected_rows(
    host: SelectedSnapshotHost,
    request: ForeignKeyReconciliationRequest,
    *,
    reference: bool,
) -> list[dict[str, object]]:
    """Read exactly one pinned version and restrict it to its producer rows."""
    layer = request.reference_layer if reference else request.source_layer
    name = request.reference_table if reference else request.source_table
    entry = _entry(request, layer, name)
    path = _path(host, layer, name)
    version = cast(int, entry["version"])
    table = await asyncio.to_thread(
        lambda: DeltaTable(path, version=version).to_pyarrow_table()
    )
    if not any(
        c in table.column_names for c in ("_run_id", "run_id", "workflow_run_id")
    ):
        raise ValueError(f"selected snapshot has no row run identity: {layer}:{name}")
    rows = filter_current_rows(table.to_pylist(), current_only=True, layer=layer)
    scoped, disposition = filter_source_rows_to_current_run(
        rows,
        source_scope="current_run",
        source_run_ids=tuple(cast(list[str], entry["run_ids"])),
    )
    if disposition == "blocked":
        raise ValueError(f"selected snapshot row scope unbound: {layer}:{name}")
    return scoped


async def selected_result(
    host: SelectedSnapshotHost,
    request: ForeignKeyReconciliationRequest,
    result: ForeignKeyReconciliationResult,
) -> ForeignKeyReconciliationResult:
    """Carry exact input versions and the committed descendant to the next step."""
    inputs = {
        key: dict(value) for key, value in (request.selected_snapshots or {}).items()
    }
    snapshots = {key: dict(value) for key, value in inputs.items()}
    key = f"{request.source_layer}:{request.source_table}"
    path = _path(host, request.source_layer, request.source_table)
    try:
        table = await asyncio.to_thread(lambda: DeltaTable(path))
        version = table.version()
        expected = cast(int, snapshots[key]["version"])
        if result.mutated:
            if version != expected + 1:
                raise ValueError(
                    "selected snapshot commit is ambiguous; repair required"
                )
            snapshots[key]["ancestor_versions"] = [
                *cast(list[int], snapshots[key].get("ancestor_versions", [])),
                expected,
            ]
            snapshots[key]["version"] = version
        elif version != expected:
            raise ValueError(
                "selected snapshot changed during non-mutating reconciliation"
            )
        descendant_request = replace(request, selected_snapshots=snapshots)
        await validate_snapshot_versions(host, descendant_request)
        rows = await asyncio.to_thread(lambda: table.to_pyarrow_table().to_pylist())
        current = filter_current_rows(
            rows, current_only=True, layer=request.source_layer
        )
        source_snapshot = {
            "version": version,
            "physical_rows": len(rows),
            "current_rows": len(current),
        }
    except (DeltaError, OSError, ValueError):
        if not result.mutated:
            raise
        # Return the committed mutation so the caller records ambiguity durably
        # before failing; never report a confirmed descendant for this outcome.
        return replace(
            result,
            input_snapshots=inputs,
            selected_snapshots=None,
            mutation_blocked_reason="selected_snapshot_commit_ambiguous",
        )
    return replace(
        result,
        selected_snapshots=snapshots,
        input_snapshots=inputs,
        source_snapshot=source_snapshot,
    )
