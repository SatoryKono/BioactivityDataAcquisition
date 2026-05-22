"""Private type/context helpers for pipeline factory method wrappers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline.control_plane_artifacts import (
    ControlPlaneArtifacts,
)
from bioetl.composition.factories.pipeline.creation_support import (
    _PipelineCreationRequest,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import InputFilterConfig
from bioetl.domain.ports import (
    AuditPort,
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    PipelineCreateRunnerRequest,
    TracingPort,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.config._base import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.types import GoldSchemaType


@dataclass(frozen=True, slots=True)
class _PipelineFactoryContext:
    pipeline_name: str
    create_data_source_fn: DataSourceCreatorProtocol
    pipeline_class: type[BasePipeline] | None = None
    provider: str | None = None
    transformer_class: type[BaseTransformer] | None = None
    pandera_silver_schema: object | None = None


@dataclass(frozen=True, slots=True)
class _BuildFactoryServicesRequest:
    settings: Settings
    logger: LoggerPort
    audit: AuditPort | None = None
    config: PipelineYamlConfig | None = None
    filter_config: InputFilterConfig | None = None
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None


_CreatePipelineWithServicesRequest = _PipelineCreationRequest
_ControlPlaneArtifacts = ControlPlaneArtifacts


@dataclass(frozen=True, slots=True, kw_only=True)
class _CreateFactoryRunnerRequest(ControlPlaneArtifacts):
    pipeline_name: str
    silver_schema: pa.Schema | None
    gold_schema: GoldSchemaType
    run_id: RunID
    runtime: RuntimeConfig
    started_at: datetime
    settings: Settings
    observability: ObservabilityBundle
    filter_config: InputFilterConfig | None = None
    config: PipelineYamlConfig | None = None
    cached_bronze: CachedBronzeContext | None = None


def build_create_factory_runner_request(
    *,
    pipeline_name: str,
    silver_schema: object | None,
    gold_schema: object,
    request: PipelineCreateRunnerRequest,
) -> _CreateFactoryRunnerRequest:
    """Build the canonical runner-factory request bundle."""
    control_plane = request.control_plane
    return _CreateFactoryRunnerRequest(
        pipeline_name=pipeline_name,
        silver_schema=cast("pa.Schema | None", silver_schema),
        gold_schema=cast("GoldSchemaType", gold_schema),
        run_id=request.run_id,
        runtime=request.runtime,
        started_at=request.started_at,
        settings=cast("Settings", request.settings),
        observability=cast("ObservabilityBundle", request.observability),
        manifest_id=control_plane.manifest_id,
        execution_fingerprint=control_plane.execution_fingerprint,
        config_hash=control_plane.config_hash,
        resolved_config_hash=control_plane.resolved_config_hash,
        effective_config_hash=control_plane.effective_config_hash,
        dq_contract_compatibility_hash=control_plane.dq_contract_compatibility_hash,
        effective_config_artifact_id=control_plane.effective_config_artifact_id,
        replay_of_run_id=control_plane.replay_of_run_id,
        replay_of_manifest_id=control_plane.replay_of_manifest_id,
        input_snapshot_fingerprint=control_plane.input_snapshot_fingerprint,
        filter_config=request.filter_config,
        config=cast("PipelineYamlConfig | None", request.config),
        cached_bronze=request.cached_bronze,
    )


def build_pipeline_create_runner_request_from_kwargs(
    **kwargs: object,
) -> PipelineCreateRunnerRequest:
    """Compat shim for legacy factory imports expecting the kwargs builder here."""
    from bioetl.composition.pipeline_runner_request import (
        build_pipeline_create_runner_request_from_kwargs as _build_request,
    )

    return _build_request(**kwargs)


def extract_entity_type(pipeline_name: str) -> str | None:
    """Extract trailing entity token from `<provider>_<entity>` pipeline names."""
    return pipeline_name.split("_")[-1] if "_" in pipeline_name else None


def resolve_data_source_creator(
    *,
    provider: str,
    provider_registry: object | None,
    data_source_creator: DataSourceCreatorProtocol | None,
    get_data_source_creator_fn: Callable[..., DataSourceCreatorProtocol],
) -> DataSourceCreatorProtocol:
    """Resolve explicit or registry-derived data-source creator callback."""
    if data_source_creator is not None:
        return data_source_creator
    return get_data_source_creator_fn(provider, provider_registry=provider_registry)


def build_pipeline_factory_context(
    *,
    pipeline_name: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    pipeline_class: type[BasePipeline] | None = None,
    provider: str | None = None,
    transformer_class: type[BaseTransformer] | None = None,
    pandera_silver_schema: object | None = None,
) -> _PipelineFactoryContext:
    """Build immutable factory context consumed by helper orchestration flows."""
    return _PipelineFactoryContext(
        pipeline_name=pipeline_name,
        create_data_source_fn=create_data_source_fn,
        pipeline_class=pipeline_class,
        provider=provider,
        transformer_class=transformer_class,
        pandera_silver_schema=pandera_silver_schema,
    )


def build_create_pipeline_with_services_request(
    run_id: RunID,
    runtime: RuntimeConfig,
    started_at: datetime,
    settings: Settings,
    logger: LoggerPort,
    audit: AuditPort | None = None,
    control_plane_artifacts: _ControlPlaneArtifacts | None = None,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metrics: MetricsPort | None = None,
    cached_bronze: CachedBronzeContext | None = None,
) -> _CreatePipelineWithServicesRequest:
    """Pack runtime pipeline-creation arguments into a typed request object."""
    artifacts = control_plane_artifacts or _ControlPlaneArtifacts()
    return _CreatePipelineWithServicesRequest(
        run_id=run_id,
        runtime=runtime,
        started_at=started_at,
        settings=settings,
        logger=logger,
        audit=audit,
        manifest_id=artifacts.manifest_id,
        execution_fingerprint=artifacts.execution_fingerprint,
        config_hash=artifacts.config_hash,
        resolved_config_hash=artifacts.resolved_config_hash,
        effective_config_hash=artifacts.effective_config_hash,
        dq_contract_compatibility_hash=artifacts.dq_contract_compatibility_hash,
        effective_config_artifact_id=artifacts.effective_config_artifact_id,
        config=config,
        filter_config=filter_config,
        tracer=tracer,
        dq_monitor=dq_monitor,
        metrics=metrics,
        cached_bronze=cached_bronze,
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
    """Create data-source adapter for one pipeline execution context."""
    return create_data_source_fn(
        settings, pipeline_config, logger, filter_config, pipeline_name=pipeline_name
    )
