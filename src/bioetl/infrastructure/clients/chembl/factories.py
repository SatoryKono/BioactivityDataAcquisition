"""
Factories for ChEMBL clients.
"""

from typing import Any

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.configs import ChemblSourceConfig, HttpClientConfig
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC
from bioetl.infrastructure.clients.base.factories import (
    build_http_client,
    build_rate_limiter,
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
    create_activity_parser,
)


def default_chembl_client(
    source_config: ChemblSourceConfig,
    http_config: HttpClientConfig | None = None,
    **options: Any,
) -> DataClientABC:
    """
    Создает клиент ChEMBL по умолчанию.

    Args:
        source_config: Конфигурация источника.
        http_config: HTTP конфигурация (опционально, берется из source_config.http).
        **options: Дополнительные опции.

    Returns:
        Настроенный экземпляр клиента.
    """
    # Use provided config or fall back to source_config.http
    resolved_config = http_config or source_config.http
    logger: LoggingPortABC | None = options.get("logger")

    # Create Unified HTTP Client
    unified_client = build_http_client(
        provider="chembl",
        config=resolved_config,
        logger=logger,
    )

    # Allow explicit overrides via kwargs (used in tests and manual runs)
    override_base_url = options.get("base_url")
    base_url = str(override_base_url or source_config.base_url)
    max_url_length = options.get("max_url_length", source_config.max_url_length)

    # Rate limiter for proactive limiting
    rate_limiter = build_rate_limiter(config=resolved_config, logger=logger)

    return ChemblHttpClientImpl(
        request_builder=ChemblRequestBuilderImpl(
            base_url=base_url,
            max_url_length=max_url_length,
        ),
        response_parser=create_activity_parser(),
        rate_limiter=rate_limiter,
        client=unified_client,
        provider="chembl",
        logger=logger,
        fallbacks=source_config.fallbacks or {},
    )


def default_chembl_extraction_service(
    config: ChemblSourceConfig,
    http_config: HttpClientConfig | None = None,
    *,
    client: DataClientABC | None = None,
    logger: LoggingPortABC | None = None,
    field_provider: DefaultFieldProviderABC | None = None,
) -> ExtractionServiceABC:
    """
    Создает сервис экстракции ChEMBL.

    Args:
        config: Конфигурация источника.
        http_config: HTTP конфигурация (опционально).
        client: Уже созданный клиент (опционально).
        logger: Логгер.
        field_provider: Провайдер полей.

    Returns:
        Сервис экстракции.
    """
    resolved_config = http_config or config.http

    if client is None:
        client = default_chembl_client(
            config, http_config=resolved_config, logger=logger
        )

    return ChemblExtractionServiceImpl(
        client=client,
        # Allow provider config to set batch_size while keeping a generous hard cap
        batch_size=config.resolve_effective_batch_size(hard_cap=1000),
        logger=logger,
    )
