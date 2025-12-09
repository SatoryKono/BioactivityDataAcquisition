"""
Factories for ChEMBL clients.
"""

from typing import Any

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.configs import ChemblSourceConfig, ClientConfig
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC
from bioetl.infrastructure.clients.base.factories import (
    default_api_client,
    default_rate_limiter,
)
from bioetl.infrastructure.clients.chembl.impl import (
    ChemblExtractionServiceImpl,
)
from bioetl.infrastructure.clients.chembl.impl.http_client import ChemblApiPortImpl
from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilderImpl,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParserImpl,
)


def default_chembl_client(
    source_config: ChemblSourceConfig,
    client_config: ClientConfig | None = None,
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
    if client_config is None:
        client_config = source_config.client.model_copy(deep=True)

    # Create Unified Client
    unified_client = default_api_client(
        provider="chembl",
        config=client_config,
    )

    # Allow explicit overrides via kwargs (used in tests and manual runs)
    base_url = str(options.get("base_url", source_config.base_url))
    max_url_length = options.get("max_url_length", source_config.max_url_length)

    # Rate limiter for proactive limiting (in addition to middleware backoff)
    # Using explicit rate limiter in client logic
    rate_limiter = default_rate_limiter(
        rate=client_config.rate_limit_per_sec,
        capacity=max(1.0, client_config.rate_limit_per_sec),
    )

    return ChemblApiPortImpl(
        request_builder=ChemblRequestBuilderImpl(
            base_url=base_url,
            max_url_length=max_url_length,
        ),
        response_parser=ChemblResponseParserImpl(),
        rate_limiter=rate_limiter,
        client=unified_client,
        provider="chembl",
    )


def default_chembl_extraction_service(
    config: ChemblSourceConfig,
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
    if client is None:
        client = default_chembl_client(config, client_config=client_config)

    return ChemblExtractionServiceImpl(
        client=client,
        # Allow provider config to set batch_size while keeping a generous hard cap
        batch_size=config.resolve_effective_batch_size(hard_cap=1000),
        logger=logger,
    )
