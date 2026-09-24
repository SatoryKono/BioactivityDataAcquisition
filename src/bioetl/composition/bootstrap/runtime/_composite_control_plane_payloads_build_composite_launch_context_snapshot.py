"""Extracted build_composite_launch_context_snapshot for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig

from bioetl.domain.composite import CompositeConfig

from bioetl.domain.types import RunType

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
