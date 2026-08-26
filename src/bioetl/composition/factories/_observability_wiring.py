"""Observability/data-source wiring helpers for service bundle factory."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bioetl.composition.observability_resolution import resolve_metrics_port

# Import types used in function signatures (runtime imports handled by composition)
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import InputFilterConfig
from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

from .datasource.data_source_factory import DataSourceCreatorProtocol

from bioetl.application.ports.metrics import MetricsFactoryProtocol as _MetricsFactory


def create_shared_metrics(
    *,
    settings: Settings,
    base_services_factory: _MetricsFactory,
) -> MetricsPort:
    """Create shared pipeline metrics via base services factory.

    Args:
        settings: Application settings used to configure the metrics backend.
        base_services_factory: Factory class providing the metrics creation method.

    Returns:
        Configured MetricsPort for shared use across pipeline components.
    """
    return base_services_factory._create_metrics(settings)


def _create_data_source(
    *,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort | None,
    pipeline_name: str,
) -> DataSourcePort:
    """Create provider data source through factory callback."""
    return create_data_source_fn(
        settings,
        pipeline_config,
        logger,
        filter_config,
        metrics=metrics,
        pipeline_name=pipeline_name,
    )


def _create_cached_bronze_data_source(
    *,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
    cached_bronze: CachedBronzeContext,
) -> DataSourcePort:
    """Create CachedBronzeDataSource for reading from Bronze cache."""
    from bioetl.infrastructure import adapters
    from bioetl.infrastructure.storage import bronze_writer

    provider = pipeline_config.provider
    entity_type = pipeline_config.entity_type

    if cached_bronze.bronze_path:
        configured_path = Path(cached_bronze.bronze_path)
        scoped_path = configured_path / provider / entity_type
        bronze_path = scoped_path if scoped_path.is_dir() else configured_path
    else:
        bronze_path = settings.bronze_path / provider / entity_type

    bronze_reader = bronze_writer.BronzeWriter(
        base_path=bronze_path,
        logger=logger,
        metrics=resolve_metrics_port(metrics=metrics, settings=settings),
        flat_structure=True,
    )
    return adapters.CachedBronzeDataSource(
        bronze_reader=bronze_reader,
        provider=provider,
        entity_type=entity_type,
        logger=logger,
        bronze_date=cached_bronze.bronze_date,
    )


def create_data_source_with_observability(
    *,
    create_data_source_fn: DataSourceCreatorProtocol,
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    shared_metrics: MetricsPort,
    pipeline_name: str,
    cached_bronze: CachedBronzeContext | None,
    create_cached_bronze_data_source_fn: Callable[..., DataSourcePort] | None = None,
    create_data_source_impl_fn: Callable[..., DataSourcePort] | None = None,
) -> DataSourcePort:
    """Create data source and emit cached-bronze observability logs.

    Args:
        create_data_source_fn: Factory callable producing a live DataSourcePort.
        settings: Application settings for data source configuration.
        pipeline_config: Pipeline YAML config providing provider and entity type.
        logger: LoggerPort for structured observability logging.
        filter_config: Optional input filter configuration for data source.
        shared_metrics: Shared MetricsPort passed to the live data source.
        pipeline_name: Pipeline name used in log events.
        cached_bronze: Optional cached Bronze context; if enabled, bypasses live API.

    Returns:
        DataSourcePort configured for live API or cached Bronze data.
    """
    cached_bronze_factory = (
        create_cached_bronze_data_source_fn or _create_cached_bronze_data_source
    )
    data_source_factory = create_data_source_impl_fn or _create_data_source
    if cached_bronze is not None and cached_bronze.enabled:
        data_source = cached_bronze_factory(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            metrics=shared_metrics,
            cached_bronze=cached_bronze,
        )
        logger.info(
            "using_cached_bronze_mode",
            pipeline=pipeline_name,
            bronze_path=cached_bronze.bronze_path,
            bronze_date=cached_bronze.bronze_date,
        )
        return data_source

    return data_source_factory(
        create_data_source_fn=create_data_source_fn,
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        filter_config=filter_config,
        metrics=shared_metrics,
        pipeline_name=pipeline_name,
    )
