"""Use-case service for building pipeline run options and execution context."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, TypeVar

from bioetl.domain.context import (
    CachedBronzeContext,
    InputFilterContext,
    PipelineRunContext,
    VacuumSettings,
)
from bioetl.domain.types import RunID, RunType

__all__ = [
    "PipelineRunContextService",
]


if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_models import RunOptions


TOptions = TypeVar("TOptions")


class PipelineRunContextService:
    """Builds effective run options and PipelineRunContext for runner assembly."""

    def merge_options(
        self,
        *,
        options: TOptions | None,
        dry_run: bool,
        default_options_factory: Callable[[bool], TOptions],
    ) -> TOptions:
        """Merge explicit options with command-level flags.

        Args:
            options: Pre-built options object to use as-is, or None to use defaults.
            dry_run: CLI-level dry_run flag passed to the default options factory
                when options is None.
            default_options_factory: Callable that produces a default options instance
                from the dry_run flag.

        Returns:
            The provided options if not None, otherwise a default options instance.
        """
        if options is not None:
            return options
        return default_options_factory(dry_run)

    def build_context(
        self,
        *,
        pipeline_name: str,
        run_id: RunID,
        options: RunOptions,
        started_at: datetime,
    ) -> PipelineRunContext:
        """Build PipelineRunContext from run options.

        Args:
            pipeline_name: Identifier string for the pipeline being executed.
            run_id: Unique run identifier for this execution.
            options: RunOptions controlling run behaviour (type, filters, vacuum, etc.).

        Returns:
            PipelineRunContext assembled from the provided options and context fields.
        """
        input_filter = self._build_input_filter(options)
        vacuum = VacuumSettings(
            enabled=options.vacuum_after_run,
            retention_days=options.vacuum_retention_days or 7,
        )
        cached_bronze = self._build_cached_bronze(options)

        return PipelineRunContext(
            pipeline_name=pipeline_name,
            run_id=run_id,
            run_type=RunType(options.run_type),
            started_at=started_at,
            replay_of_run_id=options.replay_of_run_id,
            replay_of_manifest_id=options.replay_of_manifest_id,
            resume_run_id=options.resume_run_id,
            resume_manifest_id=options.resume_manifest_id,
            resume=options.resume,
            start_offset=options.start_offset,
            limit=options.limit,
            dry_run=options.dry_run,
            input_filter=input_filter,
            vacuum=vacuum,
            log_level=options.log_level,
            cached_bronze=cached_bronze,
            exact_replay=options.exact_replay,
            required_persistence_profile=options.required_persistence_profile,
            required_persistence_profile_opt_down=(
                str(options.required_persistence_profile or "").strip()
                == "degraded_observable"
            ),
            tracing_enabled_override=options.enable_tracing,
            debug_export_enabled=options.debug_export_enabled,
            debug_export_formats=tuple(options.debug_export_formats or ()),
            debug_export_dir=options.debug_export_dir,
            workflow_id=options.workflow_id or "standalone",
        )

    def _build_input_filter(self, options: RunOptions) -> InputFilterContext:
        """Resolve input filter mode from options."""
        if options.input_csv:
            return InputFilterContext.from_csv(
                source_path=options.input_csv,
                column_name=options.filter_column or "",
                filter_field=options.filter_field or "",
                fallback_column=options.fallback_column,
            )
        if options.filter_ids:
            return InputFilterContext.from_ids(
                filter_ids=options.filter_ids,
                filter_field=options.filter_field or "doi",
                fallback_mapping=options.fallback_mapping,
            )
        return InputFilterContext.disabled()

    def _build_cached_bronze(self, options: RunOptions) -> CachedBronzeContext:
        """Resolve cached Bronze context from options."""
        if (
            options.exact_replay
            and not options.use_cached_bronze
            and options.replay_of_run_id is None
            and options.replay_of_manifest_id is None
        ):
            raise ValueError(
                "exact replay currently requires --use-cached-bronze or "
                "replay_of_run_id/replay_of_manifest_id with published "
                "snapshot-backed Bronze inputs"
            )
        if options.use_cached_bronze:
            return CachedBronzeContext.from_options(
                path=options.cached_bronze_path,
                date=options.cached_bronze_date,
            )
        return CachedBronzeContext.disabled()
