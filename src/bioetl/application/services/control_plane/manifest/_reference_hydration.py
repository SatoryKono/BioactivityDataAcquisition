"""Hydration helpers for manifest source, snapshot, and artifact references."""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunInputSnapshotRef,
    RunSourceRef,
)


def _optional_string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return None if value is None else str(value)


def _required_values(
    item: object,
    *,
    context: str,
    keys: tuple[str, ...],
) -> tuple[dict[str, object], tuple[object, ...]]:
    if not isinstance(item, dict):
        raise ValueError(f"{context} must be a mapping, got {type(item).__name__}")
    try:
        return item, tuple(item[key] for key in keys)
    except KeyError as exc:
        raise ValueError(f"{context} missing required key: {exc.args[0]}") from exc


def hydrate_input_snapshots(
    payload: list[object],
    *,
    context: str = "input_snapshots",
) -> tuple[RunInputSnapshotRef, ...]:
    """Hydrate snapshot references, failing closed on malformed entries."""
    hydrated: list[RunInputSnapshotRef] = []
    for index, raw_item in enumerate(payload):
        item, (snapshot_id, content_hash) = _required_values(
            raw_item,
            context=f"{context}[{index}]",
            keys=("snapshot_id", "content_hash"),
        )
        captured_at = item.get("captured_at")
        hydrated.append(
            RunInputSnapshotRef(
                snapshot_id=str(snapshot_id),
                content_hash=str(content_hash),
                immutable_uri=_optional_string(item, "immutable_uri"),
                query_fingerprint=_optional_string(item, "query_fingerprint"),
                storage_provider=_optional_string(item, "storage_provider"),
                object_bucket=_optional_string(item, "object_bucket"),
                object_key=_optional_string(item, "object_key"),
                object_version_id=_optional_string(item, "object_version_id"),
                etag=_optional_string(item, "etag"),
                last_modified=_optional_string(item, "last_modified"),
                captured_at=(
                    None
                    if captured_at is None
                    else datetime.fromisoformat(str(captured_at))
                ),
            )
        )
    return tuple(hydrated)


def hydrate_source_refs(payload: list[object]) -> tuple[RunSourceRef, ...]:
    """Hydrate source references, failing closed on malformed entries."""
    hydrated: list[RunSourceRef] = []
    for index, raw_item in enumerate(payload):
        context = f"source_refs[{index}]"
        item, (provider, entity, pipeline_name) = _required_values(
            raw_item,
            context=context,
            keys=("provider", "entity", "pipeline_name"),
        )
        raw_snapshots = item.get("input_snapshots", [])
        if raw_snapshots is None:
            snapshot_items: list[object] = []
        elif isinstance(raw_snapshots, list):
            snapshot_items = list(raw_snapshots)
        else:
            raise ValueError(
                f"{context}.input_snapshots must be a list, "
                f"got {type(raw_snapshots).__name__}"
            )
        hydrated.append(
            RunSourceRef(
                provider=str(provider),
                entity=str(entity),
                pipeline_name=str(pipeline_name),
                query=_optional_string(item, "query"),
                input_snapshots=hydrate_input_snapshots(
                    snapshot_items,
                    context=f"{context}.input_snapshots",
                ),
            )
        )
    return tuple(hydrated)


def hydrate_planned_artifacts(payload: list[object]) -> tuple[RunArtifactRef, ...]:
    """Hydrate planned artifact references, failing closed on malformed entries."""
    hydrated: list[RunArtifactRef] = []
    for index, raw_item in enumerate(payload):
        _, (layer, path) = _required_values(
            raw_item,
            context=f"planned_artifacts[{index}]",
            keys=("layer", "path"),
        )
        hydrated.append(RunArtifactRef(layer=str(layer), path=str(path)))
    return tuple(hydrated)


__all__ = [
    "hydrate_input_snapshots",
    "hydrate_planned_artifacts",
    "hydrate_source_refs",
]
