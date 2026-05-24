"""Internal pipeline creation wiring extracted from service bundle facade."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast

import pyarrow as pa

from bioetl.application.core.wiring.factory import (
    BasePipeline,
    PipelineService,
)
from bioetl.application.core.wiring.factory import ShutdownSignal
from bioetl.application.core.wiring.transformer import BaseTransformer
from bioetl.application.services.lineage.metadata_coordinator import (
    MetadataCoordinator,
)
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline.construction_types import (
    EntityTypeExtractor,
)
from bioetl.composition.factories.pipeline.run_context_factory import (
    RunContextFactory,
)
from bioetl.composition.factories.pipeline.construction_types import _SchemaBuilder
from bioetl.composition.factories.pipeline.control_plane_artifacts import (
    ControlPlaneArtifacts,
)
from bioetl.composition.factories.pipeline.transformer_builder import (
    TransformerBuilder,
)
from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
from bioetl.domain.ports import (
    AuditPort,
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    SilverValidatorPort,
    TracingPort,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.config.domain_config_resolver import (
    resolve_domain_pipeline_config,
)
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class _ServiceBundleDeps(Protocol):
    """Subset of dependencies required by pipeline creation internals."""

    def load_pipeline_config(self, pipeline_name: str) -> PipelineYamlConfig:
        """Load a pipeline YAML configuration by name."""
        ...

    def yaml_config_to_domain(
        self,
        yaml_config: PipelineYamlConfig,
        resolved_dq_config: DQConfig | None = None,
    ) -> PipelineConfig:
        """Convert a YAML pipeline config to a domain PipelineConfig."""
        ...

    def compute_config_hash(
        self, config: PipelineYamlConfig | dict[str, object]
    ) -> str:
        """Compute a deterministic hash of the pipeline configuration."""
        ...


class _BuildPipelineServicesFn(Protocol):
    """Typed callback for constructing the service bundle."""

    def __call__(
        self,
        pipeline_name: str,
        create_data_source_fn: DataSourceCreatorProtocol,
        settings: Settings,
        logger: LoggerPort,
        audit: AuditPort | None,
        config: PipelineYamlConfig | None = None,
        filter_config: object | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        cached_bronze: object | None = None,
        silver_validator: SilverValidatorPort | None = None,
        _deps: object | None = None,
    ) -> PipelineService: ...


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
    filter_config: object | None = None
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None
    metrics: MetricsPort | None = None
    cached_bronze: object | None = None


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


def _build_metadata_coordinator(
    *,
    inputs: _PipelineCreationInputs,
    yaml_config: PipelineYamlConfig,
    deps: _ServiceBundleDeps,
    extract_entity_type: EntityTypeExtractor,
) -> MetadataCoordinator:
    """Build the metadata coordinator from the canonical run context factory."""
    from bioetl.composition.services.versioning import (
        get_git_commit,
        get_pipeline_version,
    )

    request = inputs.request
    run_context_factory = RunContextFactory(
        pipeline_name=inputs.pipeline_name,
        provider=inputs.provider,
        entity_type_extractor=extract_entity_type,
        pipeline_version_getter=get_pipeline_version,
        git_commit_getter=get_git_commit,
        config_hash_getter=deps.compute_config_hash,
    )
    return MetadataCoordinator(
        run_context_factory.create(
            run_id=request.run_id,
            runtime=request.runtime,
            started_at=request.started_at,
            yaml_config=yaml_config,
            manifest_id=request.manifest_id,
            execution_fingerprint=request.execution_fingerprint,
            config_hash=request.config_hash,
            resolved_config_hash=request.resolved_config_hash,
            effective_config_hash=request.effective_config_hash,
            dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
            effective_config_artifact_id=request.effective_config_artifact_id,
            exact_replay=bool(getattr(request.runtime, "exact_replay", False)),
            replay_of_run_id=request.replay_of_run_id,
            replay_of_manifest_id=request.replay_of_manifest_id,
            input_snapshot_fingerprint=request.input_snapshot_fingerprint,
        )
    )


def _build_pipeline_transformer(
    *,
    inputs: _PipelineCreationInputs,
    yaml_config: PipelineYamlConfig,
    domain_config: PipelineConfig,
    extract_entity_type: EntityTypeExtractor,
) -> BaseTransformer | None:
    """Build the runtime transformer while preserving the public factory seam."""
    from bioetl.infrastructure.config.contract_policy_loader import (
        load_pipeline_contract_policy,
    )

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
    extract_entity_type: EntityTypeExtractor,
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
        services=services,
        config=domain_config,
        shutdown_signal=ShutdownSignal(),
        started_at=request.started_at,
        transformer=transformer,
    )


def _create_silver_validator(
    pandera_silver_schema: object | None,
    dq_config: DQConfig | None = None,
) -> SilverValidatorPort | None:
    """Create contract-aware silver validator when schema is configured.

    Args:
        pandera_silver_schema: Optional Pandera DataFrameModel class with a
            to_schema() method; returns None when not provided.

    Returns:
        ContractAwareSilverValidator wrapping the schema, or None if schema is absent.
    """
    if pandera_silver_schema is None:
        return None

    from bioetl.infrastructure.validation import (
        ContractAwareSilverValidator,
    )

    schema_builder = cast(_SchemaBuilder, pandera_silver_schema)
    typed_schema = cast("pa.DataFrameSchema | None", schema_builder.to_schema())
    return ContractAwareSilverValidator(typed_schema, dq_config=dq_config)
