"""Internal pipeline creation wiring extracted from service bundle facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.core.wiring.factory import ShutdownSignal
from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.factories.pipeline.construction_types import (
    _SchemaBuilder,
)
from bioetl.composition.factories.pipeline.run_context_factory import (
    RunContextFactory,
)
from bioetl.composition.factories.pipeline.transformer_builder import (
    TransformerBuilder,
)
from bioetl.composition.services.versioning import get_git_commit, get_pipeline_version
from bioetl.infrastructure.config import load_pipeline_contract_policy
from bioetl.infrastructure.config.domain_config_resolver import (
    resolve_domain_pipeline_config,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.wiring.factory import (
        BasePipeline,
        PipelineService,
    )
    from bioetl.application.core.wiring.transformer import BaseTransformer
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
    )
    from bioetl.composition.factories.pipeline.construction_types import (
        EntityTypeExtractor,
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
    from bioetl.infrastructure.config import Settings
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
        audit: AuditPort,
        config: PipelineYamlConfig | None = None,
        filter_config: object | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        cached_bronze: object | None = None,
        silver_validator: SilverValidatorPort | None = None,
        _deps: object | None = None,
    ) -> PipelineService: ...


@dataclass(frozen=True, slots=True)
class _PipelineCreationRequest:
    """Shared runtime request bundle for pipeline creation helpers."""

    run_id: RunID
    runtime: RuntimeConfig
    settings: Settings
    logger: LoggerPort
    audit: AuditPort
    manifest_id: str | None = None
    execution_fingerprint: str | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
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
    yaml_config = request.config or deps.load_pipeline_config(inputs.pipeline_name)
    run_context_factory = RunContextFactory(
        pipeline_name=inputs.pipeline_name,
        provider=inputs.provider,
        entity_type_extractor=extract_entity_type,
        pipeline_version_getter=get_pipeline_version,
        git_commit_getter=get_git_commit,
        config_hash_getter=deps.compute_config_hash,
    )
    metadata_coordinator = MetadataCoordinator(
        run_context_factory.create(
            run_id=request.run_id,
            runtime=request.runtime,
            yaml_config=yaml_config,
            manifest_id=request.manifest_id,
            execution_fingerprint=request.execution_fingerprint,
            config_hash=request.config_hash,
            resolved_config_hash=request.resolved_config_hash,
            effective_config_hash=request.effective_config_hash,
            dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
            effective_config_artifact_id=request.effective_config_artifact_id,
        )
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
        silver_validator=_create_silver_validator(inputs.pandera_silver_schema),
    )
    domain_config = resolve_domain_pipeline_config(
        yaml_config,
        relaxed_dq=request.settings.pipeline.relaxed_dq,
        domain_mapper=deps.yaml_config_to_domain,
    )
    transformer = TransformerBuilder(
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

    return inputs.pipeline_class.create(
        run_id=request.run_id,
        runtime=request.runtime,
        services=services,
        config=domain_config,
        shutdown_signal=ShutdownSignal(),
        transformer=transformer,
    )


def _create_silver_validator(
    pandera_silver_schema: object | None,
) -> SilverValidatorPort | None:
    """Create Pandera silver validator when schema is configured.

    Args:
        pandera_silver_schema: Optional Pandera DataFrameModel class with a
            to_schema() method; returns None when not provided.

    Returns:
        PanderaSilverValidator wrapping the schema, or None if schema is absent.
    """
    if pandera_silver_schema is None:
        return None

    from bioetl.infrastructure.validation.pandera_validator import (
        PanderaSilverValidator,
    )

    schema_builder = cast(_SchemaBuilder, pandera_silver_schema)
    typed_schema = cast("pa.DataFrameSchema | None", schema_builder.to_schema())
    return PanderaSilverValidator(typed_schema)
