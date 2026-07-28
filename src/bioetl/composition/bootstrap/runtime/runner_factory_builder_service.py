"""Builder helpers for composite runner factories."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypedDict, TypeVar

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import PipelineRunner
    from bioetl.domain.composite import DependencyConfig, EnricherConfig
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import LoggerPort

from bioetl.composition.bootstrap.runtime._dependency_runner_support import (
    build_dependency_debug_context,
    resolve_dependency_runner_limit,
)
from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
    CompositeFilterExtractor,
)

class BronzeRunOptions(TypedDict):
    """Cached bronze options passed to RunOptions constructor."""

    use_cached_bronze: bool
    cached_bronze_path: str | None
    cached_bronze_date: str | None

_RunOptionsT = TypeVar("_RunOptionsT")

def resolve_bronze_opts(
    runtime: CompositeRuntimeConfig,
    phase_override: bool | None,
) -> BronzeRunOptions:
    """Resolve per-phase cached bronze options using tri-state override.

    Returns:
        BronzeRunOptions with resolved cached bronze settings for the phase.
    """
    effective = (
        phase_override if phase_override is not None else runtime.use_cached_bronze
    )
    return BronzeRunOptions(
        use_cached_bronze=effective,
        cached_bronze_path=runtime.cached_bronze_path if effective else None,
        cached_bronze_date=runtime.cached_bronze_date if effective else None,
    )

class RunnerFactoryBuilder[RunOptionsT]:
    """Build seed/enricher/dependency runner factories."""

    def __init__(
        self,
        *,
        logger: LoggerPort,
        run_options_cls: Callable[..., _RunOptionsT],
        build_context: Callable[[str, _RunOptionsT], PipelineRunContext],
        pipeline_runner_builder: Callable[[PipelineRunContext], PipelineRunner],
        filter_extraction_service: CompositeFilterExtractor,
    ) -> None:
        self._logger = logger
        self._run_options_cls = run_options_cls
        self._build_context = build_context
        self._pipeline_runner_builder = pipeline_runner_builder
        self._filter_extraction_service = filter_extraction_service

    def _create_runner(
        self,
        *,
        pipeline_name: str,
        **option_kwargs: object,
    ) -> PipelineRunner:
        """Build a runner from one resolved RunOptions payload."""
        options = self._run_options_cls(**option_kwargs)
        ctx = self._build_context(pipeline_name, options)
        return self._pipeline_runner_builder(ctx)

    def build_seed_factory(
        self,
        *,
        seed_pipeline: str,
        seed_limit: int | None,
        bronze_opts: BronzeRunOptions,
    ) -> Callable[[], PipelineRunner]:
        """Build seed phase runner factory.

        Returns:
            Callable that creates a configured PipelineRunner for the seed phase.
        """

        def seed_runner_factory() -> PipelineRunner:
            """Create a PipelineRunner configured for the seed phase."""
            return self._create_runner(
                pipeline_name=seed_pipeline,
                run_type="incremental",
                limit=seed_limit,
                skip_gold=True,
                **bronze_opts,
            )

        return seed_runner_factory

    def build_enricher_factory(
        self,
        *,
        enrichers: list[EnricherConfig],
        bronze_opts: BronzeRunOptions,
    ) -> Callable[[str, pl.DataFrame], PipelineRunner]:
        """Build enricher phase runner factory.

        Returns:
            Callable that creates a configured PipelineRunner for a named enricher.
        """
        enricher_configs = {enricher.pipeline: enricher for enricher in enrichers}

        def enricher_runner_factory(
            pipeline_name: str,
            keys: pl.DataFrame,
        ) -> PipelineRunner:
            """Create a PipelineRunner configured for the given enricher."""
            enricher_cfg = enricher_configs.get(pipeline_name)
            filter_ids: tuple[str, ...] | None = None
            filter_field: str | None = None
            fallback_mapping: dict[str, str] | None = None

            if enricher_cfg is not None:
                filter_ids, filter_field, fallback_mapping = (
                    self._filter_extraction_service.extract_enricher_filters(
                        enricher_cfg=enricher_cfg,
                        keys=keys,
                    )
                )

            self._logger.debug(
                "Creating enricher runner",
                pipeline=pipeline_name,
                keys_columns=list(keys.columns) if keys is not None else [],
                keys_count=len(keys) if keys is not None else 0,
                join_keys=list(enricher_cfg.join_keys) if enricher_cfg else [],
                filter_field=filter_field,
                filter_ids_count=len(filter_ids) if filter_ids else 0,
                filter_ids_sample=list(filter_ids)[:5] if filter_ids else [],
            )

            limit: int | None = None
            if enricher_cfg and not enricher_cfg.is_many_to_one and keys is not None:
                limit = len(keys)

            return self._create_runner(
                pipeline_name=pipeline_name,
                run_type="incremental",
                limit=limit,
                ignore_yaml_filter=True,
                skip_gold=True,
                filter_ids=filter_ids,
                filter_field=filter_field,
                fallback_mapping=fallback_mapping,
                execution_context="enricher",
                **bronze_opts,
            )

        return enricher_runner_factory

    def build_dependency_factory(
        self,
        *,
        dependencies: list[DependencyConfig],
        bronze_opts: BronzeRunOptions,
    ) -> Callable[[str, pl.DataFrame], PipelineRunner]:
        """Build dependency phase runner factory.

        Returns:
            Callable that creates a configured PipelineRunner for a named dependency.
        """
        dependency_configs = {
            dependency.pipeline: dependency for dependency in dependencies
        }

        def dependency_runner_factory(
            pipeline_name: str,
            keys: pl.DataFrame,
        ) -> PipelineRunner:
            """Create a PipelineRunner configured for the given dependency."""
            dep_cfg = dependency_configs.get(pipeline_name)
            filter_ids, filter_field, multi_filter_ids = (
                self._filter_extraction_service.resolve_dependency_filter_inputs(
                    dep_cfg=dep_cfg,
                    keys=keys,
                )
            )
            debug_context = build_dependency_debug_context(
                pipeline_name=pipeline_name,
                keys=keys,
                dep_cfg=dep_cfg,
                filter_field=filter_field,
                filter_ids=filter_ids,
                multi_filter_ids=multi_filter_ids,
            )
            limit = resolve_dependency_runner_limit(
                keys=keys,
                filter_ids=filter_ids,
                multi_filter_ids=multi_filter_ids,
            )

            self._logger.debug("Creating dependency runner", **debug_context)

            return self._create_runner(
                pipeline_name=pipeline_name,
                run_type="incremental",
                limit=limit,
                filter_ids=filter_ids,
                filter_field=filter_field,
                multi_filter_ids=multi_filter_ids,
                ignore_yaml_filter=True,
                skip_gold=True,
                execution_context="dependency",
                **bronze_opts,
            )

        return dependency_runner_factory

__all__ = ["BronzeRunOptions", "RunnerFactoryBuilder", "resolve_bronze_opts"]
