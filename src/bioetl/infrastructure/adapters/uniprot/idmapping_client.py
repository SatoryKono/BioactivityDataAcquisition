"""UniProt ID Mapping API client.

Implements asynchronous ID mapping using UniProt REST API.
Documentation: https://www.uniprot.org/help/id_mapping

API Flow:
1. POST /idmapping/run → returns jobId
2. GET /idmapping/status/{jobId} → poll until complete
3. GET /idmapping/results/{jobId} → retrieve results

Rate Limits:
- Max 100,000 IDs per job
- Job results stored for 7 days
- Polling interval: 3 seconds (minimum)
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator, Mapping
from typing import TYPE_CHECKING, Any

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class IDMappingJobError(Exception):
    """Raised when ID Mapping job fails."""

    def __init__(self, job_id: str, message: str) -> None:
        """Initialize error with job context.

        Args:
            job_id: UniProt job ID that failed.
            message: Error description.
        """
        super().__init__(f"ID Mapping job {job_id} failed: {message}")
        self.job_id = job_id


class IDMappingTimeoutError(Exception):
    """Raised when ID Mapping job polling times out."""

    def __init__(self, job_id: str, attempts: int) -> None:
        """Initialize timeout error.

        Args:
            job_id: UniProt job ID that timed out.
            attempts: Number of polling attempts made.
        """
        super().__init__(
            f"ID Mapping job {job_id} timed out after {attempts} polling attempts"
        )
        self.job_id = job_id
        self.attempts = attempts


class UniProtIDMappingClient(BaseHttpAdapter):
    """UniProt ID Mapping API client.

    Supports mapping between ChEMBL and UniProtKB identifiers using
    UniProt's job-based ID Mapping REST API.

    Example:
        >>> client = UniProtIDMappingClient(http_client, logger)
        >>> results = await client.map_ids("ChEMBL", "UniProtKB", ["CHEMBL204"])
        >>> results
        {"CHEMBL204": "P00742"}
    """

    provider_name: str = "uniprot_idmapping"

    # UniProt ID Mapping constants
    BASE_URL = "https://rest.uniprot.org"
    POLLING_INTERVAL = 3.0  # seconds
    MAX_POLL_ATTEMPTS = 100  # ~5 minutes max wait
    MAX_IDS_PER_BATCH = 500  # Conservative batch size

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
        base_url: str = BASE_URL,
    ) -> None:
        """Initialize UniProt ID Mapping client.

        Args:
            http_client: Injected UnifiedHTTPClient for HTTP requests.
            logger: LoggerPort instance for structured logging.
            metrics: MetricsPort instance for recording SLA metrics.
            base_url: UniProt REST API base URL.
        """
        super().__init__(http_client, logger)
        self.base_url = base_url.rstrip("/")
        metrics_port = metrics if metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)

    async def map_ids(
        self,
        from_db: str,
        to_db: str,
        ids: list[str],
    ) -> Mapping[str, str | None]:
        """Map identifiers using UniProt ID Mapping API.

        Args:
            from_db: Source database (e.g., "ChEMBL")
            to_db: Target database (e.g., "UniProtKB")
            ids: List of source identifiers

        Returns:
            Dict mapping source IDs to target IDs (None if not found)

        Raises:
            IDMappingJobError: If the mapping job fails.
            IDMappingTimeoutError: If polling times out.
        """
        if not ids:
            return {}

        results: dict[str, str | None] = dict.fromkeys(ids, None)

        # Process in batches
        for batch_start in range(0, len(ids), self.MAX_IDS_PER_BATCH):
            batch = ids[batch_start : batch_start + self.MAX_IDS_PER_BATCH]
            batch_results = await self._map_batch(from_db, to_db, batch)
            results.update(batch_results)

        return results

    async def _map_batch(
        self,
        from_db: str,
        to_db: str,
        ids: list[str],
    ) -> dict[str, str | None]:
        """Map a batch of IDs.

        Args:
            from_db: Source database.
            to_db: Target database.
            ids: Batch of source identifiers.

        Returns:
            Dict mapping source IDs to target IDs.
        """
        # Step 1: Submit job
        job_id = await self._submit_job(from_db, to_db, ids)

        # Step 2: Poll for completion
        await self._poll_until_ready(job_id)

        # Step 3: Retrieve results
        return await self._fetch_results(job_id, ids)

    async def _submit_job(
        self,
        from_db: str,
        to_db: str,
        ids: list[str],
    ) -> str:
        """Submit ID mapping job to UniProt.

        POST /idmapping/run
        Body: from={from_db}&to={to_db}&ids={comma_separated_ids}
        Response: {"jobId": "..."}

        Args:
            from_db: Source database.
            to_db: Target database.
            ids: List of identifiers to map.

        Returns:
            Job ID for polling status.

        Raises:
            IDMappingJobError: If job submission fails.
        """
        url = f"{self.base_url}/idmapping/run"
        data = {
            "from": from_db,
            "to": to_db,
            "ids": ",".join(ids),
        }

        self.logger.info(
            "submitting_idmapping_job",
            from_db=from_db,
            to_db=to_db,
            id_count=len(ids),
        )

        with self._adapter_metrics.measure_request("/idmapping/run"):
            response = await self.http_client.post(url, data=data)

        if response.status_code != 200:
            raise IDMappingJobError(
                job_id="unknown",
                message=f"Job submission failed with status {response.status_code}",
            )

        result = response.json()
        job_id = result.get("jobId")

        if not job_id:
            raise IDMappingJobError(
                job_id="unknown",
                message="No jobId in response",
            )

        self.logger.debug("idmapping_job_submitted", job_id=job_id)
        return str(job_id)

    async def _poll_until_ready(self, job_id: str) -> None:
        """Poll job status until complete.

        GET /idmapping/status/{jobId}
        Response: {"jobStatus": "RUNNING|FINISHED|ERROR", ...}

        Args:
            job_id: Job ID to poll.

        Raises:
            IDMappingJobError: If the job fails.
            IDMappingTimeoutError: If polling times out.
        """
        url = f"{self.base_url}/idmapping/status/{job_id}"

        for attempt in range(self.MAX_POLL_ATTEMPTS):
            with self._adapter_metrics.measure_request("/idmapping/status"):
                response = await self.http_client.get(url)

            # UniProt returns 200 for running jobs, 303 redirect when finished
            if response.status_code not in (200, 303):
                self.logger.warning(
                    "idmapping_status_error",
                    job_id=job_id,
                    status_code=response.status_code,
                )
                await asyncio.sleep(self.POLLING_INTERVAL)
                continue

            result = response.json()
            status = result.get("jobStatus", "UNKNOWN")

            # 303 redirect indicates job is finished (redirect to results)
            if response.status_code == 303:
                status = "FINISHED"

            if status == "FINISHED":
                self.logger.debug(
                    "idmapping_job_finished",
                    job_id=job_id,
                    attempts=attempt + 1,
                )
                return

            if status == "ERROR":
                error_msg = result.get("errorMessage", "Unknown error")
                self.logger.error(
                    "idmapping_job_error",
                    job_id=job_id,
                    error=error_msg,
                )
                raise IDMappingJobError(job_id=job_id, message=error_msg)

            # RUNNING or other status - continue polling
            await asyncio.sleep(self.POLLING_INTERVAL)

        raise IDMappingTimeoutError(job_id=job_id, attempts=self.MAX_POLL_ATTEMPTS)

    async def _fetch_results(
        self,
        job_id: str,
        original_ids: list[str],
    ) -> dict[str, str | None]:
        """Fetch mapping results.

        GET /idmapping/results/{jobId}
        Response: {"results": [{"from": "CHEMBL204", "to": "P00742"}, ...]}

        Note: Results may be paginated. Handle Link header for pagination.

        Args:
            job_id: Job ID to fetch results for.
            original_ids: Original list of IDs for initializing results dict.

        Returns:
            Dict mapping source IDs to target IDs (None if not found).
        """
        results: dict[str, str | None] = dict.fromkeys(original_ids, None)
        url: str | None = f"{self.base_url}/idmapping/results/{job_id}"

        while url:
            with self._adapter_metrics.measure_request("/idmapping/results"):
                response = await self.http_client.get(url)

            if response.status_code != 200:
                self.logger.warning(
                    "idmapping_results_error",
                    job_id=job_id,
                    status_code=response.status_code,
                )
                break

            data = response.json()

            # Process results
            for mapping in data.get("results", []):
                from_id, to_id = self._parse_mapping_entry(mapping)
                if from_id in results and to_id:
                    results[from_id] = to_id

            # Check for pagination (Link header)
            url = self._get_next_page_url(response.headers)

        found_count = sum(1 for v in results.values() if v is not None)
        self.logger.info(
            "idmapping_results_fetched",
            job_id=job_id,
            total=len(original_ids),
            found=found_count,
            not_found=len(original_ids) - found_count,
        )

        return results

    @staticmethod
    def _get_next_page_url(headers: Mapping[str, Any]) -> str | None:
        """Extract next page URL from Link header.

        Args:
            headers: Response headers (dict or httpx.Headers).

        Returns:
            Next page URL if present, None otherwise.
        """
        link_header = headers.get("Link", headers.get("link", ""))
        if not link_header:
            return None

        match = re.search(r'<([^>]+)>;\s*rel="next"', str(link_header))
        return match.group(1) if match else None

    @staticmethod
    def _parse_mapping_entry(mapping: dict[str, Any]) -> tuple[str | None, str | None]:
        """Parse a single mapping entry from API response.

        Handles both direct string mappings and entry-based responses
        where UniProtKB returns full entry objects with primaryAccession.

        Args:
            mapping: Single mapping entry from results array.

        Returns:
            Tuple of (from_id, to_id), either may be None if not found.
        """
        from_id = mapping.get("from")
        to_entry = mapping.get("to", {})

        # Handle both direct mapping and entry-based response
        if isinstance(to_entry, str):
            return from_id, to_entry

        if isinstance(to_entry, dict):
            # UniProtKB returns full entry with primaryAccession
            accession = to_entry.get("primaryAccession")
            return from_id, str(accession) if accession else None

        return from_id, None

    async def _probe_health(self) -> HealthStatus:
        """Perform health probe for ID Mapping API.

        Probes /configure/idmapping/fields as a lightweight endpoint.

        Returns:
            HealthStatus based on probe response.
        """
        try:
            url = f"{self.base_url}/configure/idmapping/fields"
            with self._adapter_metrics.measure_request("/health"):
                response = await self.http_client.get_once(url, params=None)

            if response.status_code != 200:
                self.logger.warning(
                    "health_check_degraded",
                    provider=self.provider_name,
                    reason="non_200_response",
                    status_code=response.status_code,
                )
                return HealthStatus.DEGRADED

            return HealthStatus.HEALTHY
        except Exception as e:
            error_type = self._error_handler.get_error_type(e)
            self.logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error_type=error_type.value,
                error=str(e),
            )
            raise

    def _get_health_endpoint(self) -> str:
        """Get health check endpoint for ID Mapping API.

        Returns:
            Health check endpoint path.
        """
        return "/configure/idmapping/fields"

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Not implemented - use IDMappingDataSource instead.

        This client is designed to be used via IDMappingDataSource,
        not directly as a DataSourcePort. Use map_ids() for direct
        ID mapping operations.

        Raises:
            NotImplementedError: Always, as this is not a data source.
        """
        raise NotImplementedError(
            "UniProtIDMappingClient is not a DataSourcePort. "
            "Use IDMappingDataSource for pipeline integration, "
            "or call map_ids() directly for ID mapping operations."
        )
        yield  # pragma: no cover  # Make this an async generator

    def __repr__(self) -> str:
        """Return string representation."""
        return f"UniProtIDMappingClient(base_url='{self.base_url}')"
