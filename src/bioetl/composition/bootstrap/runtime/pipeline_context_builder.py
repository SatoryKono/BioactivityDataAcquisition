"""Shared PipelineRunContext construction helpers for composition runtime seams."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import cast
from uuid import UUID

from bioetl.application.runtime_timestamps import capture_runtime_timing_anchor
from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.composition.occurrence_identity import create_runtime_occurrence_run_id
from bioetl.domain.context import (
    CachedBronzeContext,
    InputFilterContext,
    PipelineRunContext,
    VacuumSettings,
)
from bioetl.domain.ports import ClockPort
from bioetl.domain.types import ExecutionContext, RunID, RunType

__all__ = ["build_pipeline_context"]


def _build_input_filter_context(options: RunOptions) -> InputFilterContext:
    """Build input filter context from user-facing run options."""
    if options.multi_filter_ids:
        return InputFilterContext.from_multi_ids(
            multi_filter_ids=options.multi_filter_ids,
        )
    if options.filter_ids:
        return InputFilterContext.from_ids(
            filter_ids=options.filter_ids,
            filter_field=options.filter_field or "doi",
            fallback_mapping=options.fallback_mapping,
        )
    if options.input_csv:
        return InputFilterContext(
            enabled=True,
            source_path=options.input_csv,
            column_name=options.filter_column or "",
            filter_field=options.filter_field or "",
        )
    return InputFilterContext.disabled()


def _build_vacuum_config(options: RunOptions) -> VacuumSettings:
    """Build vacuum config from CLI overrides while preserving tri-state input."""
    return VacuumSettings(
        enabled=options.vacuum_after_run,
        retention_days=options.vacuum_retention_days or 7,
    )


def _build_cached_bronze_context(options: RunOptions) -> CachedBronzeContext:
    """Build cached Bronze context from user-facing run options."""
    if options.use_cached_bronze:
        return CachedBronzeContext.from_options(
            path=options.cached_bronze_path,
            date=options.cached_bronze_date,
        )
    if (
        options.exact_replay
        and options.replay_of_run_id is None
        and options.replay_of_manifest_id is None
    ):
        raise ValueError(
            "exact replay currently requires --use-cached-bronze or "
            "replay_of_run_id/replay_of_manifest_id with published "
            "snapshot-backed Bronze inputs"
        )
    return CachedBronzeContext.disabled()


def _coerce_run_id(run_id: RunID | UUID | str) -> RunID:
    if isinstance(run_id, UUID):
        return cast(RunID, run_id)
    return cast(RunID, UUID(str(run_id)))


def _resolve_pipeline_run_id(
    *,
    options: RunOptions,
    run_id: RunID | UUID | str | None,
    run_id_factory: Callable[[], RunID | UUID | str] | None,
) -> RunID:
    if run_id is not None:
        return _coerce_run_id(run_id)
    if run_id_factory is not None:
        return _coerce_run_id(run_id_factory())
    if options.exact_replay:
        raise ValueError("exact replay requires explicit run_id or run_id_factory")
    return create_runtime_occurrence_run_id("pipeline_context")


def build_pipeline_context(
    name: str,
    options: RunOptions,
    *,
    run_id: RunID | UUID | str | None = None,
    run_id_factory: Callable[[], RunID | UUID | str] | None = None,
    clock: ClockPort | None = None,
    started_at: datetime | None = None,
) -> PipelineRunContext:
    """Build a PipelineRunContext from user-facing options."""
    started_at, _ = capture_runtime_timing_anchor(
        clock=clock,
        started_at=started_at,
    )
    cached_bronze = _build_cached_bronze_context(options)
    return PipelineRunContext.create(
        pipeline_name=name,
        run_id=_resolve_pipeline_run_id(
            options=options,
            run_id=run_id,
            run_id_factory=run_id_factory,
        ),
        run_type=RunType(options.run_type),
        started_at=started_at,
        replay_of_run_id=options.replay_of_run_id,
        replay_of_manifest_id=options.replay_of_manifest_id,
        resume_run_id=options.resume_run_id,
        resume_manifest_id=options.resume_manifest_id,
        resume=options.resume,
        limit=options.limit,
        dry_run=options.dry_run,
        input_filter=_build_input_filter_context(options),
        vacuum=_build_vacuum_config(options),
        log_level=options.log_level,
        ignore_yaml_filter=options.ignore_yaml_filter,
        skip_gold=options.skip_gold,
        cached_bronze=cached_bronze,
        exact_replay=options.exact_replay,
        required_persistence_profile=options.required_persistence_profile,
        debug_export_enabled=options.debug_export_enabled,
        debug_export_formats=tuple(options.debug_export_formats or ()),
        debug_export_dir=options.debug_export_dir,
        workflow_id=options.workflow_id or "standalone",
        execution_context=ExecutionContext(options.execution_context),
    )
