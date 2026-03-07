"""Generic pipeline assembly facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, cast

from bioetl.application.core.runner import PipelineRunner
from bioetl.composition.factories.data_source_factory import (
    DataSourceCreator,
    DataSourceRegistry,
)
from bioetl.composition.factories.pipeline_factory_dq_helpers import (
    extract_dq_configs as _extract_dq_configs,
)
from bioetl.composition.factories.pipeline_factory_runner_assembly import (
    assemble_runner_impl as _assemble_runner_impl,
)
from bioetl.composition.factories.service_bundle_factory import (
    build_pipeline_services,
    create_pipeline_with_services,
)
from bioetl.domain.services import IdentityService
from bioetl.infrastructure.config import load_pipeline_config

if TYPE_CHECKING:
    import pandera
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import (
        GoldFilterConfig,
        InputFilterConfig,
        SilverFilterConfig,
    )
    from bioetl.domain.ports import (
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")

__all__ = [
    "GenericPipelineFactory",
    "assemble_runner",
    "create_pipeline_factory",
]


def _extract_entity_type(pipeline_name: str) -> str | None:
    """Extract entity_type from pipeline_name.

    Example: "chembl_activity" -> "activity"

    Args:
        pipeline_name: Full pipeline name with provider prefix.

    Returns:
        Entity type suffix, or None if no underscore in name.
    """
    return pipeline_name.split("_")[-1] if "_" in pipeline_name else None


class GenericPipelineFactory(Generic[TPipeline]):
    """Configurable factory for creating pipeline instances."""

    def __init__(
        self,
        pipeline_name: str,
        pipeline_class: type[TPipeline],
        provider: str,
        silver_schema: pa.Schema | None = None,
        gold_schema: type[pandera.DataFrameModel] | None = None,
        pandera_silver_schema: object | None = None,
        data_source_creator: DataSourceCreator | None = None,
        transformer_class: type[BaseTransformer] | None = None,
    ) -> None:
        """Initialize factory dependencies and schema contracts."""
        if gold_schema is None:
            raise ValueError(
                f"gold_schema is required for pipeline '{pipeline_name}'. "
                "All Gold layer writes must have schema validation."
            )
        self.pipeline_name = pipeline_name
        self.pipeline_class = pipeline_class
        self.provider = provider
        self.silver_schema = silver_schema
        self.gold_schema = gold_schema
        self.pandera_silver_schema = pandera_silver_schema
        self.transformer_class = transformer_class

        # Use custom creator or look up from registry
        self._create_data_source = data_source_creator or DataSourceRegistry.get(
            provider
        )

    def create_transformer(
        self,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
    ) -> BaseTransformer | None:
        """Create transformer when a transformer class is configured.

        Args:
            tracer: Optional TracingPort for span propagation inside the transformer.
            metrics: Optional MetricsPort for transformer-level metrics.
            silver_filters: Optional Silver layer filter rules applied during transform.
            gold_filters: Optional Gold layer filter rules applied during transform.
            identity_service: Optional service for entity identity resolution.
            pii_hasher: Optional hasher for PII fields in transformed records.

        Returns:
            Configured BaseTransformer instance, or None if no transformer class set.
        """
        if self.transformer_class is None:
            return None

        return self.transformer_class(
            provider=self.provider,
            entity_type=_extract_entity_type(self.pipeline_name),
            tracer=tracer,
            metrics=metrics,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
        )

    def create_data_source(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create provider data source via injected data-source creator.

        Args:
            settings: Application settings for HTTP client and API key configuration.
            pipeline_config: Pipeline YAML configuration with source parameters.
            logger: LoggerPort for structured logging inside the adapter.
            filter_config: Optional input filter configuration; no filtering if None.

        Returns:
            DataSourcePort for the configured provider.
        """
        return self._create_data_source(
            settings,
            pipeline_config,
            logger,
            filter_config,
            pipeline_name=self.pipeline_name,
        )

    def build_services(
        self,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
    ) -> PipelineService:
        """Build shared pipeline services for the configured pipeline.

        Args:
            settings: Application settings for infrastructure wiring.
            logger: LoggerPort for structured logging.
            config: Optional pre-loaded pipeline YAML config; loaded from disk if None.
            filter_config: Optional input filter configuration; disables filtering if None.
            tracer: Optional TracingPort for distributed tracing.
            dq_monitor: Optional DQMonitorPort for data quality monitoring.

        Returns:
            Fully wired PipelineService bundle for the configured pipeline.
        """
        return build_pipeline_services(
            pipeline_name=self.pipeline_name,
            create_data_source_fn=self._create_data_source,
            settings=settings,
            logger=logger,
            config=config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
        )

    def create_with_services(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metrics: MetricsPort | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> TPipeline:
        """Create pipeline instance with wired services and optional transformer.

        Args:
            run_id: Unique identifier for this pipeline run.
            runtime: Runtime configuration (run type, limits, vacuum settings).
            settings: Application settings for infrastructure wiring.
            logger: LoggerPort for structured logging.
            config: Optional pre-loaded pipeline YAML config; loaded from disk if None.
            filter_config: Optional input filter configuration; disables filtering if None.
            tracer: Optional TracingPort for distributed tracing.
            dq_monitor: Optional DQMonitorPort for data quality monitoring.
            metrics: Optional MetricsPort for metrics collection.
            cached_bronze: Optional cached Bronze context; uses live API if None or disabled.

        Returns:
            Configured pipeline instance of type TPipeline ready for execution.
        """
        return cast(
            TPipeline,
            create_pipeline_with_services(
                pipeline_name=self.pipeline_name,
                pipeline_class=self.pipeline_class,
                provider=self.provider,
                create_data_source_fn=self._create_data_source,
                transformer_class=self.transformer_class,
                pandera_silver_schema=self.pandera_silver_schema,
                run_id=run_id,
                runtime=runtime,
                settings=settings,
                logger=logger,
                config=config,
                filter_config=filter_config,
                tracer=tracer,
                dq_monitor=dq_monitor,
                metrics=metrics,
                cached_bronze=cached_bronze,
            ),
        )

    def create_runner(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        observability: ObservabilityBundle,
        filter_config: InputFilterConfig | None = None,
        config: PipelineYamlConfig | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> PipelineRunner:
        """Create and assemble a fully configured PipelineRunner instance.

        Args:
            run_id: Unique identifier for this pipeline run.
            runtime: Runtime configuration (run type, limits, vacuum settings).
            settings: Application settings for infrastructure wiring.
            observability: Bundle containing logger, tracer, metrics, and DQ monitor.
            filter_config: Optional input filter configuration; disables filtering if None.
            config: Optional pre-loaded pipeline YAML config; loaded from disk if None.
            cached_bronze: Optional cached Bronze context; uses live API if None or disabled.

        Returns:
            Fully wired PipelineRunner ready for execution.
        """
        # Load config once if not provided
        yaml_config = config or load_pipeline_config(self.pipeline_name)

        # Create pipeline instance with services
        pipeline = self.create_with_services(
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            logger=observability.logger,
            config=yaml_config,
            filter_config=filter_config,
            tracer=observability.tracer,
            dq_monitor=observability.dq_monitor,
            metrics=observability.metrics,
            cached_bronze=cached_bronze,
        )

        # Delegate runner assembly to dedicated function
        return assemble_runner(
            pipeline=pipeline,
            observability=observability,
            silver_schema=self.silver_schema,
            gold_schema=self.gold_schema,
            strict_gold_validation=(
                runtime.strict_gold_validation
                if settings.env != "prod" or settings.test_mode
                else True
            ),
            yaml_config=yaml_config,
        )


def create_pipeline_factory(
    pipeline_name: str,
    pipeline_class: type[TPipeline],
    provider: str,
    silver_schema: pa.Schema | None = None,
    gold_schema: type[pandera.DataFrameModel] | None = None,
    pandera_silver_schema: object | None = None,
    transformer_class: type[BaseTransformer] | None = None,
) -> GenericPipelineFactory[TPipeline]:
    """Create a configured :class:`GenericPipelineFactory`.

    Returns:
        GenericPipelineFactory instance wired with the provided schemas and classes.
    """
    return GenericPipelineFactory(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        pandera_silver_schema=pandera_silver_schema,
        transformer_class=transformer_class,
    )


def assemble_runner(
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    silver_schema: pa.Schema | None,
    gold_schema: type[pandera.DataFrameModel],
    strict_gold_validation: bool,
    yaml_config: PipelineYamlConfig | None = None,
) -> PipelineRunner:
    """Assemble a PipelineRunner from a pipeline instance.

    Returns:
        Fully wired PipelineRunner ready for execution.
    """
    return _assemble_runner_impl(
        pipeline=pipeline,
        observability=observability,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        yaml_config=yaml_config,
        dq_configs_extractor=_extract_dq_configs,
    )
