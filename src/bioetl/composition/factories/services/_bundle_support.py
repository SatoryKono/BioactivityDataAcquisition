"""Private support helpers for service-bundle wiring."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline.creation_support import (
    _PipelineCreationInputs,
    _PipelineCreationRequest,
)

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
    )
    from bioetl.composition.factories.services.factory import BaseServicesFactory
    from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import (
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class ServiceBundleDependencies:
    """Explicit dependency set for service-bundle wiring."""

    load_pipeline_config: Callable[[str], PipelineYamlConfig]
    yaml_config_to_domain: Callable[
        [PipelineYamlConfig, DQConfig | None], PipelineConfig
    ]
    compute_config_hash: Callable[[PipelineYamlConfig | dict[str, object]], str]
    base_services_factory: type[BaseServicesFactory]


def resolve_service_bundle_dependencies(
    *,
    override: ServiceBundleDependencies | None,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    yaml_config_to_domain_fn: Callable[
        [PipelineYamlConfig, DQConfig | None], PipelineConfig
    ],
    compute_config_hash_fn: Callable[[PipelineYamlConfig | dict[str, object]], str],
    base_services_factory: type[BaseServicesFactory],
) -> ServiceBundleDependencies:
    """Resolve runtime dependencies with an optional test override."""
    if override is not None:
        return override
    return ServiceBundleDependencies(
        load_pipeline_config=load_pipeline_config_fn,
        yaml_config_to_domain=yaml_config_to_domain_fn,
        compute_config_hash=compute_config_hash_fn,
        base_services_factory=base_services_factory,
    )


def create_pipeline_data_source(
    *,
    pipeline_name: str,
    pipeline_config: PipelineYamlConfig,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort,
    cached_bronze: CachedBronzeContext | None,
    create_cached_bronze_data_source_fn: Callable[..., DataSourcePort],
    create_data_source_impl_fn: Callable[..., DataSourcePort],
) -> DataSourcePort:
    """Resolve live-vs-cached data source construction for one pipeline run."""
    if cached_bronze is not None and cached_bronze.enabled:
        data_source = create_cached_bronze_data_source_fn(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            cached_bronze=cached_bronze,
        )
        logger.info(
            "using_cached_bronze_mode",
            pipeline=pipeline_name,
            bronze_path=cached_bronze.bronze_path,
            bronze_date=cached_bronze.bronze_date,
        )
        return data_source
    return create_data_source_impl_fn(
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
    )


def build_pipeline_creation_inputs(
    *,
    pipeline_name: str,
    pipeline_class: type[BasePipeline],
    provider: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    transformer_class: type[BaseTransformer] | None,
    run_id: RunID,
    runtime: RuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    manifest_id: str | None,
    config_hash: str | None,
    dq_contract_compatibility_hash: str | None,
    effective_config_artifact_id: str | None,
    config: PipelineYamlConfig | None,
    filter_config: InputFilterConfig | None,
    tracer: TracingPort | None,
    dq_monitor: DQMonitorPort | None,
    metrics: MetricsPort | None,
    cached_bronze: CachedBronzeContext | None,
    pandera_silver_schema: object | None,
) -> _PipelineCreationInputs:
    """Build the delegated pipeline-creation envelope."""
    return _PipelineCreationInputs(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        create_data_source_fn=create_data_source_fn,
        transformer_class=transformer_class,
        request=_PipelineCreationRequest(
            run_id=run_id,
            runtime=runtime,
            settings=settings,
            logger=logger,
            manifest_id=manifest_id,
            config_hash=config_hash,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
            config=config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
            metrics=metrics,
            cached_bronze=cached_bronze,
        ),
        pandera_silver_schema=pandera_silver_schema,
    )
