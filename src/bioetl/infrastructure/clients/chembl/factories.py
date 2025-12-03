from typing import Any

from bioetl.infrastructure.clients.base.factories import (
    default_rate_limiter,
    default_retry_policy,
)
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
from bioetl.infrastructure.config.source_chembl import ChemblSourceConfig
from bioetl.infrastructure.services.chembl_extraction import (
    ChemblExtractionService,
)


def _resolve_base_url(options: dict[str, Any], source_config: ChemblSourceConfig) -> str:
    """
    Resolves the base URL for ChEMBL API.
    Prioritizes explicit options over source config.
    """
    base_url = options.get("base_url")
    
    if not base_url and source_config.parameters:
         base_url = source_config.parameters.base_url
         
    if not base_url or not isinstance(base_url, str):
        raise ValueError("ChEMBL base_url is required and must be a string. Check your configuration.")
        
    return base_url


def _resolve_max_url_length(options: dict[str, Any], source_config: ChemblSourceConfig) -> int | None:
    """
    Resolves max_url_length.
    """
    max_len = options.get("max_url_length")
    
    if max_len is None and source_config.parameters:
        max_len = source_config.parameters.max_url_length
        
    # Optional fallback to http defaults could be handled here if config passed
    # But strict source config is preferred.
    
    if max_len is not None and not isinstance(max_len, int):
        raise ValueError("max_url_length must be an integer.")

    return max_len


def default_chembl_client(
    source_config: ChemblSourceConfig, 
    **options: Any
) -> ChemblDataClientABC:
    """
    Creates a default ChEMBL HTTP client.
    
    Uses conservative rate limiting and exponential backoff retry policy.
    Requires source_config for URL and connection parameters.
    """
    base_url = _resolve_base_url(options, source_config)
    max_url_length = _resolve_max_url_length(options, source_config)

    return ChemblDataClientHTTPImpl(
        request_builder=ChemblRequestBuilder(base_url=base_url, max_url_length=max_url_length),
        response_parser=ChemblResponseParser(),
        rate_limiter=default_rate_limiter(rate=5.0, capacity=10.0),
        retry_policy=default_retry_policy(),
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
    # ChEMBL API typically supports up to 1000 items per page. 
    # We raise the default hard_cap (25) to 1000 to allow efficient extraction.
    batch_size = source_config.resolve_effective_batch_size(hard_cap=1000)
    
    return ChemblExtractionService(
        client=client,
        batch_size=batch_size
    )
