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
    provider_name: str = field(init=False, default="{{provider}}")

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
        # TODO: implement provider endpoint routing + pagination + filtering.
        # Use self.http_client.request/get and yield normalized raw records.
        if False:
            yield {}
