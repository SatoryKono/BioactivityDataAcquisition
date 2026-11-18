"""Public helper for resolving an exact-replay parent run manifest."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.composition.control_plane_paths import control_plane_root
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.snapshot_field_resolution import coerce_optional_text
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import FileRunManifestStore

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings


def resolve_replay_parent_manifest(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
) -> RunManifest:
    """Load the persisted parent run manifest for an exact-replay request."""
    manifest_store = FileRunManifestStore(
        base_path=control_plane_root(settings, "run_manifest")
    )
    replay_of_manifest_id = coerce_optional_text(
        getattr(ctx, "replay_of_manifest_id", None)
    )
    if replay_of_manifest_id is not None:
        manifest = manifest_store.get(replay_of_manifest_id)
        if manifest is None:
            raise RuntimeError(
                "Exact replay parent manifest could not be loaded for "
                f"manifest_id '{replay_of_manifest_id}'"
            )
        return manifest

    replay_of_run_id = coerce_optional_text(getattr(ctx, "replay_of_run_id", None))
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
