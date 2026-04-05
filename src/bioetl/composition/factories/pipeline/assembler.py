"""Assemble pipelines and runners from composition-layer factory inputs."""

from __future__ import annotations

from typing import Generic, TypeVar, cast

import pyarrow as pa

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.base_transformer.types import TransformerDependencyContext
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.core.runner import PipelineRunner
from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
    get_data_source_creator,
)
from bioetl.composition.factories.dq.context_resolver import extract_dq_configs
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    _BuildFactoryServicesRequest,
    _PipelineFactoryContext,
    build_create_pipeline_with_services_request,
    build_factory_services,
    build_pipeline_factory_context,
    create_factory_data_source,
    create_factory_runner,
    create_pipeline_instance_with_services,
    create_transformer_instance,
    extract_entity_type,
    resolve_data_source_creator,
)
from bioetl.composition.factories.pipeline.runner_assembly import assemble_runner_impl
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers.provider_registry import ProviderRegistry
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
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldSchemaType, RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")

def _factory_context(
    factory: GenericPipelineFactory[TPipeline],
) -> _PipelineFactoryContext:
    return build_pipeline_factory_context(
        pipeline_name=factory.pipeline_name,
        create_data_source_fn=factory._create_data_source,
        pipeline_class=cast(type[BasePipeline] | None, factory.pipeline_class),
        provider=factory.provider,
        transformer_class=factory.transformer_class,
        pandera_silver_schema=factory.pandera_silver_schema,
    )

def _extract_entity_type(pipeline_name: str) -> str | None:
    """Compatibility wrapper for legacy unit tests expecting assembler-local helper."""
    return extract_entity_type(pipeline_name)

def _extract_dq_configs(yaml_config: PipelineYamlConfig | None) -> DQConfigsContext:
    """Compatibility wrapper for legacy unit tests expecting assembler-local helper."""
    return extract_dq_configs(yaml_config)

_assemble_runner_impl = assemble_runner_impl

class GenericPipelineFactory(Generic[TPipeline]):
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
        if gold_schema is None:
            raise ValueError(
                f"gold_schema is required for pipeline '{pipeline_name}' to enforce Gold validation."
            )
        self.pipeline_name, self.pipeline_class, self.provider = pipeline_name, pipeline_class, provider
        self.silver_schema, self.gold_schema, self.pandera_silver_schema = silver_schema, gold_schema, pandera_silver_schema
        self.transformer_class, self.provider_registry = transformer_class, provider_registry
        self._create_data_source = resolve_data_source_creator(
            provider=provider,
            provider_registry=provider_registry,
            data_source_creator=data_source_creator,
            get_data_source_creator_fn=get_data_source_creator,
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
        return create_transformer_instance(
            transformer_class=self.transformer_class,
            provider=self.provider,
            pipeline_name=self.pipeline_name,
            extract_entity_type=extract_entity_type,
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
        return build_factory_services(
            factory_context=_factory_context(self),
            request=_BuildFactoryServicesRequest(
                settings,
                logger,
                config,
                filter_config,
                tracer,
                dq_monitor,
            ),
        )
    def create_with_services(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        manifest_id: str | None = None,
        config_hash: str | None = None,
        dq_contract_compatibility_hash: str | None = None,
        effective_config_artifact_id: str | None = None,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metrics: MetricsPort | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> TPipeline:
        return cast(
            TPipeline,
            create_pipeline_instance_with_services(
                factory_context=_factory_context(self),
                request=build_create_pipeline_with_services_request(
                    run_id,
                    runtime,
                    settings,
                    logger,
                    manifest_id,
                    config_hash,
                    dq_contract_compatibility_hash,
                    effective_config_artifact_id,
                    config,
                    filter_config,
                    tracer,
                    dq_monitor,
                    metrics,
                    cached_bronze,
                ),
            ),
        )
    def create_runner(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        observability: ObservabilityBundle,
        manifest_id: str | None = None,
        config_hash: str | None = None,
        dq_contract_compatibility_hash: str | None = None,
        effective_config_artifact_id: str | None = None,
        filter_config: InputFilterConfig | None = None,
        config: PipelineYamlConfig | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> PipelineRunner:
        return create_factory_runner(
            pipeline_name=self.pipeline_name,
            silver_schema=self.silver_schema,
            gold_schema=self.gold_schema,
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            observability=observability,
            manifest_id=manifest_id,
            config_hash=config_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
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
    return GenericPipelineFactory(pipeline_name, pipeline_class, provider, silver_schema, gold_schema, pandera_silver_schema, None, transformer_class, provider_registry)

def assemble_runner(
    pipeline: BasePipeline,
    observability: ObservabilityBundle,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    strict_gold_validation: bool,
    yaml_config: PipelineYamlConfig | None = None,
) -> PipelineRunner:
    return _assemble_runner_impl(
        pipeline=pipeline,
        observability=observability,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=strict_gold_validation,
        yaml_config=yaml_config,
        dq_configs_extractor=_extract_dq_configs,
    )

__all__ = ["GenericPipelineFactory", "assemble_runner", "create_pipeline_factory"]
