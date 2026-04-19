"""Internal helpers for GenericPipelineFactory orchestration."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import pyarrow as pa

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.base_transformer.types import (
    TransformerDependencyContext,
)
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.core.runner import PipelineRunner
from bioetl.composition.factories.pipeline._factory_method_control_plane import (
    apply_optional_control_plane_kwargs as _apply_optional_control_plane_kwargs,
)
from bioetl.composition.factories.pipeline._factory_method_runtime_support import (
    create_factory_runner_from_request,
    create_pipeline_instance_from_request,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    _BuildFactoryServicesRequest,
    _ControlPlaneArtifacts,
    _CreatePipelineWithServicesRequest,
    _PipelineFactoryContext,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    build_create_pipeline_with_services_request as _build_create_pipeline_with_services_request,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    build_pipeline_factory_context as _build_pipeline_factory_context,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    create_factory_data_source as _create_factory_data_source,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    extract_entity_type as _extract_entity_type_helper,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    resolve_data_source_creator as _resolve_data_source_creator,
)
from bioetl.composition.factories.pipeline.transformer_dependencies import (
    build_transformer_dependencies,
)
from bioetl.composition.factories.services.bundle import (
    build_pipeline_services,
    create_pipeline_with_services,
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
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldSchemaType, RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")
build_create_pipeline_with_services_request = (
    _build_create_pipeline_with_services_request
)
build_pipeline_factory_context = _build_pipeline_factory_context
create_factory_data_source = _create_factory_data_source
extract_entity_type = _extract_entity_type_helper
resolve_data_source_creator = _resolve_data_source_creator


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
    """Create transformer instance with resolved dependency context."""
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


def build_factory_services(
    *,
    factory_context: _PipelineFactoryContext,
    request: _BuildFactoryServicesRequest,
) -> PipelineService:
    """Build shared pipeline services from context and runtime request values."""
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
    return create_pipeline_instance_from_request(
        factory_context=factory_context,
        request=request,
        create_pipeline_with_services_fn=create_pipeline_with_services,
        apply_optional_control_plane_kwargs_fn=_apply_optional_control_plane_kwargs,
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
    yaml_config = config or load_pipeline_config(pipeline_name)
    return create_factory_runner_from_request(
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        run_id=run_id,
        runtime=runtime,
        settings=settings,
        observability=observability,
        yaml_config=yaml_config,
        control_plane_artifacts=_ControlPlaneArtifacts(
            manifest_id=manifest_id,
            config_hash=config_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
        ),
        create_with_services_fn=create_with_services_fn,
        assemble_runner_fn=assemble_runner_fn,
        filter_config=filter_config,
        cached_bronze=cached_bronze,
    )
