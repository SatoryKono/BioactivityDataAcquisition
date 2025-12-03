from typing import Any, Iterator

import requests

from bioetl.domain.errors import ClientResponseError
from bioetl.infrastructure.clients.base.contracts import RateLimiterABC
from bioetl.infrastructure.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginator
from bioetl.infrastructure.clients.chembl.request_builder import ChemblRequestBuilder
from bioetl.infrastructure.clients.chembl.response_parser import ChemblResponseParser
from bioetl.infrastructure.clients.middleware import HttpClientMiddleware


class ChemblDataClientHTTPImpl(ChemblDataClientABC):
    """
    HTTP implementation of ChEMBL client.
    Uses rate limiter and middleware with retry/backoff.
    """

    def __init__(
        self,
        request_builder: ChemblRequestBuilder,
        response_parser: ChemblResponseParser,
        rate_limiter: RateLimiterABC,
        http_middleware: HttpClientMiddleware | None = None,
        *,
        provider: str = "chembl",
    ) -> None:
        self.request_builder = request_builder
        self.response_parser = response_parser
        self.rate_limiter = rate_limiter
        self.provider = provider

        if http_middleware is None:
            self.session = requests.Session()
            self.http = HttpClientMiddleware(
                provider=provider,
                base_client=self.session,
            )
        else:
            self.http = http_middleware
            base_client = getattr(http_middleware, "base_client", None)
            self.session = base_client if base_client is not None else requests.Session()

    def fetch_one(self, id: str) -> dict[str, Any]:
        # Generic fetch not fully supported by ChEMBL generic endpoint unless we know entity
        raise NotImplementedError("Use specific request methods")

    def fetch_many(self, ids: list[str]) -> list[dict[str, Any]]:
        raise NotImplementedError("Use specific request methods")

    def iter_pages(self, request: Any) -> Iterator[Any]:
        url = str(request)
        paginator = ChemblPaginator()

        while url:
            self.rate_limiter.wait_if_needed()
            self.rate_limiter.acquire()

            response_data = self._execute_request(url)

            yield response_data

            next_marker = paginator.get_next_marker(response_data)
            if next_marker:
                pass

            break

    def metadata(self) -> dict[str, Any]:
        url = self.request_builder.for_endpoint("status").build({})
        data = self._execute_request(url)
        return data

    def close(self) -> None:
        close_method = getattr(self.session, "close", None)
        if callable(close_method):
            close_method()

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


# NOTE: iter_pages реализован частично (возвращает только первую страницу без перехода по next).
# Планируется доработать построение next-URL для полноценной пагинации.
