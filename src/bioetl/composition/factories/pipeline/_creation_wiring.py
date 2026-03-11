"""Internal pipeline creation wiring extracted from service bundle facade."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.composition.factories.pipeline.construction import (
    DomainConfigResolver,
    RunContextFactory,
    TransformerBuilder,
)
from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
from bioetl.composition.services.versioning import get_git_commit, get_pipeline_version
from bioetl.infrastructure.config import load_pipeline_contract_policy
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.composition.factories.datasource.factory import DataSourceCreator
    from bioetl.composition.factories.pipeline.construction import (
        EntityTypeExtractor,
    )
    from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import (
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


from bioetl.composition.factories.pipeline.contract_validator import (
    _SchemaBuilder,
)


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
        create_data_source_fn: DataSourceCreator,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        cached_bronze: CachedBronzeContext | None = None,
        silver_validator: SilverValidatorPort | None = None,
        _deps: object | None = None,
    ) -> PipelineService: ...


@dataclass(frozen=True, slots=True)
class _PipelineCreationInputs:
    """Immutable input bundle for pipeline creation."""

    pipeline_name: str
    pipeline_class: type[BasePipeline]
    provider: str
    create_data_source_fn: DataSourceCreator
    transformer_class: type[BaseTransformer] | None
    run_id: RunID
    runtime: RuntimeConfig
    settings: Settings
    logger: LoggerPort
    config: PipelineYamlConfig | None = None
    filter_config: InputFilterConfig | None = None
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None
    metrics: MetricsPort | None = None
    cached_bronze: CachedBronzeContext | None = None
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
    yaml_config = inputs.config or deps.load_pipeline_config(inputs.pipeline_name)
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
            run_id=inputs.run_id,
            runtime=inputs.runtime,
            yaml_config=yaml_config,
        )
    )

    services = build_pipeline_services_fn(
        pipeline_name=inputs.pipeline_name,
        create_data_source_fn=inputs.create_data_source_fn,
        settings=inputs.settings,
        logger=inputs.logger,
        config=yaml_config,
        filter_config=inputs.filter_config,
        tracer=inputs.tracer,
        dq_monitor=inputs.dq_monitor,
        metadata_coordinator=metadata_coordinator,
        cached_bronze=inputs.cached_bronze,
        silver_validator=_create_silver_validator(inputs.pandera_silver_schema),
    )
    domain_config = DomainConfigResolver(
        configs_root=Path("configs"),
        loader_class=PipelineConfigLoader,
        domain_mapper=deps.yaml_config_to_domain,
    ).resolve(
        yaml_config,
        relaxed_dq=inputs.settings.pipeline.relaxed_dq,
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
        tracer=inputs.tracer,
        metrics=inputs.metrics,
    )

    return inputs.pipeline_class.create(
        run_id=inputs.run_id,
        runtime=inputs.runtime,
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
