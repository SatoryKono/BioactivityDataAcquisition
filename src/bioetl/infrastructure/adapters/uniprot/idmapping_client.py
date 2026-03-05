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

__all__ = ["IDMappingJobError", "IDMappingTimeoutError", "UniProtIDMappingClient"]


import asyncio
import json
import re
from collections.abc import AsyncIterator, Mapping
from typing import TYPE_CHECKING

from bioetl.domain.ports import NoOpMetrics
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.uniprot.constants import UNIPROT_API_BASE

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
    UniProt's job-based ID Mapping REST API. Extracts comprehensive
    entry metadata when mapping to UniProtKB.

    Example:
        >>> client = UniProtIDMappingClient(http_client, logger)
        >>> results = await client.map_ids("ChEMBL", "UniProtKB", ["CHEMBL204"])
        >>> results["CHEMBL204"]
        {"uniprot_accession": "P00742", "uniprot_entry_name": "FA10_HUMAN", ...}
    """

    provider_name: str = "uniprot_idmapping"

    # UniProt ID Mapping constants
    BASE_URL = UNIPROT_API_BASE
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
    ) -> Mapping[str, JsonDict | None]:  # Any: untyped API JSON
        """Map identifiers using UniProt ID Mapping API.

        Args:
            from_db: Source database (e.g., "ChEMBL")
            to_db: Target database (e.g., "UniProtKB")
            ids: List of source identifiers

        Returns:
            Dict mapping source IDs to entry data dicts (None if not found).
            Each entry dict contains: uniprot_accession, uniprot_entry_name,
            organism_scientific, organism_common, taxonomy_id, protein_name,
            gene_primary, sequence_length, sequence_mass, reviewed, annotation_score,
            and optionally all_mappings (JSON) if multiple mappings found.

        Raises:
            IDMappingJobError: If the mapping job fails.
            IDMappingTimeoutError: If polling times out.
        """
        if not ids:
            return {}

        results: dict[str, JsonDict | None] = dict.fromkeys(ids, None)  # Any: API

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
    ) -> dict[str, JsonDict | None]:  # Any: untyped API JSON
        """Map a batch of IDs.

        Args:
            from_db: Source database.
            to_db: Target database.
            ids: Batch of source identifiers.

        Returns:
            Dict mapping source IDs to entry data dicts.
        """
        # Step 1: Submit job
        job_id = await self._submit_job(from_db, to_db, ids)

        # Step 2: Poll for completion (returns redirect URL if detected)
        results_url = await self._poll_until_ready(job_id)

        # Step 3: Retrieve results using redirect URL or default
        return await self._fetch_results(job_id, ids, results_url=results_url)

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

    async def _poll_until_ready(self, job_id: str) -> str | None:
        """Poll job status until complete.

        GET /idmapping/status/{jobId}
        Response: {"jobStatus": "RUNNING|FINISHED|ERROR", ...}

        Note: When job is finished, UniProt returns 303 redirect to results.
        httpx follows redirects automatically, so we detect completion by:
        1. Checking if response URL contains '/results/' (redirect was followed)
        2. Checking if response has 'results' key (we got results directly)
        3. Checking jobStatus field for running/error states

        Args:
            job_id: Job ID to poll.

        Returns:
            Results URL captured from redirect (e.g.
            ``/idmapping/uniprotkb/results/{jobId}``), or None if the URL
            was not detected via redirect.

        Raises:
            IDMappingJobError: If the job fails.
            IDMappingTimeoutError: If polling times out.
        """
        url = f"{self.base_url}/idmapping/status/{job_id}"

        for attempt in range(self.MAX_POLL_ATTEMPTS):
            with self._adapter_metrics.measure_request("/idmapping/status"):
                response = await self.http_client.get(url)

            # Check if httpx followed redirect to results URL
            # This happens when job is finished (303 → results)
            response_url = str(response.url) if hasattr(response, "url") else ""
            if "/results/" in response_url or "/uniprotkb/results/" in response_url:
                self.logger.debug(
                    "idmapping_job_finished",
                    job_id=job_id,
                    attempts=attempt + 1,
                    detected_by="redirect_to_results",
                    results_url=response_url,
                )
                return response_url

            if response.status_code not in (200, 303):
                self.logger.warning(
                    "idmapping_status_error",
                    job_id=job_id,
                    status_code=response.status_code,
                )
                await asyncio.sleep(self.POLLING_INTERVAL)
                continue

            result = response.json()

            # If response contains 'results' key, job is finished
            # (httpx followed redirect and we got results directly)
            if "results" in result:
                self.logger.debug(
                    "idmapping_job_finished",
                    job_id=job_id,
                    attempts=attempt + 1,
                    detected_by="results_in_response",
                )
                return response_url or None

            status = result.get("jobStatus", "UNKNOWN")

            # 303 redirect indicates job is finished (redirect to results)
            if response.status_code == 303:
                status = "FINISHED"

            if status == "FINISHED":
                self.logger.debug(
                    "idmapping_job_finished",
                    job_id=job_id,
                    attempts=attempt + 1,
                    detected_by="job_status",
                )
                return None

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
        results_url: str | None = None,
    ) -> dict[str, JsonDict | None]:  # Any: untyped API JSON
        """Fetch mapping results with full entry metadata.

        GET /idmapping/results/{jobId}
        Response: {"results": [{"from": "CHEMBL204", "to": {...}}, ...]}

        Note: Results may be paginated. Handle Link header for pagination.
        Multiple mappings for same ID are aggregated with primary selection.

        Args:
            job_id: Job ID to fetch results for.
            original_ids: Original list of IDs for initializing results dict.
            results_url: Exact results URL captured from the polling redirect
                (e.g. ``/idmapping/uniprotkb/results/{jobId}``).
                When provided, avoids an extra redirect hop.  Falls back to
                the generic ``/idmapping/results/{jobId}`` when *None*.

        Returns:
            Dict mapping source IDs to entry data dicts (None if not found).
        """
        # Collect all entries per source ID (for multiple mappings)
        entries_by_id: dict[str, list[JsonDict]] = {  # Any: untyped API JSON
            id_: [] for id_ in original_ids
        }
        url: str | None = results_url or f"{self.base_url}/idmapping/results/{job_id}"

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

            # Process results - collect all entries per source ID
            for mapping in data.get("results", []):
                from_id, entry_data = self._parse_mapping_entry(mapping)
                if from_id in entries_by_id and entry_data:
                    entries_by_id[from_id].append(entry_data)

            # Check for pagination (Link header)
            url = self._get_next_page_url(response.headers)

        # Select primary entry for each ID, handle multiple mappings
        results: dict[str, JsonDict | None] = {}  # Any: untyped API JSON
        for id_, entries in entries_by_id.items():
            results[id_] = self._select_primary_entry(entries)

        found_count = sum(1 for v in results.values() if v is not None)
        multiple_count = sum(1 for v in results.values() if v and v.get("all_mappings"))
        self.logger.info(
            "idmapping_results_fetched",
            job_id=job_id,
            total=len(original_ids),
            found=found_count,
            not_found=len(original_ids) - found_count,
            multiple_mappings=multiple_count,
        )

        return results

    @staticmethod
    def _select_primary_entry(
        entries: list[JsonDict],  # Any: untyped API JSON
    ) -> JsonDict | None:  # Any: untyped API JSON
        """Select primary entry from list, handling multiple mappings.

        When multiple mappings exist, selects the best entry based on:
        1. Reviewed status (Swiss-Prot preferred over TrEMBL)
        2. Annotation score (higher is better)

        Args:
            entries: List of entry data dicts for a single source ID.

        Returns:
            Primary entry dict with optional all_mappings field, or None.
        """
        if not entries:
            return None
        if len(entries) == 1:
            return entries[0]

        # Multiple mappings: sort by reviewed (desc), annotation_score (desc)
        sorted_entries = sorted(
            entries,
            key=lambda e: (
                -int(e.get("reviewed") or False),
                -int(e.get("annotation_score") or 0),
            ),
        )
        primary = dict(sorted_entries[0])  # Copy to avoid mutation
        # Store all accessions as JSON array
        all_accessions = [e["uniprot_accession"] for e in sorted_entries]
        primary["all_mappings"] = json.dumps(all_accessions)
        return primary

    @staticmethod
    def _get_next_page_url(headers: Mapping[str, str]) -> str | None:
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
    def _extract_organism_info(
        organism: object,
    ) -> tuple[str | None, str | None, int | None]:
        """Extract organism metadata from entry.

        Args:
            organism: Organism object from UniProt entry.

        Returns:
            Tuple of (scientific_name, common_name, taxonomy_id).
        """
        if not isinstance(organism, dict):
            return None, None, None
        return (
            organism.get("scientificName"),
            organism.get("commonName"),
            organism.get("taxonId"),
        )

    @staticmethod
    def _extract_protein_name(protein_desc: object) -> str | None:
        """Extract recommended protein name from description.

        Args:
            protein_desc: proteinDescription object from UniProt entry.

        Returns:
            Protein full name or None.
        """
        if not isinstance(protein_desc, dict):
            return None
        recommended = protein_desc.get("recommendedName", {})
        if not isinstance(recommended, dict):
            return None
        full_name = recommended.get("fullName", {})
        if not isinstance(full_name, dict):
            return None
        return full_name.get("value")

    @staticmethod
    def _extract_gene_primary(genes: object) -> str | None:
        """Extract primary gene name from genes list.

        Args:
            genes: Genes array from UniProt entry.

        Returns:
            Primary gene name or None.
        """
        if not isinstance(genes, list) or not genes:
            return None
        first_gene = genes[0]
        if not isinstance(first_gene, dict):
            return None
        gene_name_obj = first_gene.get("geneName", {})
        if not isinstance(gene_name_obj, dict):
            return None
        return gene_name_obj.get("value")

    @staticmethod
    def _extract_sequence_info(
        sequence: object,
    ) -> tuple[int | None, int | None]:
        """Extract sequence length and mass from entry.

        Args:
            sequence: Sequence object from UniProt entry.

        Returns:
            Tuple of (sequence_length, sequence_mass).
        """
        if not isinstance(sequence, dict):
            return None, None
        return sequence.get("length"), sequence.get("molWeight")

    @staticmethod
    def _parse_mapping_entry(
        mapping: JsonDict,  # Any: untyped API JSON
    ) -> tuple[str | None, JsonDict | None]:  # Any: untyped API JSON
        """Parse a single mapping entry from API response.

        Extracts comprehensive entry metadata from UniProtKB responses.
        Handles both direct string mappings and full entry objects.

        Args:
            mapping: Single mapping entry from results array.

        Returns:
            Tuple of (from_id, entry_data_dict), either may be None if not found.
        """
        from_id = mapping.get("from")
        to_entry = mapping.get("to", {})

        # Handle direct string mapping (simple database mapping)
        if isinstance(to_entry, str):
            return from_id, {"uniprot_accession": to_entry}

        if not isinstance(to_entry, dict):
            return from_id, None

        # Extract primary accession (required)
        accession = to_entry.get("primaryAccession")
        if not accession:
            return from_id, None

        # Extract nested fields using helper methods
        org_sci, org_common, tax_id = UniProtIDMappingClient._extract_organism_info(
            to_entry.get("organism")
        )
        protein_name = UniProtIDMappingClient._extract_protein_name(
            to_entry.get("proteinDescription")
        )
        gene_primary = UniProtIDMappingClient._extract_gene_primary(
            to_entry.get("genes")
        )
        seq_len, seq_mass = UniProtIDMappingClient._extract_sequence_info(
            to_entry.get("sequence")
        )

        # Determine reviewed status from entryType
        entry_type = to_entry.get("entryType", "")
        reviewed = "Swiss-Prot" in entry_type if entry_type else None

        return from_id, {
            "uniprot_accession": str(accession),
            "uniprot_entry_name": to_entry.get("uniProtkbId"),
            "organism_scientific": org_sci,
            "organism_common": org_common,
            "taxonomy_id": tax_id,
            "protein_name": protein_name,
            "gene_primary": gene_primary,
            "sequence_length": seq_len,
            "sequence_mass": seq_mass,
            "reviewed": reviewed,
            "annotation_score": to_entry.get("annotationScore"),
        }

    async def _probe_health(self) -> HealthStatus:
        """Perform health probe for ID Mapping API.

        Probes /configure/idmapping/fields as a lightweight endpoint.

        Returns:
            HealthStatus based on probe response.
        """
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
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON
        """Not implemented - use IDMappingDataSource instead.

        This client is designed to be used via IDMappingDataSource,
        not directly as a DataSourcePort. Use map_ids() for direct
        ID mapping operations.

        Raises:
            NotImplementedError: Always, as this is not a data source.

        Args:
            entity_type: Entity type identifier.
            limit: Maximum number of records to process.
            query: Search query string.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            offset: Offset.

        Returns:
            Async iterator yielding fetched records.
        """
        raise NotImplementedError(
            "UniProtIDMappingClient is not a DataSourcePort. "
            "Use IDMappingDataSource for pipeline integration, "
            "or call map_ids() directly for ID mapping operations."
        )
        yield {}  # pragma: no cover - keeps AsyncIterator contract

    def __repr__(self) -> str:
        """Return string representation."""
        return f"UniProtIDMappingClient(base_url='{self.base_url}')"
