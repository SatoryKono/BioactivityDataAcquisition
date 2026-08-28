# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Transport and result retrieval logic for UniProt ID mapping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.common.response_shapes import (
    extract_response_items,
    extract_response_text,
)
from bioetl.infrastructure.adapters.uniprot._idmapping_errors import IDMappingJobError
from bioetl.infrastructure.adapters.uniprot._idmapping_url_policy import (
    trusted_idmapping_url,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder


@runtime_checkable
class IDMappingTransportDependencies(Protocol):
    """Host dependency contract for IDMappingTransportMixin."""

    logger: LoggerPort
    http_client: Any  # Any: preserves BaseHttpAdapter-compatible host typing.
    _adapter_metrics: AdapterMetricsRecorder
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
    """HTTP transport helpers for job submission and result retrieval.

    Host attributes come from the concrete client; they are not re-declared
    here so MRO types stay compatible with BaseHttpAdapter.
    """

    def _transport_deps(self) -> IDMappingTransportDependencies:
        """Return typed dependency view of the host client.

        Returns:
            IDMappingTransportDependencies cast of the current client instance.
        """
        return cast("IDMappingTransportDependencies", self)  # pyright: ignore[reportInvalidCast]

    async def _map_batch(
        self,
        from_db: str,
        to_db: str,
        ids: list[str],
    ) -> dict[str, JsonDict | None]:  # Any: untyped API JSON
        """Map a batch of IDs.

        Returns:
            Dictionary mapping each source ID to its UniProt entry dict, or None if not found.
        """
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
        """Submit ID mapping job to UniProt.

        Returns:
            Job ID string assigned by UniProt for polling.
        """
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
        if not isinstance(result, dict):
            raise IDMappingJobError(
                job_id="unknown", message="No jobId in malformed response"
            )
        job_id = extract_response_text(result, "jobId")
        if not job_id:
            raise IDMappingJobError(job_id="unknown", message="No jobId in response")

        deps.logger.debug("idmapping_job_submitted", job_id=job_id)
        return str(job_id)

    async def _fetch_results_pages(
        self,
        job_id: str,
        entries_by_id: dict[str, list[JsonDict]],
        start_url: str,
    ) -> None:
        """Paginate through ID mapping results, populating entries_by_id in place."""
        deps = self._transport_deps()
        url: str | None = trusted_idmapping_url(deps.base_url, start_url)

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
            if not isinstance(data, dict):
                break
            for mapping in extract_response_items(data, "results"):
                if not isinstance(mapping, dict):
                    continue
                from_id, entry_data = deps._parse_mapping_entry(mapping)
                if from_id in entries_by_id and entry_data:
                    entries_by_id[from_id].append(entry_data)

            next_url = deps._get_next_page_url(response.headers)
            url = (
                trusted_idmapping_url(deps.base_url, next_url)
                if next_url is not None
                else None
            )

    def _resolve_entries(
        self,
        entries_by_id: dict[str, list[JsonDict]],
    ) -> dict[str, JsonDict | None]:  # Any: untyped API JSON
        """Select primary entry for each ID and return final results.

        Returns:
            Dictionary mapping each source ID to its resolved UniProt entry dict, or None if not found.
        """
        deps = self._transport_deps()
        return {
            id_: deps._select_primary_entry(entries)
            for id_, entries in entries_by_id.items()
        }

    def _log_fetch_summary(
        self,
        job_id: str,
        results: dict[str, JsonDict | None],
        total: int,
    ) -> None:
        """Log summary statistics for fetched ID mapping results."""
        deps = self._transport_deps()
        found_count = sum(1 for value in results.values() if value is not None)
        multiple_count = sum(
            1 for value in results.values() if value and value.get("all_mappings")
        )
        deps.logger.info(
            "idmapping_results_fetched",
            job_id=job_id,
            total=total,
            found=found_count,
            not_found=total - found_count,
            multiple_mappings=multiple_count,
        )

    async def _fetch_results(
        self,
        job_id: str,
        original_ids: list[str],
        results_url: str | None = None,
    ) -> dict[str, JsonDict | None]:  # Any: untyped API JSON
        """Fetch mapping results with full entry metadata.

        Returns:
            Dictionary mapping each source ID to its resolved UniProt entry dict, or None if not found.
        """
        deps = self._transport_deps()
        entries_by_id: dict[str, list[JsonDict]] = {id_: [] for id_ in original_ids}
        start_url = results_url or f"{deps.base_url}/idmapping/results/{job_id}"

        await self._fetch_results_pages(job_id, entries_by_id, start_url)
        results = self._resolve_entries(entries_by_id)
        self._log_fetch_summary(job_id, results, len(original_ids))
        return results
