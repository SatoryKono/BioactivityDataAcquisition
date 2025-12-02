from bioetl.infrastructure.clients.base.factories import default_rate_limiter, default_retry_policy
from bioetl.infrastructure.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.clients.chembl.impl.http_client import ChemblDataClientHTTPImpl
from bioetl.infrastructure.clients.chembl.request_builder import ChemblRequestBuilder
from bioetl.infrastructure.clients.chembl.response_parser import ChemblResponseParser
from bioetl.application.pipelines.chembl.extraction import ChemblExtractionService


def default_chembl_client() -> ChemblDataClientABC:
    """
    Creates a default ChEMBL HTTP client.
    
    Uses conservative rate limiting and exponential backoff retry policy.
    """
    return ChemblDataClientHTTPImpl(
        request_builder=ChemblRequestBuilder(),
        response_parser=ChemblResponseParser(),
        rate_limiter=default_rate_limiter(rate=5.0, capacity=10.0),
        retry_policy=default_retry_policy(),
    )


def default_chembl_extraction_service() -> ChemblExtractionService:
    """
    Creates a default ChEMBL extraction service.
    
    Uses default client and standard batch size.
    """
    return ChemblExtractionService(
        client=default_chembl_client(),
        batch_size=1000
    )

