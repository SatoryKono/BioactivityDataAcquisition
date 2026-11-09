"""Helpers for resolving exact-replay cached Bronze context from control-plane evidence."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.composition.control_plane_paths import control_plane_root
from bioetl.composition.runtime_builders._cached_bronze_binding import (
    bind_cached_bronze_context as bind_cached_bronze_context,
)
from bioetl.composition.runtime_builders._exact_replay_snapshot_evidence import (
    _extract_bronze_date,
    _optional_text,
    _validated_ledger_snapshot_uri,
)
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_ledger import INPUT_SNAPSHOT_PUBLISHED_EVENT
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import FileRunLedgerStore, FileRunManifestStore

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings


def resolve_exact_replay_cached_bronze_context(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    cached_bronze: CachedBronzeContext,
) -> CachedBronzeContext:
    """Resolve cached Bronze replay context from parent run evidence when needed."""
    if not bool(getattr(ctx, "exact_replay", False)):
        return cached_bronze
    if bool(getattr(cached_bronze, "enabled", False)):
        return cached_bronze

    parent_manifest = _resolve_replay_parent_manifest(ctx=ctx, settings=settings)
    provider = str(parent_manifest.provider).strip()
    entity = str(parent_manifest.entity).strip()
    if parent_manifest.pipeline_name != ctx.pipeline_name:
        raise RuntimeError(
            "Exact replay parent pipeline mismatch: "
            f"requested '{ctx.pipeline_name}' but parent manifest belongs to "
            f"'{parent_manifest.pipeline_name}'"
        )
    bronze_date = _resolve_parent_bronze_date(
        manifest=parent_manifest,
        settings=settings,
    )
    bronze_root = Path(str(settings.bronze_path)) / provider / entity
    return CachedBronzeContext.from_options(
        path=str(bronze_root),
        date=bronze_date,
    )


def _resolve_replay_parent_manifest(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
) -> RunManifest:
    manifest_store = FileRunManifestStore(
        base_path=control_plane_root(settings, "run_manifest")
    )
    replay_of_manifest_id = _optional_text(getattr(ctx, "replay_of_manifest_id", None))
    if replay_of_manifest_id is not None:
        manifest = manifest_store.get(replay_of_manifest_id)
        if manifest is None:
            raise RuntimeError(
                "Exact replay parent manifest could not be loaded for "
                f"manifest_id '{replay_of_manifest_id}'"
            )
        return manifest

    replay_of_run_id = _optional_text(getattr(ctx, "replay_of_run_id", None))
    if replay_of_run_id is None:
        raise RuntimeError(
            "Exact replay without --use-cached-bronze requires replay_of_run_id "
            "or replay_of_manifest_id pointing to a persisted parent run"
        )
    try:
        run_id = RunID(UUID(replay_of_run_id))
    except ValueError as exc:
        raise RuntimeError(
            "Exact replay parent run_id must be a valid UUID when replay_of_manifest_id "
            "is not provided"
        ) from exc
    manifest = manifest_store.get_by_run_id(run_id)
    if manifest is None:
        raise RuntimeError(
            "Exact replay parent manifest could not be loaded for "
            f"run_id '{replay_of_run_id}'"
        )
    return manifest


def _resolve_parent_bronze_date(*, manifest: RunManifest, settings: Settings) -> str:
    ledger_store = FileRunLedgerStore(
        base_path=control_plane_root(settings, "run_ledger")
    )
    selected = ledger_store.list_entries_by_run_id(manifest.run_id)
    ledger_entries = tuple(selected or ledger_store.list_entries(manifest.manifest_id))
    bronze_dates = _collect_ledger_bronze_dates(
        manifest=manifest,
        ledger_entries=ledger_entries,
    )
    if not bronze_dates:
        raise RuntimeError(
            "Exact replay parent run is missing published Bronze input snapshot "
            "events and cannot be reconstructed into cached Bronze replay mode"
        )
    if len(bronze_dates) != 1:
        raise RuntimeError(
            "Exact replay parent run spans multiple Bronze snapshot dates; "
            "current replay runtime requires a single bounded Bronze snapshot date"
        )
    return bronze_dates[0]


def _collect_ledger_bronze_dates(
    *,
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> tuple[str, ...]:
    dates: set[str] = set()
    for entry in ledger_entries:
        if entry.event_type != INPUT_SNAPSHOT_PUBLISHED_EVENT:
            continue
        details_immutable_uri = _validated_ledger_snapshot_uri(
            manifest=manifest,
            entry=entry,
        )
        if details_immutable_uri is None:
            continue
        dates.add(_extract_bronze_date(details_immutable_uri))
    if dates:
        return tuple(sorted(dates))
    return _collect_manifest_bronze_dates(manifest)


def _collect_manifest_bronze_dates(manifest: RunManifest) -> tuple[str, ...]:
    """Collect the compatibility fallback dates from manifest source refs."""
    dates: set[str] = set()
    for source_ref in manifest.source_refs:
        if (
            source_ref.provider != manifest.provider
            or source_ref.entity != manifest.entity
        ):
            raise RuntimeError(
                "Exact replay parent source_refs contain mixed provider/entity values"
            )
        for snapshot in source_ref.input_snapshots:
            if snapshot.immutable_uri is None:
                raise RuntimeError(
                    "Exact replay parent input snapshot is missing immutable_uri"
                )
            dates.add(_extract_bronze_date(snapshot.immutable_uri))
    return tuple(sorted(dates))
