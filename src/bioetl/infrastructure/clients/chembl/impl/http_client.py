"""
HTTP implementation of ChEMBL API port.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any, Iterator

from bioetl.domain.clients.base.contracts import (
    ApiClientABC,
    RateLimiterABC,
    RequestBuilderABC,
    ResponseParserABC,
)
from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.observability import LoggingPortABC
from bioetl.infrastructure.errors import (
    ApiUnexpectedStatusError,
    wrap_http_errors,
)
from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginatorImpl
from bioetl.infrastructure.observability.factories import default_logging_port


class ChemblApiPortImpl(DataClientABC):
    """
    ChEMBL API port implemented over HTTP.
    Uses UnifiedAPIClientImpl for requests and RateLimiter for proactive throttling.
    """

    def __init__(
        self,
        request_builder: RequestBuilderABC,
        response_parser: ResponseParserABC,
        rate_limiter: RateLimiterABC,
        client: ApiClientABC | None = None,
        *,
        provider: str = "chembl",
        logger: LoggingPortABC | None = None,
    ) -> None:
        self.request_builder = request_builder
        self.response_parser = response_parser
        self.rate_limiter = rate_limiter
        self.client = client
        self.logger = logger or default_logging_port()
        if client is not None:
            self.http = client
        else:
            # Fallback stub to keep attribute accessible in tests;
            # real runs must inject a concrete client.
            def _missing_http_request(
                method: str, url: str, **_: Any
            ) -> Any:  # pragma: no cover
                """Fail fast when HTTP client is not configured."""
                raise RuntimeError("HTTP client is not configured")

            self.http = SimpleNamespace(request=_missing_http_request)
        self.provider = provider

    def iter_pages(self, request: Any) -> Iterator[Any]:
        """Iterate over paginated responses for a built request."""
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
        """Fetch ChEMBL API status/metadata endpoint."""
        url = self.request_builder.build_for_endpoint("status").build_request({})
        data = self._execute_request(url)
        return data

    def close(self) -> None:
        """Close underlying HTTP client if present."""
        if self.client is not None:
            self.client.close()

    def fetch(self, entity: str, **filters: Any) -> Any:
        """Request specific entity endpoint with provided filters."""
        endpoint = self._resolve_endpoint(entity)
        url = self._build_request_url(endpoint, filters)
        return self._execute_request(url)

    def _execute_request(self, url: str) -> dict[str, Any]:
        with wrap_http_errors(
            provider=self.provider, endpoint=url, logger=self.logger
        ) as context:
            start = time.monotonic()
            response = self.http.request("GET", url)
            latency = time.monotonic() - start
            raw_status = getattr(response, "status_code", None)
            status_code = raw_status if isinstance(raw_status, int) else None
            context["status_code"] = status_code
            log_level = (
                self.logger.error
                if status_code is not None and status_code >= 400
                else self.logger.info
            )
            log_level(
                "http_request_completed",
                provider=self.provider,
                method="GET",
                url=url,
                status_code=status_code,
                latency_sec=latency,
            )
            if status_code is not None and status_code >= 400:
                self.logger.error(
                    "api_unexpected_status",
                    provider=self.provider,
                    url=url,
                    status_code=status_code,
                )
                raise ApiUnexpectedStatusError(
                    f"Unexpected status code: {status_code}",
                    provider=self.provider,
                    endpoint=url,
                    status_code=status_code,
                )
            return response.json()

    def _build_request_url(self, endpoint: str, filters: dict[str, Any]) -> str:
        """
        Build request URL using both fluent aliases to satisfy test expectations
        and real builder behaviour.
        """
        builder = self.request_builder
        self._apply_endpoint_aliases(builder, endpoint)

        candidates = [
            self._invoke_builder_method(builder, "build_request", filters),
            self._invoke_builder_method(builder, "build", filters),
        ]

        string_candidate = next(
            (candidate for candidate in candidates if isinstance(candidate, str)),
            None,
        )
        if string_candidate is not None:
            return string_candidate

        for candidate in candidates:
            if candidate is not None:
                return str(candidate)

        raise RuntimeError(f"Unable to build request URL for endpoint '{endpoint}'")

    def _apply_endpoint_aliases(self, builder: Any, endpoint: str) -> None:
        if hasattr(builder, "build_for_endpoint"):
            builder.build_for_endpoint(endpoint)
        if hasattr(builder, "for_endpoint"):
            builder.for_endpoint(endpoint)

    def _invoke_builder_method(
        self, builder: Any, method: str, filters: dict[str, Any]
    ) -> str | Any | None:
        if not hasattr(builder, method):
            return None

        callable_method = getattr(builder, method)
        try:
            return callable_method(filters)
        except TypeError:
            return callable_method(**filters)

    def _resolve_endpoint(self, entity: str) -> str:
        aliases = {
            "activity": "activity",
            "assay": "assay",
            "target": "target",
            "publication": "document",
            "molecule": "molecule",
        }
        if entity not in aliases:
            raise ValueError(f"Unknown entity: {entity}")
        return aliases[entity]
