"""Internal helpers for GenericPipelineFactory orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar, cast

from bioetl.composition.factories.pipeline.creation_support import (
    _PipelineCreationRequest,
)
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


@dataclass(frozen=True, slots=True)
class _PipelineFactoryContext:
    """Stable internal factory context shared across assembler helper calls."""

    pipeline_name: str
    create_data_source_fn: DataSourceCreatorProtocol
    pipeline_class: type[BasePipeline] | None = None
    provider: str | None = None
    transformer_class: type[BaseTransformer] | None = None
    pandera_silver_schema: object | None = None


@dataclass(frozen=True, slots=True)
class _BuildFactoryServicesRequest:
    """Runtime request inputs for pipeline service assembly."""

    settings: Settings
    logger: LoggerPort
    config: PipelineYamlConfig | None = None
    filter_config: InputFilterConfig | None = None
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None


_CreatePipelineWithServicesRequest = _PipelineCreationRequest


def extract_entity_type(pipeline_name: str) -> str | None:
    """Extract trailing entity from `<provider>_<entity>` pipeline names."""
    return pipeline_name.split("_")[-1] if "_" in pipeline_name else None


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
    factory_context: _PipelineFactoryContext,
    request: _BuildFactoryServicesRequest,
) -> PipelineService:
    """Build shared pipeline services for the configured pipeline."""
    return build_pipeline_services(
        pipeline_name=factory_context.pipeline_name,
        create_data_source_fn=factory_context.create_data_source_fn,
        settings=request.settings,
        logger=request.logger,
        config=request.config,
        filter_config=request.filter_config,
        tracer=request.tracer,
        dq_monitor=request.dq_monitor,
    )


def create_pipeline_instance_with_services(
    *,
    factory_context: _PipelineFactoryContext,
    request: _CreatePipelineWithServicesRequest,
) -> BasePipeline:
    """Create pipeline instance with wired services and optional transformer."""
    if factory_context.pipeline_class is None or factory_context.provider is None:
        raise AssertionError(
            "factory_context must include pipeline_class and provider for pipeline creation"
        )
    create_pipeline_kwargs: dict[str, object] = {
        "pipeline_name": factory_context.pipeline_name,
        "pipeline_class": factory_context.pipeline_class,
        "provider": factory_context.provider,
        "create_data_source_fn": factory_context.create_data_source_fn,
        "transformer_class": factory_context.transformer_class,
        "pandera_silver_schema": factory_context.pandera_silver_schema,
        "run_id": request.run_id,
        "runtime": request.runtime,
        "settings": request.settings,
        "logger": request.logger,
        "config": request.config,
        "filter_config": cast("InputFilterConfig | None", request.filter_config),
        "tracer": request.tracer,
        "dq_monitor": request.dq_monitor,
        "metrics": request.metrics,
        "cached_bronze": cast("CachedBronzeContext | None", request.cached_bronze),
    }
    if request.manifest_id is not None:
        create_pipeline_kwargs["manifest_id"] = request.manifest_id
    if request.config_hash is not None:
        create_pipeline_kwargs["config_hash"] = request.config_hash
    if request.dq_contract_compatibility_hash is not None:
        create_pipeline_kwargs["dq_contract_compatibility_hash"] = (
            request.dq_contract_compatibility_hash
        )
    if request.effective_config_artifact_id is not None:
        create_pipeline_kwargs["effective_config_artifact_id"] = (
            request.effective_config_artifact_id
        )
    return create_pipeline_with_services(
        **cast(
            "dict[str, object]", create_pipeline_kwargs
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
    manifest_id: str | None = None,
    config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    create_with_services_fn: Callable[..., TPipeline],
    assemble_runner_fn: Callable[..., PipelineRunner],
    filter_config: InputFilterConfig | None = None,
    config: PipelineYamlConfig | None = None,
    cached_bronze: CachedBronzeContext | None = None,
) -> PipelineRunner:
    """Create and assemble a fully configured PipelineRunner instance."""
    yaml_config = config or load_pipeline_config(pipeline_name)
    create_with_services_kwargs: dict[str, object] = {
        "run_id": run_id,
        "runtime": runtime,
        "settings": settings,
        "logger": observability.logger,
        "config": yaml_config,
        "filter_config": filter_config,
        "tracer": observability.tracer,
        "dq_monitor": observability.dq_monitor,
        "metrics": observability.metrics,
        "cached_bronze": cached_bronze,
    }
    if manifest_id is not None:
        create_with_services_kwargs["manifest_id"] = manifest_id
    if config_hash is not None:
        create_with_services_kwargs["config_hash"] = config_hash
    if dq_contract_compatibility_hash is not None:
        create_with_services_kwargs["dq_contract_compatibility_hash"] = (
            dq_contract_compatibility_hash
        )
    if effective_config_artifact_id is not None:
        create_with_services_kwargs["effective_config_artifact_id"] = (
            effective_config_artifact_id
        )
    pipeline = create_with_services_fn(
        **cast(
            "dict[str, object]", create_with_services_kwargs
        ),
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
