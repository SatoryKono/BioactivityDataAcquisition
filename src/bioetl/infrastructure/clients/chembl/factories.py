from typing import Any

import requests

from bioetl.infrastructure.clients.base.factories import default_rate_limiter
from bioetl.infrastructure.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.clients.chembl.impl.http_client import (
    ChemblDataClientHTTPImpl,
)
from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilder,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParser,
)
from bioetl.infrastructure.clients.middleware import HttpClientMiddleware
from bioetl.application.services.chembl_extraction import (
    ChemblExtractionService,
)
from bioetl.infrastructure.config.models import ChemblSourceConfig


def default_chembl_client(
    source_config: ChemblSourceConfig,
    **options: Any
) -> ChemblDataClientABC:
    """
    Creates a default ChEMBL HTTP client.

    Uses conservative rate limiting and exponential backoff retry.
    Config fields are now top-level (no nested 'parameters').
    """
    base_url = str(options.get("base_url") or source_config.base_url)
    max_len = options.get("max_url_length") or source_config.max_url_length

    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=requests.Session(),
        max_attempts=options.get("max_attempts", 3),
        base_delay=options.get("base_delay", 1.0),
        max_delay=options.get("max_delay", 30.0),
        backoff_factor=options.get("backoff_factor", 2.0),
        timeout=options.get("timeout", 30.0),
        circuit_breaker_threshold=options.get("circuit_breaker_threshold", 5),
        circuit_breaker_recovery_time=options.get("circuit_breaker_recovery_time", 60.0),
    )

    return ChemblDataClientHTTPImpl(
        request_builder=ChemblRequestBuilder(
            base_url=base_url,
            max_url_length=max_len
        ),
        response_parser=ChemblResponseParser(),
        rate_limiter=default_rate_limiter(rate=5.0, capacity=10.0),
        http_middleware=middleware,
        provider="chembl",
    )


def default_chembl_extraction_service(
    source_config: ChemblSourceConfig,
    **client_options: Any
) -> ChemblExtractionService:
    """
    Creates a default ChEMBL extraction service.

    Uses default client and configured batch size.
    """
    client = default_chembl_client(source_config, **client_options)
    # ChEMBL API supports up to 1000 items per page.
    batch_size = source_config.resolve_effective_batch_size(hard_cap=1000)

    return ChemblExtractionService(
        client=client,
        batch_size=batch_size
    )
