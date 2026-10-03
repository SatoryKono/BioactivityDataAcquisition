"""Bind producer rows when analytical contracts omit row-level run metadata."""

import asyncio
from collections.abc import Mapping

from deltalake import DeltaTable

from bioetl.domain.workflow.foreign_key_reconciliation_models import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_reads import (
    filter_current_rows,
)

RUN_COLUMNS = ("_run_id", "run_id", "workflow_run_id")


def entity_hashes(rows: list[dict[str, object]]) -> dict[str, str]:
    """Require stable technical identity and content identity for every row."""
    identities: dict[str, str] = {}
    for row in rows:
        identity, content = row.get("entity_id"), row.get("content_hash")
        if (
            not isinstance(identity, str)
            or not identity
            or not isinstance(content, str)
            or not content
        ):
            raise ValueError("selected producer snapshot lacks entity/content identity")
        if identity in identities and identities[identity] != content:
            raise ValueError(
                "selected producer snapshot has ambiguous current entities"
            )
        identities[identity] = content
    return identities


async def capture_ownership(
    path: str,
    layer: str,
    version: int,
    *,
    before: bool,
    previous: Mapping[str, object] | None,
    table_id: str,
) -> dict[str, object]:
    """Record exactly the new or changed current entities produced in this interval."""
    table = await asyncio.to_thread(
        lambda: DeltaTable(path, version=version).to_pyarrow_table()
    )
    if any(column in table.column_names for column in RUN_COLUMNS):
        return {}
    if not {"entity_id", "content_hash"}.issubset(table.column_names):
        raise ValueError(
            "selected snapshot has no row run identity or technical identity"
        )
    rows = filter_current_rows(table.to_pylist(), current_only=True, layer=layer)
    current = entity_hashes(rows)
    if before:
        return {"entity_hashes": current}
    if previous is None:
        raise ValueError(
            "selected producer ownership requires a pre-execution snapshot"
        )
    if "version" in previous and "entity_hashes" not in previous:
        raise ValueError("selected producer identity schema changed during execution")
    baseline = previous.get("entity_hashes", {})
    if previous.get("table_id") is not None and previous["table_id"] != table_id:
        baseline = {}
    if not isinstance(baseline, Mapping):
        raise ValueError("selected producer ownership baseline is invalid")
    return {
        "ownership": "producer_delta_entities",
        "owned_entities": {
            key: value for key, value in current.items() if baseline.get(key) != value
        },
        "producer_input_version": previous.get("version"),
        "producer_input_table_id": previous.get("table_id"),
    }


def filter_owned_entities(
    rows: list[dict[str, object]], entry: Mapping[str, object]
) -> list[dict[str, object]]:
    """Use persisted producer membership; never substitute the whole table."""
    owned = entry.get("owned_entities")
    if entry.get("ownership") != "producer_delta_entities" or not isinstance(
        owned, Mapping
    ):
        raise ValueError(
            "selected snapshot has no row run identity or producer membership"
        )
    if any(
        not isinstance(key, str) or not key or not isinstance(value, str) or not value
        for key, value in owned.items()
    ):
        raise ValueError("selected producer membership is invalid")
    return [
        row
        for row in rows
        if owned.get(str(row.get("entity_id"))) == row.get("content_hash")
        and row.get("content_hash") is not None
    ]


def selected_primary_keys(request: ForeignKeyReconciliationRequest) -> tuple[str, ...]:
    """Bind the mutation predicate to the selected technical row identity."""
    keys = request.primary_keys
    snapshots = request.selected_snapshots or {}
    identity = f"{request.source_layer}:{request.source_table}"
    if snapshots.get(identity, {}).get("ownership") == "producer_delta_entities":
        return tuple(dict.fromkeys((*keys, "entity_id", "content_hash")))
    return keys
