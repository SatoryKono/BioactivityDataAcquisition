"""Compatibility helpers for the legacy pipeline factory facade."""

from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.composition.factories.services.bundle import ServiceBundleDependencies
from bioetl.composition.factories.services.factory import BaseServicesFactory
from bioetl.composition.services.versioning import compute_config_hash
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
    )
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.config import RuntimeConfig
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

_BUILD_PIPELINE_SERVICES_WARNING = (
    "Use bioetl.composition.factories.services.bundle.build_pipeline_services "
    "for direct wiring. pipeline_factory facade remains for compatibility."
)
_CREATE_PIPELINE_WITH_SERVICES_WARNING = (
    "Use bioetl.composition.factories.services.bundle.create_pipeline_with_services "
    "for direct wiring. pipeline_factory facade remains for compatibility."
)


def build_compat_service_bundle_dependencies() -> ServiceBundleDependencies:
    """Build compatibility dependencies bound to legacy facade symbols."""
    return ServiceBundleDependencies(
        load_pipeline_config=load_pipeline_config,
        yaml_config_to_domain=yaml_config_to_domain,
        compute_config_hash=compute_config_hash,
        base_services_factory=BaseServicesFactory,
    )


def call_build_pipeline_services_compat(
    *,
    build_pipeline_services_fn: Callable[..., PipelineService],
    pipeline_name: str,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    logger: LoggerPort,
    config: PipelineYamlConfig | None = None,
    filter_config: InputFilterConfig | None = None,
    tracer: TracingPort | None = None,
    dq_monitor: DQMonitorPort | None = None,
    metadata_coordinator: MetadataCoordinator | None = None,
    cached_bronze: CachedBronzeContext | None = None,
    silver_validator: SilverValidatorPort | None = None,
    deps: ServiceBundleDependencies | None = None,
) -> PipelineService:
    """Run the deprecated build facade with warning and compat dependencies."""
    warnings.warn(
        _BUILD_PIPELINE_SERVICES_WARNING,
        DeprecationWarning,
        stacklevel=3,
    )
    return build_pipeline_services_fn(
        pipeline_name=pipeline_name,
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        logger=logger,
        config=config,
        filter_config=filter_config,
        tracer=tracer,
        dq_monitor=dq_monitor,
        metadata_coordinator=metadata_coordinator,
        cached_bronze=cached_bronze,
        silver_validator=silver_validator,
        _deps=deps or build_compat_service_bundle_dependencies(),
    )


def call_create_pipeline_with_services_compat(
    *,
    create_pipeline_with_services_fn: Callable[..., BasePipeline],
    pipeline_name: str,
    pipeline_class: type[BasePipeline],
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
    deps: ServiceBundleDependencies | None = None,
) -> BasePipeline:
    """Run the deprecated create facade with warning and compat dependencies."""
    warnings.warn(
        _CREATE_PIPELINE_WITH_SERVICES_WARNING,
        DeprecationWarning,
        stacklevel=3,
    )
    return create_pipeline_with_services_fn(
        pipeline_name=pipeline_name,
        pipeline_class=pipeline_class,
        provider=provider,
        create_data_source_fn=create_data_source_fn,
        transformer_class=transformer_class,
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
        pandera_silver_schema=pandera_silver_schema,
        _deps=deps or build_compat_service_bundle_dependencies(),
    )
