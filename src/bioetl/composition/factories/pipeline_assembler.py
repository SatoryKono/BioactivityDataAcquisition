"""Pipeline Assembler.

Contains GenericPipelineFactory and runner assembly entry points.
Extracted from pipeline_factory.py for composition layer LOC compliance.
"""

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
    """Configurable factory for creating pipelines via constructor parameters.

    Attributes:
        pipeline_name: Unique name for the pipeline
        pipeline_class: The pipeline class to instantiate
        silver_schema: PyArrow schema for Silver layer
        gold_schema: Pandera schema for Gold layer
        pandera_silver_schema: Pandera DataFrameModel class for Silver validation
    """

    def __init__(
        self,
        pipeline_name: str,
        pipeline_class: type[TPipeline],
        provider: str,
        silver_schema: pa.Schema | None = None,
        gold_schema: object | None = None,
        pandera_silver_schema: object | None = None,
        data_source_creator: DataSourceCreator | None = None,
        transformer_class: type[BaseTransformer] | None = None,
    ) -> None:
        """Initialize the factory.

        Args:
            pipeline_name: Unique name for the pipeline (e.g., "chembl_activity").
            pipeline_class: The pipeline class to instantiate.
            provider: Data provider name (e.g., "chembl", "pubmed").
            silver_schema: Optional PyArrow schema for Silver layer validation.
            gold_schema: Pandera DataFrameModel class for Gold layer validation.
            pandera_silver_schema: Optional Pandera DataFrameModel class for Silver
                validation. If provided, PanderaSilverValidator is created and
                injected into SilverWriter.
            data_source_creator: Optional custom data source creator function.
                If None, looked up from DataSourceRegistry by provider.
            transformer_class: Optional transformer class for Bronze-to-Silver
                and Silver-to-Gold transformations.

        Raises:
            ValueError: If gold_schema is not provided.
        """
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
        """Create transformer instance if transformer_class is configured.

        Args:
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            silver_filters: Optional domain-level filter configuration for Silver layer.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names.

        Returns:
            Configured transformer instance, or None if no transformer_class.
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
        """Create data source using the configured creator.

        Args:
            settings: Application settings with provider credentials and paths.
            pipeline_config: Pipeline YAML configuration with source settings.
            logger: Structured logger for observability.
            filter_config: Optional input filter configuration for restricting
                which records are fetched from the data source.

        Returns:
            Configured DataSourcePort implementation for the pipeline's provider.
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
        """Build PipelineService from settings.

        Args:
            settings: Application settings with data paths and credentials.
            logger: Structured logger for observability.
            config: Pre-loaded pipeline YAML config. If None, loaded from disk.
            filter_config: Optional input filter configuration for the data source.
            tracer: Optional TracingPort for distributed tracing.
            dq_monitor: Optional data quality monitor for anomaly detection.

        Returns:
            Configured PipelineService instance.
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
        """Create pipeline instance with services and optional transformer.

        Args:
            run_id: Unique identifier for this pipeline run.
            runtime: Pipeline runtime configuration (run_type, resume, limits).
            settings: Application settings with data paths and credentials.
            logger: Structured logger for observability.
            config: Pre-loaded pipeline YAML config. If None, loaded from disk.
            filter_config: Optional input filter configuration for the data source.
            tracer: Optional TracingPort for distributed tracing.
            dq_monitor: Optional data quality monitor for anomaly detection.
            metrics: Optional MetricsPort for transformer observability.
            cached_bronze: Optional CachedBronzeContext for reading from Bronze
                cache instead of making API calls.

        Returns:
            Fully configured pipeline instance of type TPipeline.
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
        """Create and assemble a fully configured PipelineRunner instance."""
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
    gold_schema: object | None = None,
    pandera_silver_schema: object | None = None,
    transformer_class: type[BaseTransformer] | None = None,
) -> GenericPipelineFactory[TPipeline]:
    """Convenience function for creating pipeline factories.

    Args:
        pipeline_name: Pipeline identifier.
        pipeline_class: Pipeline class.
        provider: Data provider name.
        silver_schema: Silver schema.
        gold_schema: Gold schema.
        pandera_silver_schema: Pandera silver schema.
        transformer_class: Transformer class.

    Returns:
        Newly created GenericPipelineFactory[TPipeline] instance.
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
    gold_schema: object,
    strict_gold_validation: bool,
    yaml_config: PipelineYamlConfig | None = None,
) -> PipelineRunner:
    """Assemble a PipelineRunner from a pipeline instance."""
    return _assemble_runner_impl(
        pipeline=pipeline,
        observability=observability,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        yaml_config=yaml_config,
        dq_configs_extractor=_extract_dq_configs,
    )
