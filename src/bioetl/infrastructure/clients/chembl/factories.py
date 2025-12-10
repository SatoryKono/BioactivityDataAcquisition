"""Factories for ChEMBL clients.

All factories require explicit dependencies - no implicit defaults.
Use CompositionRoot for creating instances with default implementations.
"""

from typing import Any

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.configs import ChemblSourceConfig, HttpClientConfig
from bioetl.domain.observability.contracts import LoggingPortABC, MetricsPortABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC
from bioetl.infrastructure.clients.base.factories import (
    build_http_client,
    build_rate_limiter,
)
from bioetl.infrastructure.clients.base.http_error_handler import (
    DefaultHttpErrorHandler,
)
from bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl import (
    ChemblExtractionServiceImpl,
)
from bioetl.infrastructure.clients.chembl.impl.chembl_http_client_impl import (
    ChemblHttpClientImpl,
)
from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilderImpl,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)


def default_chembl_client(
    source_config: ChemblSourceConfig,
    logger: LoggingPortABC,
    metrics: MetricsPortABC,
    http_config: HttpClientConfig | None = None,
    **options: Any,
) -> DataClientABC:
    """
    Create default ChEMBL client with explicit dependencies.

    Args:
        source_config: Source configuration.
        logger: Required logger instance.
        metrics: Required metrics instance.
        http_config: Optional HTTP configuration (defaults to source_config.http).
        **options: Additional options (base_url, max_url_length).

    Returns:
        Configured client instance.
    """
    # Use provided config or fall back to source_config.http
    resolved_config = http_config or source_config.http

    # Create Unified HTTP Client
    unified_client = build_http_client(
        provider="chembl",
        logger=logger,
        metrics=metrics,
        config=resolved_config,
    )

    # Allow explicit overrides via kwargs (used in tests and manual runs)
    override_base_url = options.get("base_url")
    base_url = str(override_base_url or source_config.base_url)
    max_url_length = options.get("max_url_length", source_config.max_url_length)

    # Rate limiter for proactive limiting
    rate_limiter = build_rate_limiter(logger, config=resolved_config)

    # Create unified error handler
    error_handler = DefaultHttpErrorHandler(logger)

    return ChemblHttpClientImpl(
        request_builder=ChemblRequestBuilderImpl(
            base_url=base_url,
            max_url_length=max_url_length,
        ),
        response_parser=ChemblGenericResponseParser(),
        rate_limiter=rate_limiter,
        http_client=unified_client,
        logger=logger,
        provider="chembl",
        fallbacks=source_config.fallbacks or {},
        error_handler=error_handler,
    )


def default_chembl_extraction_service(
    config: ChemblSourceConfig,
    logger: LoggingPortABC,
    metrics: MetricsPortABC,
    http_config: HttpClientConfig | None = None,
    *,
    client: DataClientABC | None = None,
    field_provider: DefaultFieldProviderABC | None = None,
    parser: ResponseParserPortABC | None = None,
) -> ExtractionServiceABC:
    """Create ChEMBL extraction service with generic parser.

    Args:
        config: Source configuration.
        logger: Required logger instance.
        metrics: Required metrics instance.
        http_config: Optional HTTP configuration.
        client: Optional pre-created client.
        field_provider: Optional field provider.
        parser: Optional parser instance (defaults to ChemblGenericResponseParser).

    Returns:
        Configured extraction service returning raw dicts.
    """
    resolved_config = http_config or config.http

    if client is None:
        client = default_chembl_client(
            config, logger=logger, metrics=metrics, http_config=resolved_config
        )

    return ChemblExtractionServiceImpl(
        client=client,
        logger=logger,
        # Allow provider config to set batch_size while keeping a generous hard cap
        batch_size=config.resolve_effective_batch_size(hard_cap=1000),
        field_provider=field_provider,
        parser=parser or ChemblGenericResponseParser(),
    )
