"""Extracted assemble_runtime_config for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from typing import Literal

from bioetl.composition.runtime_builders.inputs_runtime_models import (
    ResolvedVacuumSettings,
)

from bioetl.domain.config import RuntimeConfig

from bioetl.domain.types import RunType

from bioetl.domain.filtering.silver_filter_identity import (
    resolve_silver_filter_compatibility_mode,
)


def assemble_runtime_config(
    *,
    run_type: RunType,
    resume: bool,
    limit: int | None,
    query: str | None,
    dry_run: bool,
    heartbeat_interval: int,
    vacuum: ResolvedVacuumSettings,
    skip_gold: bool = False,
    debug_export_enabled: bool = False,
    debug_export_formats: tuple[str, ...] = (),
    debug_export_dir: str | None = None,
    workflow_id: str = "standalone",
    health_check_mode: Literal["strict", "probe"] = "strict",
) -> RuntimeConfig:
    """Build ``RuntimeConfig`` from already-resolved runtime inputs."""
    return RuntimeConfig(
        run_type=run_type,
        resume=resume,
        limit=limit,
        heartbeat_interval=heartbeat_interval,
        query=query,
        dry_run=dry_run,
        vacuum_after_run=vacuum.enabled,
        vacuum_retention_days=vacuum.retention_days,
        skip_gold=skip_gold,
        debug_export_enabled=debug_export_enabled,
        debug_export_formats=debug_export_formats,
        debug_export_dir=debug_export_dir,
        workflow_id=workflow_id,
        health_check_mode=health_check_mode,
        silver_filter_compatibility_mode=resolve_silver_filter_compatibility_mode(),
    )
