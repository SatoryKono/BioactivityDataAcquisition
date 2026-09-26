"""Template for a new provider adapter.

Location: src/bioetl/infrastructure/adapters/<provider>/client.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.base import BaseHttpAdapter

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@dataclass
class {{Provider}}Adapter(BaseHttpAdapter):
    """Data source adapter for {{Provider}} API."""

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    metrics: MetricsPort | None = None
    base_url: str = "{{provider_api_base}}"
    provider_name: str = field(init=False, default="{{provider}}")
    entity_endpoints: dict[str, str] = field(default_factory=dict)
    page_size: int = 100
    max_page_size: int = 1000

    def __post_init__(self) -> None:
        self._init_adapter_metrics()

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from provider API (async generator)."""
        endpoint = self._resolve_endpoint(entity_type)
        page_size = self._resolve_page_size(limit)
        request_offset = 0 if offset is None else max(0, offset)
        yielded = 0
        while True:
            request = self._build_request_params(
                query=query,
                filter_ids=filter_ids,
                filter_field=filter_field,
                request_offset=request_offset,
                page_size=page_size,
            )
            response = await self.http_client.get(
                f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}",
                params=request,
            )
            response.raise_for_status()

            response_data = response.json()
            records = self._extract_records(response_data, entity_type=entity_type)
            if not records:
                return

            for record in records:
                if limit is not None and yielded >= limit:
                    return
                yield self._normalize_record(record)
                yielded += 1

            request_offset += len(records)
            if limit is not None and yielded >= limit:
                return
            if len(records) < page_size:
                return

    def _resolve_endpoint(self, entity_type: str) -> str:
        """Map entity type to relative API endpoint."""
        endpoint = self.entity_endpoints.get(entity_type)
        if endpoint is None:
            supported = ", ".join(sorted(self.entity_endpoints))
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Supported entity types: {supported}"
            )
        return endpoint

    def _resolve_page_size(self, limit: int | None) -> int:
        """Resolve per-request page size within configured bounds."""
        if limit is None:
            return self.page_size
        return min(limit, self.max_page_size, max(1, self.page_size))

    def _build_request_params(
        self,
        *,
        query: str | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
        request_offset: int,
        page_size: int,
    ) -> dict[str, str | int | list[str]]:
        """Build common request parameters for paging and filtering."""
        params: dict[str, str | int | list[str]] = {
            "limit": page_size,
            "offset": request_offset,
        }
        if query is not None:
            params["q"] = query
        if filter_ids:
            if not filter_field:
                raise ValueError("filter_field is required when filter_ids is provided")
            params["filter_field"] = filter_field
            params["filter_value"] = filter_ids
        return params

    @staticmethod
    def _extract_records(
        payload: dict[str, Any] | list[Any],
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract record list from common payload shapes.

        Providers with custom response schemas should override this method.
        """
        del entity_type
        if isinstance(payload, list):
            return [record for record in payload if isinstance(record, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("results", "items", "records", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [record for record in value if isinstance(record, dict)]
        return []

    @staticmethod
    def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
        """Normalize raw API records before yielding.

        Override this method to apply provider-specific field mapping.
        """
        return record
