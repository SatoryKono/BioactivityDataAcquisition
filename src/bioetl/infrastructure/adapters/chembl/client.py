"""ChEMBL data source adapter.

Implements DataSourcePort for ChEMBL database.
See RULES.md Appendix A for rate limits and retry strategy.

Uses chembl_webresource_client library for API access.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bioetl.domain.types import HealthStatus, Watermark
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker

# ChEMBL API base URL
CHEMBL_API_BASE = "https://www.ebi.ac.uk/chembl/api/data"
CHEMBL_STATUS_URL = f"{CHEMBL_API_BASE}/status.json"

# Entity type to ChEMBL resource mapping
ENTITY_MAPPING = {
    "activity": "activity",
    "assay": "assay",
    "compound": "molecule",
    "target": "target",
    "document": "document",
    "cell_line": "cell_line",
    "tissue": "tissue",
}


class ChemblApiError(Exception):
    """Raised when ChEMBL API returns an error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class ChemblAdapter:
    """ChEMBL data source adapter.

    Implements DataSourcePort for fetching data from ChEMBL database.

    Args:
        http_client: UnifiedHTTPClient instance
        batch_size: Number of records per API request (default: 1000)
        thread_pool: ThreadPoolExecutor for sync operations

    Example:
        >>> bucket = TokenBucket(rate=10.0, capacity=10)
        >>> cb = CircuitBreaker(provider="chembl")
        >>> async with UnifiedHTTPClient(bucket, cb) as http:
        ...     adapter = ChemblAdapter(http_client=http)
        ...     async for record in adapter.fetch("activity", limit=100):
        ...         process(record)
    """

    http_client: UnifiedHTTPClient
    batch_size: int = 1000
    thread_pool: ThreadPoolExecutor | None = None

    _consecutive_errors: int = field(init=False, default=0)
    _last_health_check: datetime | None = field(init=False, default=None)
    _cached_health: HealthStatus = field(init=False, default=HealthStatus.HEALTHY)

    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "chembl"

    def _get_resource_url(self, entity_type: str) -> str:
        """Get ChEMBL API URL for entity type."""
        resource = ENTITY_MAPPING.get(entity_type)
        if resource is None:
            msg = f"Unknown entity type: {entity_type}"
            raise ValueError(msg)
        return f"{CHEMBL_API_BASE}/{resource}.json"

    async def fetch(
        self,
        entity_type: str,
        watermark: Watermark | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from ChEMBL.

        Args:
            entity_type: Type of entity (activity, compound, target, etc)
            watermark: Last checkpoint for incremental load
            limit: Maximum number of records

        Yields:
            Raw records as dictionaries

        Raises:
            ChemblApiError: On API errors
            ValueError: On unknown entity type
        """
        url = self._get_resource_url(entity_type)
        offset = 0
        total_fetched = 0

        while True:
            params: dict[str, Any] = {
                "limit": self.batch_size,
                "offset": offset,
                "format": "json",
            }

            # Apply watermark filter if provided
            if watermark is not None:
                # ChEMBL uses different filter fields per entity
                if entity_type == "activity":
                    # Filter by document_chembl_id or assay modification date
                    if isinstance(watermark, datetime):
                        params["updated_on__gte"] = watermark.isoformat()
                    else:
                        # Assume it's an ID-based watermark
                        params["activity_id__gt"] = str(watermark)

            try:
                response = await self.http_client.get(url, params=params)
                data = response.json()

                # ChEMBL returns data in a wrapper with pagination info
                records = data.get(ENTITY_MAPPING.get(entity_type, entity_type) + "s", [])
                page_meta = data.get("page_meta", {})

                if not records:
                    break

                for record in records:
                    yield record
                    total_fetched += 1

                    if limit and total_fetched >= limit:
                        return

                # Reset error counter on success
                self._consecutive_errors = 0

                # Check if there are more pages
                if not page_meta.get("next"):
                    break

                offset += self.batch_size

            except Exception as e:
                self._consecutive_errors += 1
                self._update_health()
                raise ChemblApiError(str(e)) from e

    def fetch_sync(
        self,
        entity_type: str,
        watermark: Watermark | None = None,
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Synchronous version of fetch (for compatibility with DataSourcePort).

        This wraps the async fetch method using asyncio.run().
        For better performance, use the async version directly.
        """

        async def _fetch_all() -> list[dict[str, Any]]:
            results = []
            async for record in self.fetch(entity_type, watermark, limit):
                results.append(record)
            return results

        # Run in event loop
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(_fetch_all())
            yield from results
        finally:
            loop.close()

    async def health_check(self) -> HealthStatus:
        """Check ChEMBL API health status.

        Returns:
            HEALTHY: API is operational
            DEGRADED: API responding slowly or with some errors
            UNHEALTHY: API is down
        """
        try:
            response = await self.http_client.get(CHEMBL_STATUS_URL)

            if response.status_code == 200:
                data = response.json()
                # ChEMBL status endpoint returns service info
                if data.get("status") == "UP":
                    self._consecutive_errors = 0
                    self._cached_health = HealthStatus.HEALTHY
                else:
                    self._cached_health = HealthStatus.DEGRADED
            else:
                self._consecutive_errors += 1
                self._update_health()

        except Exception:
            self._consecutive_errors += 1
            self._update_health()

        self._last_health_check = datetime.now()
        return self._cached_health

    def _update_health(self) -> None:
        """Update health status based on error count."""
        if self._consecutive_errors >= 3:
            self._cached_health = HealthStatus.UNHEALTHY
        elif self._consecutive_errors >= 1:
            self._cached_health = HealthStatus.DEGRADED
        else:
            self._cached_health = HealthStatus.HEALTHY

    async def get_entity_count(self, entity_type: str) -> int:
        """Get total count of entities (for progress tracking).

        Args:
            entity_type: Type of entity

        Returns:
            Total count of entities
        """
        url = self._get_resource_url(entity_type)
        params = {"limit": 1, "format": "json"}

        response = await self.http_client.get(url, params=params)
        data = response.json()

        page_meta = data.get("page_meta", {})
        return page_meta.get("total_count", 0)


def create_chembl_adapter(
    circuit_breaker: CircuitBreaker,
    run_id: Any = None,
) -> tuple[ChemblAdapter, UnifiedHTTPClient]:
    """Factory function to create ChemblAdapter with dependencies.

    Args:
        circuit_breaker: CircuitBreaker instance for fault tolerance
        run_id: Optional run ID for correlation

    Returns:
        Tuple of (ChemblAdapter, UnifiedHTTPClient)
        Note: Caller is responsible for entering http_client context.
    """
    # ChEMBL has no explicit rate limit, use conservative default
    rate_limiter = TokenBucket(rate=10.0, capacity=20)

    http_client = UnifiedHTTPClient(
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        run_id=run_id,
    )

    adapter = ChemblAdapter(http_client=http_client)

    return adapter, http_client