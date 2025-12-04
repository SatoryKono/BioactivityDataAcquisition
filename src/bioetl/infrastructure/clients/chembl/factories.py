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
    timeout = options.get("timeout", float(source_config.timeout_sec))
    max_attempts = options.get("max_attempts", int(source_config.max_retries))
    base_delay = options.get("base_delay", 1.0)
    max_delay = options.get("max_delay", 30.0)
    backoff_factor = options.get("backoff_factor", 2.0)
    rate_limit = options.get("rate_limit_per_sec") or source_config.rate_limit_per_sec
    rate_limit_value = float(rate_limit) if rate_limit is not None else 5.0

    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=requests.Session(),
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_factor=backoff_factor,
        timeout=timeout,
    )

    return ChemblDataClientHTTPImpl(
        request_builder=ChemblRequestBuilder(
            base_url=base_url,
            max_url_length=max_len
        ),
        response_parser=ChemblResponseParser(),
        rate_limiter=default_rate_limiter(
            rate=rate_limit_value,
            capacity=rate_limit_value,
        ),
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
    client = client_options.pop("client", None) or default_chembl_client(
        source_config, **client_options
    )
    # ChEMBL API supports up to 1000 items per page.
    hard_cap = source_config.page_size or 1000
    batch_size = source_config.resolve_effective_batch_size(hard_cap=hard_cap)

    return ChemblExtractionService(
        client=client,
        batch_size=batch_size
    )
