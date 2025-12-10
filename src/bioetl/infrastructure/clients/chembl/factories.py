"""
Factories for ChEMBL clients.
"""

from typing import Any

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.configs import ChemblSourceConfig, ClientConfig, HttpClientSettings
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
    ChemblResponseParserImpl,
)


def default_chembl_client(
    source_config: ChemblSourceConfig,
    http_client: HttpClientSettings | None = None,
    **options: Any,
) -> DataClientABC:
    """
    Создает клиент ChEMBL по умолчанию.

    Args:
        source_config: Конфигурация источника.
        client_config: Конфигурация клиента (опционально).
        **options: Дополнительные опции.

    Returns:
        Настроенный экземпляр клиента.
    """
    resolved_http = http_client or source_config.http_client
    client_config = ClientConfig.from_http_settings(
        resolved_http, existing=source_config.client
    )

    # Create Unified Client
    logger: LoggingPortABC | None = options.get("logger")

    unified_client = build_http_client(
        provider="chembl",
        client_config=client_config,
        http_settings=resolved_http,
        logger=logger,
    )

    # Allow explicit overrides via kwargs (used in tests and manual runs)
    override_base_url = options.get("base_url")
    base_url = str(override_base_url or resolved_http.base_url)
    if override_base_url:
        resolved_http = resolved_http.model_copy(update={"base_url": base_url})
    max_url_length = options.get("max_url_length", source_config.max_url_length)

    # Rate limiter for proactive limiting (in addition to middleware backoff)
    # Using explicit rate limiter in client logic
    rate_limiter = build_rate_limiter(
        client_config=client_config, http_settings=resolved_http, logger=logger
    )

    return ChemblHttpClientImpl(
        request_builder=ChemblRequestBuilderImpl(
            base_url=base_url,
            max_url_length=max_url_length,
        ),
        response_parser=ChemblResponseParserImpl(),
        rate_limiter=rate_limiter,
        client=unified_client,
        provider="chembl",
        logger=logger,
        fallbacks=source_config.fallbacks or {},
    )


def default_chembl_extraction_service(
    config: ChemblSourceConfig,
    http_client: HttpClientSettings | None = None,
    client_config: ClientConfig | None = None,
    *,
    client: DataClientABC | None = None,
    logger: LoggingPortABC | None = None,
    field_provider: DefaultFieldProviderABC | None = None,
) -> ExtractionServiceABC:
    """
    Создает сервис экстракции ChEMBL.

    Args:
        config: Конфигурация источника.
        client_config: Конфигурация клиента.
        client: Уже созданный клиент (опционально).

    Returns:
        Сервис экстракции.
    """
    resolved_http = http_client or config.http_client
    if client_config is not None:
        resolved_http = resolved_http.model_copy(
            update={
                "timeout": int(client_config.timeout_sec),
                "retries": client_config.max_retries,
                "backoff": float(client_config.backoff_factor),
                "rate_limit": float(client_config.rate_limit_per_sec),
                "retry_enabled": bool(client_config.retry_enabled),
            }
        )

    if client is None:
        client = default_chembl_client(config, http_client=resolved_http, logger=logger)

    return ChemblExtractionServiceImpl(
        client=client,
        # Allow provider config to set batch_size while keeping a generous hard cap
        batch_size=config.resolve_effective_batch_size(hard_cap=1000),
        logger=logger,
    )
