"""Configuration helpers for provider registration.

Utility functions for loading and extracting provider configuration
from YAML source configs. Split from registration.py per
audit-package-structure-2026-02-07.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.core.filtered_data_source import FilteredDataSource
from bioetl.composition.bootstrap_contexts import (
    CircuitBreakerConfig,
    RateLimitContext,
)
from bioetl.domain.resilience import AdapterConfig
from bioetl.infrastructure.adapters.input.csv_filter_reader import CsvFilterReader
from bioetl.infrastructure.config import load_source_config

if TYPE_CHECKING:
    from typing import Any

    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def _get_factories(
    *,
    data_source_factory_getter: Callable[[], Any],
    http_client_factory_getter: Callable[[], Any],
) -> tuple[Any, Any]:
    """Resolve factory classes via injected getters.

    Keeps this helper module decoupled from factory modules to avoid
    cross-import dependency chains.
    """
    return data_source_factory_getter(), http_client_factory_getter()


def _get_source_config(provider: str) -> SourceYamlConfig | None:
    """Load config from configs/sources/{provider}.yaml or return None.

    Returns:
        SourceYamlConfig if found, None if config file does not exist.

    Raises:
        ValueError: If config file exists but is invalid.
    """
    from pathlib import Path

    config_path = Path(f"configs/sources/{provider}.yaml")
    if not config_path.exists():
        return None
    return load_source_config(provider)


def _get_batch_size_from_config(provider: str, default: int = 100) -> int:
    """Get batch size from source config or return default."""
    source_config = _get_source_config(provider)
    return source_config.batch_size if source_config else default


def _get_rate_limit_from_config(provider: str) -> RateLimitContext:
    """Get rate limit configuration from source config or defaults.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').

    Returns:
        RateLimitContext with rate and capacity values.
    """
    source_config = _get_source_config(provider)
    if source_config:
        return RateLimitContext(
            rate=source_config.rate_limit.requests_per_second,
            capacity=source_config.rate_limit.burst,
        )
    return RateLimitContext(rate=5.0, capacity=10)


def _get_circuit_breaker_from_config(provider: str) -> CircuitBreakerConfig:
    """Get circuit breaker configuration from source config or defaults.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').

    Returns:
        CircuitBreakerConfig with failure_threshold and recovery_timeout.
    """
    source_config = _get_source_config(provider)
    if source_config:
        return CircuitBreakerConfig(
            failure_threshold=source_config.circuit_breaker.failure_threshold,
            recovery_timeout=source_config.circuit_breaker.recovery_timeout,
        )
    return CircuitBreakerConfig(failure_threshold=5, recovery_timeout=300)


def _get_adapter_config(provider: str, default_page_size: int = 1000) -> AdapterConfig:
    """Get AdapterConfig from source YAML config.

    This is the single source of truth for adapter parameters (RULES.md §12.1.2).
    Loads from configs/sources/{provider}.yaml and converts to domain dataclass.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem')
        default_page_size: Default page size if not specified in config

    Returns:
        AdapterConfig: Immutable adapter configuration

    Raises:
        ValueError: If source config file exists but is invalid.
    """
    source_config = _get_source_config(provider)
    if source_config is not None:
        return source_config.to_adapter_config(default_page_size=default_page_size)

    # Fallback to domain defaults when config file does not exist
    return AdapterConfig(page_size=default_page_size)


def _wrap_with_filter(
    data_source: DataSourcePort,
    filter_config: InputFilterConfig | None,
    logger: LoggerPort | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Wrap data source with FilteredDataSource if filter is enabled."""
    if filter_config and filter_config.enabled:
        return FilteredDataSource(
            data_source=data_source,
            filter_reader=CsvFilterReader(logger=logger),
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
            logger=logger,
        )
    return data_source
