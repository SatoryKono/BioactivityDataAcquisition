"""Source-ref and composite replay helpers for run-manifest diagnostics."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from datetime import datetime

from bioetl.domain.control_plane import (
    RunInputSnapshotRef,
    RunLedgerEntry,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
)

__all__ = [
    "_attach_rich_composite_replay_support",
    "_build_effective_source_refs",
]

_RICH_COMPOSITE_REPLAY_EVENTS = frozenset(
    {
        COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
        COMPOSITE_ENRICHER_COMPLETED_EVENT,
        COMPOSITE_MERGE_COMPLETED_EVENT,
    }
)


def _build_effective_source_refs(
    *,
    manifest: RunManifest,
    input_snapshots: Sequence[object],
) -> tuple[RunSourceRef, ...]:
    snapshots_by_source = _group_input_snapshots_by_source(
        manifest=manifest,
        input_snapshots=input_snapshots,
    )
    if not snapshots_by_source:
        return manifest.source_refs
    effective_refs = _merge_manifest_source_refs(
        manifest=manifest,
        snapshots_by_source=snapshots_by_source,
    )
    effective_refs.extend(_build_additional_source_refs(snapshots_by_source))
    return tuple(effective_refs)


def _group_input_snapshots_by_source(
    *,
    manifest: RunManifest,
    input_snapshots: Sequence[object],
) -> dict[tuple[str, str, str, str | None], list[RunInputSnapshotRef]]:
    """Group input snapshots by their effective source identity."""
    snapshots_by_source: dict[
        tuple[str, str, str, str | None],
        list[RunInputSnapshotRef],
    ] = {}
    for item in input_snapshots:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or manifest.provider)
        entity = str(item.get("entity") or manifest.entity)
        pipeline_name = str(item.get("pipeline_name") or manifest.pipeline_name)
        query_value = item.get("query")
        query = str(query_value) if query_value is not None else None
        snapshots_by_source.setdefault(
            _source_key(
                provider=provider,
                entity=entity,
                pipeline_name=pipeline_name,
                query=query,
            ),
            [],
        ).append(_build_snapshot_ref(item))
    return snapshots_by_source


def _merge_manifest_source_refs(
    *,
    manifest: RunManifest,
    snapshots_by_source: dict[
        tuple[str, str, str, str | None], list[RunInputSnapshotRef]
    ],
) -> list[RunSourceRef]:
    """Attach grouped snapshot refs to manifest-declared source refs."""
    effective_refs: list[RunSourceRef] = []
    for source_ref in manifest.source_refs:
        snapshots = _pop_matching_source_snapshots(
            snapshots_by_source=snapshots_by_source,
            provider=source_ref.provider,
            entity=source_ref.entity,
            pipeline_name=source_ref.pipeline_name,
            query=source_ref.query,
        )
        effective_refs.append(
            RunSourceRef(
                provider=source_ref.provider,
                entity=source_ref.entity,
                pipeline_name=source_ref.pipeline_name,
                query=source_ref.query,
                input_snapshots=tuple(snapshots),
            )
        )
    return effective_refs


def _pop_matching_source_snapshots(
    *,
    snapshots_by_source: dict[
        tuple[str, str, str, str | None], list[RunInputSnapshotRef]
    ],
    provider: str,
    entity: str,
    pipeline_name: str,
    query: str | None,
) -> list[RunInputSnapshotRef]:
    """Resolve ledger-derived snapshots back onto a manifest-declared source."""
    exact_key = _source_key(
        provider=provider,
        entity=entity,
        pipeline_name=pipeline_name,
        query=query,
    )
    if query is not None:
        return snapshots_by_source.pop(exact_key, [])

    matched_keys = [key for key in snapshots_by_source if key[:3] == exact_key[:3]]
    snapshots: list[RunInputSnapshotRef] = []
    for key in matched_keys:
        snapshots.extend(snapshots_by_source.pop(key, []))
    return snapshots


def _build_additional_source_refs(
    snapshots_by_source: dict[
        tuple[str, str, str, str | None], list[RunInputSnapshotRef]
    ],
) -> list[RunSourceRef]:
    """Build source refs discovered only from input snapshots."""
    return [
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=pipeline_name,
            query=query,
            input_snapshots=tuple(snapshots),
        )
        for (provider, entity, pipeline_name, query), snapshots in sorted(
            snapshots_by_source.items(),
            key=lambda item: (*item[0][:3], item[0][3] is not None, item[0][3] or ""),
        )
    ]


def _source_key(
    *,
    provider: str,
    entity: str,
    pipeline_name: str,
    query: str | None,
) -> tuple[str, str, str, str | None]:
    """Return one normalized source-identity key for grouping and lookup."""
    return (
        provider.strip(),
        entity.strip(),
        pipeline_name.strip(),
        query.strip() if query is not None else None,
    )


def _build_snapshot_ref(snapshot: dict[str, object]) -> RunInputSnapshotRef:
    return RunInputSnapshotRef(
        snapshot_id=str(snapshot.get("snapshot_id") or ""),
        content_hash=str(snapshot.get("content_hash") or ""),
        immutable_uri=_optional_text(snapshot.get("immutable_uri")),
        query_fingerprint=_optional_text(snapshot.get("query_fingerprint")),
        storage_provider=_optional_text(snapshot.get("storage_provider")),
        object_bucket=_optional_text(snapshot.get("object_bucket")),
        object_key=_optional_text(snapshot.get("object_key")),
        object_version_id=_optional_text(snapshot.get("object_version_id")),
        etag=_optional_text(snapshot.get("etag")),
        last_modified=_optional_text(snapshot.get("last_modified")),
        captured_at=_parse_optional_datetime(snapshot.get("captured_at")),
    )


def _parse_optional_datetime(value: object) -> datetime | None:
    """Parse an optional ISO datetime without failing diagnostics assembly."""
    if not isinstance(value, str) or not value.strip():
        return None
    with suppress(ValueError):
        return datetime.fromisoformat(value.strip())
    return None


def _optional_text(value: object) -> str | None:
    """Return optional textual snapshot metadata without unsafe coercion."""
    return value if isinstance(value, str) else None


def _attach_rich_composite_replay_support(
    summary: dict[str, object],
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Mark composite rich replay support only when ledger evidence is present."""
    observed_events = {
        entry.event_type
        for entry in ledger_entries
        if entry.event_type in _RICH_COMPOSITE_REPLAY_EVENTS
    }
    if not _RICH_COMPOSITE_REPLAY_EVENTS.issubset(observed_events):
        return summary
    updated = dict(summary)
    updated["composite_resume_rich_replay_supported"] = True
    return updated
