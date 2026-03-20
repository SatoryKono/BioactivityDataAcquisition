"""Generic pipeline assembly facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar

from bioetl.application.core.runner import PipelineRunner
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
    get_data_source_creator,
)
from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_configs as _extract_dq_configs,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    build_factory_services,
    create_factory_data_source,
    create_factory_runner,
    create_pipeline_instance_with_services,
    create_transformer_instance,
)
from bioetl.composition.factories.pipeline.runner_assembly import (
    assemble_runner_impl as _assemble_runner_impl,
)
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.base_transformer.types import (
        TransformerDependencyContext,
    )
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.composition.bootstrap_contexts import DQConfigsContext
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import (
        GoldFilterConfig,
        InputFilterConfig,
        SilverFilterConfig,
    )
    from bioetl.domain.ports import (
        ContractPolicyPort,
        DataNormalizationPort,
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.types import GoldSchemaType, RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")

__all__ = ["GenericPipelineFactory", "assemble_runner", "create_pipeline_factory"]


def _extract_entity_type(pipeline_name: str) -> str | None:
    """Extract entity_type suffix (e.g. 'chembl_activity' -> 'activity')."""
    return pipeline_name.split("_")[-1] if "_" in pipeline_name else None


def _default_dq_configs_extractor() -> Callable[
    [PipelineYamlConfig | None], DQConfigsContext
]:
    """Return the canonical DQ config extractor for runner assembly."""
    return _extract_dq_configs


class GenericPipelineFactory(Generic[TPipeline]):
    """Configurable factory for creating pipeline instances."""

    def __init__(
        self,
        pipeline_name: str,
        pipeline_class: type[TPipeline],
        provider: str,
        silver_schema: pa.Schema | None = None,
        gold_schema: GoldSchemaType | None = None,
        pandera_silver_schema: object | None = None,
        data_source_creator: DataSourceCreatorProtocol | None = None,
        transformer_class: type[BaseTransformer] | None = None,
        provider_registry: ProviderRegistry | None = None,
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
        self.provider_registry = provider_registry
        # Use custom creator or resolve the canonical provider-bound creator.
        self._create_data_source = data_source_creator or get_data_source_creator(
            provider,
            provider_registry=provider_registry,
        )

    def create_transformer(
        self,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
        contract_policy: ContractPolicyPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> BaseTransformer | None:
        """Create transformer when a transformer class is configured."""
        return create_transformer_instance(
            transformer_class=self.transformer_class,
            provider=self.provider,
            pipeline_name=self.pipeline_name,
            extract_entity_type=_extract_entity_type,
            tracer=tracer,
            metrics=metrics,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
            dependencies=dependencies,
        )

    def create_data_source(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        """Create provider data source via injected data-source creator."""
        return create_factory_data_source(
            create_data_source_fn=self._create_data_source,
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            pipeline_name=self.pipeline_name,
            filter_config=filter_config,
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
        """Build shared pipeline services for the configured pipeline."""
        return build_factory_services(
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
        """Create pipeline instance with wired services and optional transformer."""
        return create_pipeline_instance_with_services(
            pipeline_name=self.pipeline_name,
            pipeline_class=self.pipeline_class,
            provider=self.provider,
            create_data_source_fn=self._create_data_source,
            transformer_class=self.transformer_class,
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
            pandera_silver_schema=self.pandera_silver_schema,
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
        return create_factory_runner(
            pipeline_name=self.pipeline_name,
            silver_schema=self.silver_schema,
            gold_schema=self.gold_schema,
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            observability=observability,
            create_with_services_fn=self.create_with_services,
            assemble_runner_fn=assemble_runner,
            filter_config=filter_config,
            config=config,
            cached_bronze=cached_bronze,
        )


def create_pipeline_factory(
    pipeline_name: str,
    pipeline_class: type[TPipeline],
    provider: str,
    silver_schema: pa.Schema | None = None,
    gold_schema: GoldSchemaType | None = None,
    pandera_silver_schema: object | None = None,
    transformer_class: type[BaseTransformer] | None = None,
    provider_registry: ProviderRegistry | None = None,
) -> GenericPipelineFactory[TPipeline]:
    """Create a configured :class:`GenericPipelineFactory`."""
    return GenericPipelineFactory(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        pandera_silver_schema=pandera_silver_schema,
        transformer_class=transformer_class,
        provider_registry=provider_registry,
    )


def assemble_runner(
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
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
        dq_configs_extractor=_default_dq_configs_extractor(),
    )
