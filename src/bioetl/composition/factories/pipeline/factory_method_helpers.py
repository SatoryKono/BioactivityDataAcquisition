"""Internal helpers for GenericPipelineFactory orchestration."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar, cast

from bioetl.composition.factories.pipeline.transformer_dependencies import (
    build_transformer_dependencies,
)
from bioetl.composition.factories.services.bundle import (
    build_pipeline_services,
    create_pipeline_with_services,
)
from bioetl.domain.services import IdentityService
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.base_transformer.types import (
        TransformerDependencyContext,
    )
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
    )
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


def create_transformer_instance(
    *,
    transformer_class: type[BaseTransformer] | None,
    provider: str,
    pipeline_name: str,
    extract_entity_type: Callable[[str], str | None],
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
    if transformer_class is None:
        return None

    resolved_entity_type = extract_entity_type(pipeline_name)
    resolved_dependencies = (
        dependencies
        if dependencies is not None
        else build_transformer_dependencies(
            provider=provider,
            entity_type=resolved_entity_type,
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
        )
    )
    return transformer_class(
        provider=provider,
        entity_type=resolved_entity_type,
        silver_filters=silver_filters,
        gold_filters=gold_filters,
        dependencies=resolved_dependencies,
    )


def create_factory_data_source(
    *,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    pipeline_name: str,
    filter_config: InputFilterConfig | None = None,
) -> DataSourcePort:
    """Create provider data source via injected creator."""
    return create_data_source_fn(
        settings,
        pipeline_config,
        logger,
        filter_config,
        pipeline_name=pipeline_name,
    )


def build_factory_services(
    *,
    pipeline_name: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    logger: LoggerPort,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
) -> PipelineService:
    """Build shared pipeline services for the configured pipeline."""
    return build_pipeline_services(
        pipeline_name=pipeline_name,
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        logger=logger,
        config=config,
        filter_config=filter_config,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )


def create_pipeline_instance_with_services(
    *,
    pipeline_name: str,
    pipeline_class: type[TPipeline],
    provider: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    transformer_class: type[BaseTransformer] | None,
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
    pandera_silver_schema: object | None = None,
) -> TPipeline:
    """Create pipeline instance with wired services and optional transformer."""
    return cast(
        TPipeline,
        create_pipeline_with_services(
            pipeline_name=pipeline_name,
            pipeline_class=pipeline_class,
            provider=provider,
            create_data_source_fn=create_data_source_fn,
            transformer_class=transformer_class,
            pandera_silver_schema=pandera_silver_schema,
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


def create_factory_runner(
    *,
    pipeline_name: str,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    observability: ObservabilityBundle,
    create_with_services_fn: Callable[..., TPipeline],
    assemble_runner_fn: Callable[..., PipelineRunner],
    filter_config: InputFilterConfig | None = None,
    config: PipelineYamlConfig | None = None,
    cached_bronze: CachedBronzeContext | None = None,
) -> PipelineRunner:
    """Create and assemble a fully configured PipelineRunner instance."""
    yaml_config = config or load_pipeline_config(pipeline_name)
    pipeline = create_with_services_fn(
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
    return assemble_runner_fn(
        pipeline=pipeline,
        observability=observability,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        strict_gold_validation=(
            runtime.strict_gold_validation
            if settings.env != "prod" or settings.test_mode
            else True
        ),
        yaml_config=yaml_config,
    )
