import time
from typing import Any, Iterator

import requests

from bioetl.infrastructure.clients.base.contracts import RateLimiterABC, RetryPolicyABC
from bioetl.infrastructure.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginator
from bioetl.infrastructure.clients.chembl.request_builder import ChemblRequestBuilder
from bioetl.infrastructure.clients.chembl.response_parser import ChemblResponseParser


class ChemblDataClientHTTPImpl(ChemblDataClientABC):
    """
    HTTP implementation of ChEMBL client.
    Uses requests, TokenBucket rate limiter, and ExponentialBackoff retry.
    """

    def __init__(
        self,
        request_builder: ChemblRequestBuilder,
        response_parser: ChemblResponseParser,
        rate_limiter: RateLimiterABC,
        retry_policy: RetryPolicyABC,
    ) -> None:
        self.request_builder = request_builder
        self.response_parser = response_parser
        self.rate_limiter = rate_limiter
        self.retry_policy = retry_policy
        self.session = requests.Session()

    def fetch_one(self, id: str) -> dict[str, Any]:
        # Generic fetch not fully supported by ChEMBL generic endpoint unless we know entity
        raise NotImplementedError("Use specific request methods")

    def fetch_many(self, ids: list[str]) -> list[dict[str, Any]]:
        raise NotImplementedError("Use specific request methods")

    def iter_pages(self, request: Any) -> Iterator[Any]:
        # In this impl, request is the URL string
        url = str(request)
        paginator = ChemblPaginator()
        
        while url:
            self.rate_limiter.wait_if_needed()
            self.rate_limiter.acquire()
            
            response_data = self._execute_request(url)
            
            yield response_data
            
            # Check for next page
            next_marker = paginator.get_next_marker(response_data)
            if next_marker:
                # Update offset in params. 
                # Complex logic if URL already has params.
                # For simplicity, assume get_next_marker logic handles it or we rebuild URL.
                # Current Paginator implementation returns next offset (int).
                # We need to update the URL with new offset.
                # This requires parsing the URL.
                # Alternative: Paginator returns next URL.
                # Let's assume Paginator logic in client is better handled by ExtractionService loop
                # or we handle it here.
                # To strictly follow iter_pages contract which yields pages:
                pass
            
            # For now, simple break to avoid infinite loop in this stub
            break

    def metadata(self) -> dict[str, Any]:
        # Fetch status to get version
        url = self.request_builder.for_endpoint("status").build({})
        data = self._execute_request(url)
        return data

    def close(self) -> None:
        self.session.close()

    def request_activity(self, **filters: Any) -> Any:
        url = self.request_builder.for_endpoint("activity").build(filters)
        return self._execute_request(url)

    def request_assay(self, **filters: Any) -> Any:
        url = self.request_builder.for_endpoint("assay").build(filters)
        return self._execute_request(url)

    def request_target(self, **filters: Any) -> Any:
        url = self.request_builder.for_endpoint("target").build(filters)
        return self._execute_request(url)

    def request_document(self, **filters: Any) -> Any:
        url = self.request_builder.for_endpoint("document").build(filters)
        return self._execute_request(url)

    def request_molecule(self, **filters: Any) -> Any:
        url = self.request_builder.for_endpoint("molecule").build(filters)
        return self._execute_request(url)

    def _execute_request(self, url: str) -> dict[str, Any]:
        attempt = 1
        while True:
            try:
                response = self.session.get(url)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if not self.retry_policy.should_retry(e, attempt):
                    raise
                time.sleep(self.retry_policy.get_delay(attempt))
                attempt += 1


# NOTE: iter_pages реализован частично (возвращает только первую страницу без перехода по next).
# Планируется доработать построение next-URL для полноценной пагинации.

