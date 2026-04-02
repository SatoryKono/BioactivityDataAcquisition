"""Pure payload builders for composite control-plane bootstrap."""

from __future__ import annotations

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite.config import CompositeConfig
from bioetl.domain.control_plane import RunArtifactRef, RunSourceRef
from bioetl.domain.types import RunType

__all__ = [
    "build_composite_launch_context_snapshot",
    "build_composite_planned_artifacts",
    "build_composite_source_refs",
]


def build_composite_launch_context_snapshot(
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
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
    }


def build_composite_source_refs(
    config: CompositeConfig,
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


def _resolve_provider_entity(pipeline_name: str) -> tuple[str, str]:
    """Resolve provider/entity from a canonical pipeline name."""
    if "_" not in pipeline_name:
        return pipeline_name, pipeline_name
    provider, entity = pipeline_name.split("_", 1)
    return provider, entity
