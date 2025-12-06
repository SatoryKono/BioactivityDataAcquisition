"""
Implementation of ChEMBL HTTP client.
"""

from __future__ import annotations

from typing import Any, Iterator

from bioetl.domain.clients.base.contracts import RateLimiterABC
from bioetl.domain.clients.chembl.contracts import ChemblDataClientABC
from bioetl.domain.errors import ClientResponseError
from bioetl.infrastructure.clients.base.impl.unified_client import UnifiedAPIClient
from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginatorImpl
from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilderImpl,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParserImpl,
)
from bioetl.infrastructure.clients.middleware import HttpClientMiddleware


class ChemblDataClientHTTPImpl(ChemblDataClientABC):
    """
    HTTP implementation of ChEMBL client.
    Uses UnifiedAPIClient for requests and RateLimiter for proactive throttling.
    """

    def __init__(
        self,
        request_builder: ChemblRequestBuilderImpl,
        response_parser: ChemblResponseParserImpl,
        rate_limiter: RateLimiterABC,
        client: UnifiedAPIClient | None = None,
        *,
        http_middleware: HttpClientMiddleware | None = None,
        provider: str = "chembl",
    ) -> None:
        self.request_builder = request_builder
        self.response_parser = response_parser
        self.rate_limiter = rate_limiter
        self.client = client
        if http_middleware is not None:
            self.http = http_middleware
        elif client is not None:
            self.http = client.middleware
        else:
            # Fallback stub to keep attribute accessible in tests;
            # real runs must inject middleware.
            class _NullHttpMiddleware:
                def request(
                    self, method: str, url: str, **_: Any
                ) -> Any:  # pragma: no cover
                    raise RuntimeError("HTTP middleware is not configured")

            self.http = _NullHttpMiddleware()
        self.provider = provider

    # pylint: disable=redefined-builtin
    def fetch_one(self, id: str) -> dict[str, Any]:
        # Generic fetch not fully supported by ChEMBL generic endpoint
        # unless we know entity
        raise NotImplementedError("Use specific request methods")

    def fetch_many(self, ids: list[str]) -> list[dict[str, Any]]:
        raise NotImplementedError("Use specific request methods")

    def iter_pages(self, request: Any) -> Iterator[Any]:
        url = str(request)
        paginator = ChemblPaginatorImpl()

        while url:
            self.rate_limiter.wait_if_needed()
            self.rate_limiter.acquire()

            response_data = self._execute_request(url)

            yield response_data

            next_request = paginator.get_next_request(response_data, url)
            if next_request:
                url = next_request
            else:
                break

    def metadata(self) -> dict[str, Any]:
        url = self.request_builder.for_endpoint("status").build({})
        data = self._execute_request(url)
        return data

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
        elif hasattr(self.http, "base_client") and hasattr(
            self.http.base_client, "close"
        ):
            self.http.base_client.close()

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
        response = self.http.request("GET", url)
        try:
            return response.json()
        except ValueError as exc:
            raise ClientResponseError(
                provider=self.provider,
                endpoint=url,
                status_code=getattr(response, "status_code", None),
                message="Failed to parse response JSON",
                cause=exc,
            ) from exc
