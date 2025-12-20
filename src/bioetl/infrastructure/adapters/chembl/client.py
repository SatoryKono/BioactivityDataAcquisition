"""ChEMBL data source adapter.

Implements DataSourcePort for ChEMBL database.
See RULES.md Appendix A for rate limits and retry strategy.

Uses chembl_webresource_client library for API access.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bioetl.domain.exceptions import ChemblApiError
from bioetl.domain.types import HealthStatus, Watermark
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from concurrent.futures import ThreadPoolExecutor

    from httpx import Response


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

# Plural forms for API response keys (ChEMBL uses irregular plurals)
ENTITY_PLURAL = {
    "activity": "activities",
    "assay": "assays",
    "molecule": "molecules",
    "target": "targets",
    "document": "documents",
    "cell_line": "cell_lines",
    "tissue": "tissues",
}


@dataclass
class ChemblAdapter(BaseHttpAdapter):
    """ChEMBL data source adapter.

    Implements DataSourcePort for fetching data from ChEMBL database.

    Args:
        http_client: UnifiedHTTPClient instance
        batch_size: Number of records per API request (default: 1000)
        thread_pool: ThreadPoolExecutor for sync operations
    """

    http_client: UnifiedHTTPClient
    batch_size: int = 1000
    thread_pool: ThreadPoolExecutor | None = None

    provider_name: str = field(init=False, default="chembl")
    """Provider identifier (required by DataSourcePort)."""

    _consecutive_errors: int = field(init=False, default=0)
    _last_health_check: datetime | None = field(init=False, default=None)
    _cached_health: HealthStatus = field(init=False, default=HealthStatus.HEALTHY)

    def _get_resource_url(self, entity_type: str) -> str:
        """Get ChEMBL API URL for entity type."""
        resource = ENTITY_MAPPING.get(entity_type)
        if resource is None:
            msg = f"Unknown entity type: {entity_type}"
            raise ValueError(msg)
        return f"{CHEMBL_API_BASE}/{resource}.json"

    def _build_params(
        self, entity_type: str, watermark: Watermark | None, offset: int
    ) -> dict[str, Any]:
        """Build API request parameters."""
        params: dict[str, Any] = {
            "limit": self.batch_size,
            "offset": offset,
            "format": "json",
        }
        if watermark is not None and entity_type == "activity":
            if isinstance(watermark.value, datetime):
                params["updated_on__gte"] = watermark.value.isoformat()
            else:
                params["activity_id__gt"] = str(watermark.value)
        return params

    def _process_response(
        self, response: Response, entity_type: str
    ) -> tuple[list[dict[str, Any]], bool]:
        """Process API response, extract records and pagination info."""
        data = response.json()
        resource = ENTITY_MAPPING.get(entity_type, entity_type)
        plural_key = ENTITY_PLURAL.get(resource, resource + "s")
        records = data.get(plural_key, [])
        page_meta = data.get("page_meta", {})
        has_next = page_meta.get("next") is not None
        return records, has_next

    def _batch_ids(self, ids: set[str], batch_size: int) -> Iterator[list[str]]:
        """Split IDs into batches for API requests."""
        id_list = list(ids)
        for i in range(0, len(id_list), batch_size):
            yield id_list[i : i + batch_size]

    async def _fetch_page(
        self, url: str, params: dict[str, Any], entity_type: str
    ) -> tuple[list[dict[str, Any]], bool]:
        """Fetch a single page and handle errors."""
        try:
            response = await self.http_client.get(url, params=params)
            records, has_next = self._process_response(response, entity_type)
            self._consecutive_errors = 0
            return records, has_next
        except Exception as e:
            self._handle_error(e)
            return [], False

    async def _page_iterator(
        self, entity_type: str, watermark: Watermark | None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Yield pages of records."""
        url = self._get_resource_url(entity_type)
        offset = 0
        while True:
            params = self._build_params(entity_type, watermark, offset)
            records, has_next = await self._fetch_page(url, params, entity_type)
            if not records:
                break
            yield records
            if not has_next:
                break
            offset += self.batch_size

    async def _fetch_with_filter(
        self,
        entity_type: str,
        watermark: Watermark | None,
        limit: int | None,
        id_batch: list[str],
        filter_field: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records filtered by ID batch."""
        url = self._get_resource_url(entity_type)
        offset = 0

        while True:
            params = self._build_params(entity_type, watermark, offset)
            params[f"{filter_field}__in"] = ",".join(id_batch)

            records, has_next = await self._fetch_page(url, params, entity_type)
            if not records:
                break

            for record in records:
                yield record

            if not has_next:
                break
            offset += self.batch_size

    def _handle_error(self, e: Exception) -> None:
        """Handle fetch errors."""
        self._consecutive_errors += 1
        self._update_health()
        raise ChemblApiError(str(e)) from e

    async def _fetch_filtered(
        self,
        entity_type: str,
        watermark: Watermark | None,
        limit: int | None,
        filter_ids: set[str],
        filter_field: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Perform filtered fetch using ID batches."""
        total_fetched = 0
        for id_batch in self._batch_ids(filter_ids, batch_size=100):
            async for record in self._fetch_with_filter(
                entity_type, watermark, limit, id_batch, filter_field
            ):
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

    async def _fetch_standard(
        self,
        entity_type: str,
        watermark: Watermark | None,
        limit: int | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Perform standard paginated fetch."""
        total_fetched = 0
        async for records in self._page_iterator(entity_type, watermark):
            for record in records:
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

    async def fetch(
        self,
        entity_type: str,
        watermark: Watermark | None = None,
        limit: int | None = None,
        query: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from ChEMBL.

        Implements DataSourcePort.fetch() interface.

        Args:
            entity_type: Type of entity to fetch (activity, assay, compound, etc.)
            watermark: Resume point for incremental fetching
            limit: Maximum number of records to fetch
            query: Unused for ChEMBL (filtering done via fetch_filtered method)

        Yields:
            Dictionary records from ChEMBL API
        """
        async for record in self._fetch_standard(entity_type, watermark, limit):
            yield record

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: set[str],
        filter_field: str,
        watermark: Watermark | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from ChEMBL with ID filtering.

        This is a ChEMBL-specific extension not part of DataSourcePort.

        Args:
            entity_type: Type of entity to fetch
            filter_ids: Set of IDs to filter by
            filter_field: Field name to filter on
            watermark: Resume point for incremental fetching
            limit: Maximum number of records to fetch

        Yields:
            Dictionary records matching the filter criteria
        """
        async for record in self._fetch_filtered(
            entity_type, watermark, limit, filter_ids, filter_field
        ):
            yield record

    async def health_check(self) -> HealthStatus:
        """Check ChEMBL API health status."""
        try:
            response = await self.http_client.get(CHEMBL_STATUS_URL)
            self._handle_health_response(response)
        except Exception:
            self._consecutive_errors += 1
            self._update_health()

        self._last_health_check = datetime.now()
        return self._cached_health

    def _handle_health_response(self, response: Response) -> None:
        """Process health check response."""
        if response.status_code == 200:
            # Reset error counter on any successful HTTP response
            self._consecutive_errors = 0
            data = response.json()
            if data.get("status") == "UP":
                self._cached_health = HealthStatus.HEALTHY
            else:
                self._cached_health = HealthStatus.DEGRADED
        else:
            self._consecutive_errors += 1
            self._update_health()

    def _update_health(self) -> None:
        """Update health status based on error count."""
        if self._consecutive_errors >= 3:
            self._cached_health = HealthStatus.UNHEALTHY
        elif self._consecutive_errors >= 1:
            self._cached_health = HealthStatus.DEGRADED
        else:
            self._cached_health = HealthStatus.HEALTHY

    async def get_entity_count(self, entity_type: str) -> int:
        """Get total count of entities."""
        url = self._get_resource_url(entity_type)
        params = {"limit": 1, "format": "json"}
        response = await self.http_client.get(url, params=params)
        data = response.json()
        page_meta = data.get("page_meta", {})
        return page_meta.get("total_count", 0)


