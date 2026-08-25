# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Internal pipeline creation wiring extracted from service bundle facade."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from bioetl.application.core.wiring.factory import (
    BasePipeline,
    ShutdownSignal,
)
from bioetl.application.core.wiring.transformer import BaseTransformer
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline._creation_metadata import (
    _build_metadata_coordinator,
    _create_silver_validator,
)
from bioetl.composition.factories.pipeline.control_plane_artifacts import (
    ControlPlaneArtifacts,
)
from bioetl.composition.factories.pipeline.transformer_builder import (
    TransformerBuilder,
)
from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import InputFilterConfig
from bioetl.domain.ports import (
    AuditPort,
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.config.domain_config_resolver import (
    resolve_domain_pipeline_config,
)
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

from bioetl.composition.contracts.factories import (
    ServiceBundleDeps as _ServiceBundleDeps,
)
from bioetl.composition.contracts.factories import (
    BuildPipelineServicesFn as _BuildPipelineServicesFn,
)

from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)
from bioetl.application.core.pipeline_service_protocols import (
    PipelineServicesProtocol,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class _PipelineCreationRequest(ControlPlaneArtifacts):
    """Shared runtime request bundle for pipeline creation helpers."""

    run_id: RunID
    runtime: RuntimeConfig
    started_at: datetime
    settings: Settings
    logger: LoggerPort
    audit: AuditPort | None = None
    config: PipelineYamlConfig | None = None
    filter_config: InputFilterConfig | None = None
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None
    metrics: MetricsPort | None = None
    cached_bronze: CachedBronzeContext | None = None


@dataclass(frozen=True, slots=True)
class _PipelineCreationInputs:
    """Immutable input bundle for pipeline creation."""

    pipeline_name: str
    pipeline_class: type[BasePipeline]
    provider: str
    create_data_source_fn: DataSourceCreatorProtocol
    transformer_class: type[BaseTransformer] | None
    request: _PipelineCreationRequest
    pandera_silver_schema: object | None = None


def _resolve_yaml_config(
    *,
    inputs: _PipelineCreationInputs,
    deps: _ServiceBundleDeps,
) -> PipelineYamlConfig:
    """Resolve the effective pipeline YAML config for one creation request."""
    return inputs.request.config or deps.load_pipeline_config(inputs.pipeline_name)


def _build_pipeline_transformer(
    *,
    inputs: _PipelineCreationInputs,
    yaml_config: PipelineYamlConfig,
    domain_config: PipelineConfig,
    extract_entity_type: Callable[[str], str | None],
) -> BaseTransformer | None:
    """Build the runtime transformer while preserving the public factory seam."""

    request = inputs.request
    return TransformerBuilder(
        provider=inputs.provider,
        pipeline_name=inputs.pipeline_name,
        entity_type_extractor=extract_entity_type,
        contract_policy_loader=load_pipeline_contract_policy,
    ).build(
        transformer_class=inputs.transformer_class,
        yaml_config=yaml_config,
        domain_config=domain_config,
        pandera_silver_schema=inputs.pandera_silver_schema,
        tracer=request.tracer,
        metrics=request.metrics,
    )


def _create_pipeline_with_services_impl(
    inputs: _PipelineCreationInputs,
    *,
    deps: _ServiceBundleDeps,
    extract_entity_type: Callable[[str], str | None],
    build_pipeline_services_fn: _BuildPipelineServicesFn,
) -> BasePipeline:
    """Implement pipeline creation while keeping facade thin.

    Args:
        inputs: Immutable bundle of pipeline creation parameters.
        deps: Service bundle dependencies providing config loading and domain mapping.
        extract_entity_type: Callable deriving entity type from pipeline name.
        build_pipeline_services_fn: Callable assembling the PipelineService bundle.

    Returns:
        Configured BasePipeline instance ready for execution.
    """
    request = inputs.request
    yaml_config = _resolve_yaml_config(
        inputs=inputs,
        deps=deps,
    )
    metadata_coordinator = _build_metadata_coordinator(
        inputs=inputs,
        yaml_config=yaml_config,
        deps=deps,
        extract_entity_type=extract_entity_type,
    )
    domain_config = resolve_domain_pipeline_config(
        yaml_config,
        configs_root=resolve_configs_root(),
        relaxed_dq=request.settings.pipeline.relaxed_dq,
        domain_mapper=deps.yaml_config_to_domain,
    )

    services = build_pipeline_services_fn(
        pipeline_name=inputs.pipeline_name,
        create_data_source_fn=inputs.create_data_source_fn,
        settings=request.settings,
        logger=request.logger,
        audit=request.audit,
        config=yaml_config,
        filter_config=request.filter_config,
        tracer=request.tracer,
        dq_monitor=request.dq_monitor,
        metadata_coordinator=metadata_coordinator,
        cached_bronze=request.cached_bronze,
        silver_validator=_create_silver_validator(
            inputs.pandera_silver_schema,
            cast("DQConfig | None", domain_config.dq),
        ),
    )
    transformer = _build_pipeline_transformer(
        inputs=inputs,
        yaml_config=yaml_config,
        domain_config=domain_config,
        extract_entity_type=extract_entity_type,
    )

    return inputs.pipeline_class.create(
        run_id=request.run_id,
        runtime=request.runtime,
        services=cast(PipelineServicesProtocol, services),  # pyright: ignore[reportInvalidCast]
        config=domain_config,
        shutdown_signal=ShutdownSignal(),
        started_at=request.started_at,
        transformer=transformer,
    )
