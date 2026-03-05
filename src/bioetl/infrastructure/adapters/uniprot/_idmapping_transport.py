"""Transport and result retrieval logic for UniProt ID mapping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.uniprot._idmapping_errors import IDMappingJobError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@runtime_checkable
class IDMappingTransportDependencies(Protocol):
    """Host dependency contract for IDMappingTransportMixin."""

    logger: LoggerPort
    http_client: UnifiedHTTPClient
    _adapter_metrics: AdapterMetrics
    base_url: str

    async def _poll_until_ready(self, job_id: str) -> str | None: ...

    def _parse_mapping_entry(
        self,
        mapping: JsonDict,  # Any: untyped API JSON
    ) -> tuple[str | None, JsonDict | None]: ...

    def _get_next_page_url(self, headers: Mapping[str, str]) -> str | None: ...

    def _select_primary_entry(
        self,
        entries: list[JsonDict],  # Any: untyped API JSON
    ) -> JsonDict | None: ...


class IDMappingTransportMixin:
    """HTTP transport helpers for job submission and result retrieval."""

    logger: LoggerPort
    http_client: UnifiedHTTPClient
    _adapter_metrics: AdapterMetrics
    base_url: str

    def _transport_deps(self) -> IDMappingTransportDependencies:
        """Return typed dependency view of the host client."""
        return cast("IDMappingTransportDependencies", self)

    async def _map_batch(
        self,
        from_db: str,
        to_db: str,
        ids: list[str],
    ) -> dict[str, JsonDict | None]:  # Any: untyped API JSON
        """Map a batch of IDs."""
        deps = self._transport_deps()
        job_id = await self._submit_job(from_db, to_db, ids)
        results_url = await deps._poll_until_ready(job_id)
        return await self._fetch_results(job_id, ids, results_url=results_url)

    async def _submit_job(
        self,
        from_db: str,
        to_db: str,
        ids: list[str],
    ) -> str:
        """Submit ID mapping job to UniProt."""
        deps = self._transport_deps()
        url = f"{deps.base_url}/idmapping/run"
        data = {"from": from_db, "to": to_db, "ids": ",".join(ids)}

        deps.logger.info(
            "submitting_idmapping_job",
            from_db=from_db,
            to_db=to_db,
            id_count=len(ids),
        )
        with deps._adapter_metrics.measure_request("/idmapping/run"):
            response = await deps.http_client.post(url, data=data)

        if response.status_code != 200:
            raise IDMappingJobError(
                job_id="unknown",
                message=f"Job submission failed with status {response.status_code}",
            )

        result = response.json()
        job_id = result.get("jobId")
        if not job_id:
            raise IDMappingJobError(job_id="unknown", message="No jobId in response")

        deps.logger.debug("idmapping_job_submitted", job_id=job_id)
        return str(job_id)

    async def _fetch_results(
        self,
        job_id: str,
        original_ids: list[str],
        results_url: str | None = None,
    ) -> dict[str, JsonDict | None]:  # Any: untyped API JSON
        """Fetch mapping results with full entry metadata."""
        deps = self._transport_deps()
        entries_by_id: dict[str, list[JsonDict]] = {id_: [] for id_ in original_ids}
        url: str | None = results_url or f"{deps.base_url}/idmapping/results/{job_id}"

        while url:
            with deps._adapter_metrics.measure_request("/idmapping/results"):
                response = await deps.http_client.get(url)

            if response.status_code != 200:
                deps.logger.warning(
                    "idmapping_results_error",
                    job_id=job_id,
                    status_code=response.status_code,
                )
                break

            data = response.json()
            for mapping in data.get("results", []):
                if not isinstance(mapping, dict):
                    continue
                from_id, entry_data = deps._parse_mapping_entry(mapping)
                if from_id in entries_by_id and entry_data:
                    entries_by_id[from_id].append(entry_data)

            url = deps._get_next_page_url(response.headers)

        results: dict[str, JsonDict | None] = {}
        for id_, entries in entries_by_id.items():
            results[id_] = deps._select_primary_entry(entries)

        found_count = sum(1 for value in results.values() if value is not None)
        multiple_count = sum(
            1 for value in results.values() if value and value.get("all_mappings")
        )
        deps.logger.info(
            "idmapping_results_fetched",
            job_id=job_id,
            total=len(original_ids),
            found=found_count,
            not_found=len(original_ids) - found_count,
            multiple_mappings=multiple_count,
        )
        return results
