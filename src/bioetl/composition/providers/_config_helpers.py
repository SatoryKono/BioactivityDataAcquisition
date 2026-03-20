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
from bioetl.infrastructure.config.source_config_loader import load_source_config

if TYPE_CHECKING:
    from bioetl.composition.providers._registration_contracts import (
        ProviderAssemblySupport,
    )
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.models.filter import ExtractionParams
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def _get_source_config(provider: str) -> SourceYamlConfig | None:
    """Load config from configs/providers/{provider}.yaml or return None.

    Args:
        provider: Provider name used to locate the YAML source config file.

    Returns:
        SourceYamlConfig if found, None if config file does not exist.

    Raises:
        yaml.YAMLError, pydantic.ValidationError: If config file exists but is invalid.
    """
    try:
        return load_source_config(provider)
    except ValueError:
        return None


def _get_batch_size_from_config(provider: str, default: int = 100) -> int:
    """Get batch size from source config or return default.

    Args:
        provider: Provider name used to locate the source config.
        default: Batch size to use when source config is absent; defaults to 100.

    Returns:
        Configured batch size from source YAML, or default.
    """
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
    Loads from configs/providers/{provider}.yaml and converts to domain dataclass.

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


def _validate_extraction_input_filter_overlap(
    extraction_params: ExtractionParams,
    input_filter: InputFilterConfig,
    logger: LoggerPort,
) -> None:
    """Warn if input_filter field overlaps extraction_params keys.

    Args:
        extraction_params: Extraction parameters that may overlap with filter fields.
        input_filter: Input filter configuration specifying filter fields.
        logger: LoggerPort used to emit overlap warnings.
    """
    if not input_filter.enabled or extraction_params.is_empty:
        return

    filter_field = input_filter.filter_field
    if filter_field and filter_field in extraction_params.params:
        logger.warning(
            "extraction_params_input_filter_overlap",
            overlap_field=filter_field,
            extraction_value=str(extraction_params.params[filter_field]),
            resolution="input_filter will override extraction_params for this field",
        )

    if input_filter.columns:
        for col in input_filter.columns:
            if col.filter_field in extraction_params.params:
                logger.warning(
                    "extraction_params_input_filter_overlap",
                    overlap_field=col.filter_field,
                    extraction_value=str(extraction_params.params[col.filter_field]),
                    resolution="input_filter will override",
                )


def _wrap_with_filter(
    data_source: DataSourcePort,
    filter_config: InputFilterConfig | None,
    logger: LoggerPort | None = None,
    metrics: MetricsPort | None = None,
    pipeline_name: str = "unknown",
) -> DataSourcePort:
    """Wrap data source with FilteredDataSource if filter is enabled.

    Args:
        data_source: Base data source to conditionally wrap.
        filter_config: Optional filter configuration; wraps only if enabled.
        logger: Optional LoggerPort for FilteredDataSource; defaults to None.
        metrics: Optional MetricsPort for filter statistics; defaults to None.
        pipeline_name: Pipeline name for metrics labels; defaults to 'unknown'.

    Returns:
        FilteredDataSource wrapping data_source, or data_source unchanged.
    """
    _wire_composable_fallback(data_source)

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


def _wire_composable_fallback(data_source: DataSourcePort) -> None:
    """Apply provider fallback policy once from composition root wiring.

    Args:
        data_source: Data source adapter to configure with fallback policy if
            it exposes a configure_fallback_policy method and a provider_name.
    """
    provider_name = getattr(data_source, "provider_name", None)
    if not isinstance(provider_name, str) or not provider_name.strip():
        return

    source_config = _get_source_config(provider_name)
    if source_config is None:
        return

    configure = getattr(data_source, "configure_fallback_policy", None)
    policy = source_config.provider_config.fallback
    if callable(configure) and policy is not None:
        configure(policy)


def _create_http_data_source(
    provider: str,
    settings: Settings,
    logger: LoggerPort,
    filter_config: InputFilterConfig | None,
    metrics: MetricsPort | None,
    pipeline_name: str,
    *,
    adapter_factory: Callable[..., DataSourcePort],
    extra_kwargs: dict[str, object] | None = None,
    assembly_support: ProviderAssemblySupport | None = None,
) -> DataSourcePort:
    """Generic HTTP data source: http_client + helpers + adapter + filter wrap.

    Encapsulates the shared skeleton of biblio provider creators
    (PubMed, CrossRef, OpenAlex, SemanticScholar).

    Args:
        provider: Provider name for HTTP client creation.
        settings: Application settings.
        logger: Logger port.
        filter_config: Optional input filter configuration.
        metrics: Optional metrics port.
        pipeline_name: Pipeline name for filter wrapping.
        adapter_factory: Callable that constructs the concrete adapter.
        extra_kwargs: Provider-specific kwargs merged into adapter construction.

    Returns:
        DataSourcePort, optionally wrapped with FilteredDataSource.
    """
    from bioetl.composition.factories.datasource.adapter_helpers import (
        AdapterHelpersFactory,
    )
    from bioetl.composition.providers._registration_contracts import (
        create_provider_assembly_support,
    )

    support = assembly_support or create_provider_assembly_support()
    http_client = support.create_http_client(provider, settings, metrics=metrics)
    helper_services = AdapterHelpersFactory.create_http_helpers(
        provider=provider,
        logger=logger,
        metrics=metrics,
    )
    kwargs: dict[str, object] = {
        "http_client": http_client,
        "logger": logger,
        "metrics": metrics,
        **helper_services.as_injection_kwargs(),
        **(extra_kwargs or {}),
    }
    data_source = adapter_factory(**kwargs)
    return _wrap_with_filter(data_source, filter_config, logger, metrics, pipeline_name)


def _normalize_optional_override(value: str | None) -> str | None:
    """Normalize optional pipeline override values.

    Empty strings and `${ENV_VAR}` placeholders are treated as unset to allow
    fallback to centralized settings/config providers.

    Args:
        value: Optional string value potentially containing empty strings or
            unresolved environment variable placeholders.

    Returns:
        Cleaned string value, or None if absent, empty, or an unresolved placeholder.
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.startswith("${") and cleaned.endswith("}"):
        return None
    return cleaned
