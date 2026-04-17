"""UniProt ID Mapping API client.

Implements asynchronous ID mapping using UniProt REST API.
Documentation: https://www.uniprot.org/help/id_mapping

API Flow:
1. POST /idmapping/run -> returns jobId
2. GET /idmapping/status/{jobId} -> poll until complete
3. GET /idmapping/results/{jobId} -> retrieve results
"""

from __future__ import annotations

__all__ = ["IDMappingJobError", "IDMappingTimeoutError", "UniProtIDMappingClient"]

from collections.abc import AsyncIterator, Mapping
from typing import TYPE_CHECKING

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.uniprot._idmapping_errors import (
    IDMappingJobError,
    IDMappingTimeoutError,
)
from bioetl.infrastructure.adapters.uniprot._idmapping_health import (
    IDMappingHealthMixin,
)
from bioetl.infrastructure.adapters.uniprot._idmapping_parser import (
    IDMappingParserMixin,
)
from bioetl.infrastructure.adapters.uniprot._idmapping_retry import IDMappingRetryMixin
from bioetl.infrastructure.adapters.uniprot._idmapping_transport import (
    IDMappingTransportMixin,
)
from bioetl.infrastructure.adapters.uniprot.constants import UNIPROT_API_BASE

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class UniProtIDMappingClient(
    IDMappingHealthMixin,
    IDMappingTransportMixin,
    IDMappingRetryMixin,
    IDMappingParserMixin,
    BaseHttpAdapter,
):
    """UniProt ID Mapping API client."""

    provider_name: str = "uniprot_idmapping"
    BASE_URL = UNIPROT_API_BASE
    POLLING_INTERVAL = 3.0
    MAX_POLL_ATTEMPTS = 100
    MAX_IDS_PER_BATCH = 500

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
        base_url: str = BASE_URL,
        *,
        adapter_metrics: AdapterMetricsRecorder | None = None,
    ) -> None:
        super().__init__(
            http_client,
            logger,
            metrics=metrics,
            adapter_metrics=adapter_metrics,
        )
        self.base_url = base_url.rstrip("/")

    async def map_ids(
        self,
        from_db: str,
        to_db: str,
        ids: list[str],
    ) -> Mapping[str, JsonDict | None]:  # Any: untyped API JSON
        """Map identifiers using UniProt ID Mapping API."""
        if not ids:
            return {}

        results: dict[str, JsonDict | None] = dict.fromkeys(ids, None)
        for batch_start in range(0, len(ids), self.MAX_IDS_PER_BATCH):
            batch = ids[batch_start : batch_start + self.MAX_IDS_PER_BATCH]
            batch_results = await self._map_batch(from_db, to_db, batch)
            results.update(batch_results)
        return results

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON
        """Not implemented - use IDMappingDataSource instead."""
        raise NotImplementedError(
            "UniProtIDMappingClient is not a DataSourcePort. "
            "Use IDMappingDataSource for pipeline integration, "
            "or call map_ids() directly for ID mapping operations."
        )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"UniProtIDMappingClient(base_url='{self.base_url}')"
