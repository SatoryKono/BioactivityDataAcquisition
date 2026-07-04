"""Helpers for resolving exact-replay cached Bronze context from control-plane evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import is_dataclass, replace
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.composition.runtime_builders._run_manifest_refs import control_plane_root
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane import RunManifest
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


def bind_cached_bronze_context(
    ctx: PipelineRunContext,
    cached_bronze: CachedBronzeContext,
) -> PipelineRunContext:
    """Return context with resolved cached Bronze replay inputs attached."""
    current = getattr(ctx, "cached_bronze", None)
    if current == cached_bronze:
        return ctx
    if is_dataclass(ctx):
        return replace(ctx, cached_bronze=cached_bronze)
    payload = dict(vars(ctx))
    payload["cached_bronze"] = cached_bronze
    return SimpleNamespace(**payload)


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


def _resolve_parent_bronze_date(
    *,
    manifest: RunManifest,
    settings: Settings,
) -> str:
    ledger_store = FileRunLedgerStore(
        base_path=control_plane_root(settings, "run_ledger")
    )
    ledger_entries = tuple(ledger_store.list_entries(manifest.manifest_id))
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
        details = entry.details if isinstance(entry.details, Mapping) else {}
        provider = _optional_text(details.get("provider"))
        entity = _optional_text(details.get("entity"))
        if provider is not None and provider != manifest.provider:
            raise RuntimeError(
                "Exact replay parent snapshot provider mismatch between ledger "
                f"('{provider}') and manifest ('{manifest.provider}')"
            )
        if entity is not None and entity != manifest.entity:
            raise RuntimeError(
                "Exact replay parent snapshot entity mismatch between ledger "
                f"('{entity}') and manifest ('{manifest.entity}')"
            )
        immutable_uri = _optional_text(details.get("immutable_uri"))
        if immutable_uri is None:
            continue
        dates.add(_extract_bronze_date(immutable_uri))
    if dates:
        return tuple(sorted(dates))
    for source_ref in manifest.source_refs:
        if (
            source_ref.provider != manifest.provider
            or source_ref.entity != manifest.entity
        ):
            raise RuntimeError(
                "Exact replay parent source_refs contain mixed provider/entity values"
            )
        for snapshot in source_ref.input_snapshots:
            dates.add(_extract_bronze_date(snapshot.immutable_uri))
    return tuple(sorted(dates))


def _extract_bronze_date(immutable_uri: str) -> str:
    prefix = "bronze://"
    if not immutable_uri.startswith(prefix):
        raise RuntimeError(
            "Exact replay parent snapshot immutable_uri must use bronze:// "
            f"for cached Bronze reconstruction, got '{immutable_uri}'"
        )
    relative = immutable_uri[len(prefix) :]
    normalized = PurePosixPath(relative)
    if not normalized.parts:
        raise RuntimeError(
            "Exact replay parent snapshot immutable_uri is missing Bronze date "
            f"segment: '{immutable_uri}'"
        )
    bronze_date = str(normalized.parts[0]).strip()
    if not bronze_date:
        raise RuntimeError(
            "Exact replay parent snapshot immutable_uri has an empty Bronze date "
            f"segment: '{immutable_uri}'"
        )
    return bronze_date


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
