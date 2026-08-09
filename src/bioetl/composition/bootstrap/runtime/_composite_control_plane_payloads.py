"""Pure payload builders for composite control-plane bootstrap."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.runtime_builders.input_snapshot_resolution import (
    resolve_cached_bronze_input_snapshot_refs,
    resolve_manifest_input_snapshot_refs,
)
from bioetl.composition.runtime_builders.run_manifest_support import (
    to_serializable_mapping,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunInputSnapshotRef,
    RunSourceRef,
)
from bioetl.domain.types import RunType
from bioetl.domain.context import CachedBronzeContext

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "build_composite_launch_context_snapshot",
    "build_composite_planned_artifacts",
    "build_composite_resolved_config_snapshot",
    "build_composite_runtime_config_snapshot",
    "build_composite_source_refs",
]


def build_composite_launch_context_snapshot(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    *,
    required_persistence_profile: str,
    run_ledger_enabled: bool = True,
) -> dict[str, object]:
    """Capture launch-time options that materially affect composite execution."""
    return {
        "pipeline_name": config.name,
        "run_type": RunType.INCREMENTAL.value,
        "resume": runtime.resume,
        "dry_run": runtime.dry_run,
        "required_only": runtime.required_only,
        "force_enricher": runtime.force_enricher,
        "seed_limit": runtime.seed_limit,
        "enrich_only": list(runtime.enrich_only or ()),
        "use_cached_bronze": runtime.use_cached_bronze,
        "cached_bronze_path": runtime.cached_bronze_path,
        "cached_bronze_date": runtime.cached_bronze_date,
        "cached_bronze_enrichers": runtime.cached_bronze_enrichers,
        "cached_bronze_dependencies": runtime.cached_bronze_dependencies,
        "execution_context": "composite",
        "exact_replay": False,
        "strict_exact_replay_supported": False,
        "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
        "composite_replay_semantics": "rebuild_resume_only",
        "replay_mode": "resume" if runtime.resume else "rebuild",
        "replay_boundary_reason": (
            "composite_execution_outside_strict_exact_replay_boundary"
        ),
        "required_persistence_profile": required_persistence_profile,
        "run_ledger_enabled": run_ledger_enabled,
    }


def build_composite_source_refs(
    config: CompositeConfig,
    *,
    runtime: CompositeRuntimeConfig | None = None,
    settings: Settings | None = None,
) -> tuple[RunSourceRef, ...]:
    """Capture seed, dependency, and enricher sources in manifest payload."""
    pipeline_names = [config.seed.pipeline]
    pipeline_names.extend(dep.pipeline for dep in config.dependencies)
    pipeline_names.extend(enricher.pipeline for enricher in config.enrichers)
    return tuple(
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=pipeline_name,
            input_snapshots=_build_composite_input_snapshots(
                runtime=runtime,
                settings=settings,
                provider=provider,
                entity=entity,
                pipeline_name=pipeline_name,
            ),
        )
        for pipeline_name in pipeline_names
        for provider, entity in [_resolve_provider_entity(pipeline_name)]
    )


def build_composite_planned_artifacts(
    config: CompositeConfig,
) -> tuple[RunArtifactRef, ...]:
    """Capture planned composite artifacts for final materialization stages."""
    return (
        RunArtifactRef(layer="silver", path=config.merge.output_silver_path),
        RunArtifactRef(layer="gold", path=config.merge.output_gold_path),
    )


def build_composite_runtime_config_snapshot(
    runtime: CompositeRuntimeConfig,
) -> dict[str, object]:
    """Normalize composite runtime config into manifest-safe mapping."""
    return to_serializable_mapping(runtime)


def build_composite_resolved_config_snapshot(
    config: CompositeConfig,
) -> dict[str, object]:
    """Normalize resolved composite config into manifest-safe mapping."""
    return to_serializable_mapping(config)


def _resolve_provider_entity(pipeline_name: str) -> tuple[str, str]:
    """Resolve provider/entity from a canonical pipeline name."""
    if "_" not in pipeline_name:
        return pipeline_name, pipeline_name
    provider, entity = pipeline_name.split("_", 1)
    return provider, entity


def _build_composite_input_snapshots(
    *,
    runtime: CompositeRuntimeConfig | None,
    settings: Settings | None,
    provider: str,
    entity: str,
    pipeline_name: str,
) -> tuple[RunInputSnapshotRef, ...]:
    """Resolve immutable snapshot refs for one composite member pipeline."""
    if runtime is None:
        return ()
    replay_of_manifest_id = getattr(runtime, "replay_of_manifest_id", None)
    replay_of_run_id = getattr(runtime, "replay_of_run_id", None)
    if replay_of_manifest_id or replay_of_run_id:
        if settings is None:
            raise ValueError("Composite replay source refs require runtime Settings")
        return resolve_manifest_input_snapshot_refs(
            settings=settings,
            manifest_id=replay_of_manifest_id,
            run_id=replay_of_run_id,
        )
    if not runtime.use_cached_bronze:
        return ()
    if settings is None:
        raise ValueError("Composite cached Bronze source refs require runtime Settings")
    bronze_root = _resolve_composite_bronze_root(
        runtime=runtime,
        settings=settings,
        provider=provider,
        entity=entity,
        pipeline_name=pipeline_name,
    )
    return resolve_cached_bronze_input_snapshot_refs(
        cached_bronze=CachedBronzeContext(
            enabled=True,
            bronze_path=str(bronze_root),
            bronze_date=runtime.cached_bronze_date,
        ),
        settings=settings,
        provider=provider,
        entity=entity,
    )


def _resolve_composite_bronze_root(
    *,
    runtime: CompositeRuntimeConfig,
    settings: Settings | None,
    provider: str,
    entity: str,
    pipeline_name: str,
) -> Path:
    """Resolve the most likely cached-Bronze root for a composite member."""
    raw_root = runtime.cached_bronze_path
    base_root = (
        Path(raw_root)
        if raw_root is not None
        else Path(str(getattr(settings, "bronze_path", "data/bronze")))
    )
    provider_entity_root = base_root / provider / entity
    if provider_entity_root.exists():
        return provider_entity_root
    pipeline_root = base_root / pipeline_name
    if pipeline_root.exists():
        return pipeline_root
    return base_root
