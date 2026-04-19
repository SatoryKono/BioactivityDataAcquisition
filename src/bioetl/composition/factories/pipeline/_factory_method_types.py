"""Private type/context helpers for pipeline factory method wrappers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline.creation_support import (
    _PipelineCreationRequest,
)
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import InputFilterConfig
from bioetl.domain.ports import (
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.composition.observability import ObservabilityBundle

if TYPE_CHECKING:
    import pyarrow as pa
    from bioetl.domain.config import RuntimeConfig
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
    config: PipelineYamlConfig | None = None
    filter_config: InputFilterConfig | None = None
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None


_CreatePipelineWithServicesRequest = _PipelineCreationRequest


@dataclass(frozen=True, slots=True)
class _ControlPlaneArtifacts:
    manifest_id: str | None = None
    config_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None


@dataclass(frozen=True, slots=True)
class _CreateFactoryRunnerRequest:
    pipeline_name: str
    silver_schema: pa.Schema | None
    gold_schema: GoldSchemaType
    run_id: RunID
    runtime: RuntimeConfig
    settings: Settings
    observability: ObservabilityBundle
    manifest_id: str | None = None
    config_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    filter_config: InputFilterConfig | None = None
    config: PipelineYamlConfig | None = None
    cached_bronze: CachedBronzeContext | None = None


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
    runtime: object,
    settings: Settings,
    logger: LoggerPort,
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
        run_id,
        runtime,
        settings,
        logger,
        artifacts.manifest_id,
        artifacts.config_hash,
        artifacts.dq_contract_compatibility_hash,
        artifacts.effective_config_artifact_id,
        config,
        filter_config,
        tracer,
        dq_monitor,
        metrics,
        cached_bronze,
    )


def create_factory_data_source(
    *,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    pipeline_name: str,
    filter_config: InputFilterConfig | None = None,
):
    """Create data-source adapter for one pipeline execution context."""
    return create_data_source_fn(
        settings, pipeline_config, logger, filter_config, pipeline_name=pipeline_name
    )
