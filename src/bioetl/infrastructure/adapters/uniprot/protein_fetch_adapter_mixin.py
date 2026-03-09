# mypy: disable-error-code=attr-defined
"""Protein fetch internals for UniProtAdapter."""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.uniprot.query_builder import (
    build_uniprot_protein_search_params,
)
from bioetl.infrastructure.adapters.uniprot.response_parser import (
    parse_uniprot_protein_response,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import httpx

_UNIPROT_FETCH_ERRORS = (Exception,)

_PROTEIN_FETCH_FIELDS: tuple[str, ...] = (
    "accession",
    "id",
    "protein_name",
    "gene_names",
    "organism_name",
    "organism_id",
    "lineage",
    "sequence",
    "length",
    "mass",
    "protein_existence",
    "annotation_score",
    "reviewed",
    "date_created",
    "date_modified",
    "version",
    "cc_function",
    "cc_catalytic_activity",
    "cc_activity_regulation",
    "cc_subunit",
    "cc_pathway",
    "cc_subcellular_location",
    "cc_tissue_specificity",
    "cc_alternative_products",
    "cc_disease",
    "cc_cofactor",
    "ph_dependence",
    "temp_dependence",
    "kinetics",
    "absorption",
    "redox_potential",
    "cc_induction",
    "cc_caution",
    "cc_similarity",
    "cc_pharmaceutical",
    "ft_domain",
    "ft_binding",
    "ft_site",
    "ft_act_site",
    "ft_mod_res",
    "xref_pdb",
    "xref_chembl",
    "xref_drugbank",
    "xref_guidetopharmacology",
    "go_id",
    "xref_interpro",
    "xref_pfam",
    "xref_reactome",
    "keyword",
)


class UniProtProteinFetchAdapterMixin:
    """Protein endpoint helpers and pagination callbacks."""

    def _build_protein_fetch_params(
        self,
        query: str,
        size: int,
        fetched: int,
        limit: int | None,
        cursor: str | None,
    ) -> JsonDict:
        """Build protein search parameters.

        Returns:
            Dictionary of query parameters for the UniProt protein search request.
        """
        return build_uniprot_protein_search_params(
            query=query,
            fetched=fetched,
            limit=limit,
            cursor=cursor,
            size=size,
            fields=_PROTEIN_FETCH_FIELDS,
        )

    def _parse_response(
        self,
        response: httpx.Response,
    ) -> tuple[list[BronzeRecord], str | None]:
        """Parse UniProt protein response payload.

        Returns:
            Tuple of (list of protein records, next cursor string or None if last page).
        """
        return parse_uniprot_protein_response(response)

    async def _fetch_proteins(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch protein entries via paginated UniProt search endpoint."""
        query = query or "*"
        size = 500

        async def _pagination_callback(
            cursor: str | None, fetched: int
        ) -> tuple[list[BronzeRecord], str | None]:
            params = self._build_protein_fetch_params(
                query, size, fetched, limit, cursor
            )
            try:
                start_time = time.perf_counter()
                with self._adapter_metrics.measure_request("/uniprotkb/search"):
                    response = await self._http_client.get(
                        f"{self.base_url}/uniprotkb/search", params=params
                    )
                duration_ms = (time.perf_counter() - start_time) * 1000
                with contextlib.suppress(Exception):
                    self._request_collector.record_from_response(response, duration_ms)
                return self._parse_response(response)
            except _UNIPROT_FETCH_ERRORS as error:
                self._handle_fetch_error("protein", query, cursor, error=error)
                return [], None

        async for item in self.paginated_fetch(_pagination_callback, limit=limit):
            yield item

    def _handle_fetch_error(
        self,
        entity_type: str,
        query: str | None,
        cursor: str | None = None,
        error: Exception | None = None,
    ) -> None:
        """Handle fetch errors with strict/non-strict behavior."""
        context = {"query": query, "cursor": cursor, "entity_type": entity_type}
        if error is not None:
            self._error_handler.log_error(
                provider=self.provider_name,
                operation=f"{entity_type}_fetch",
                error=error,
                context=context,
            )
        else:
            self._logger.error(
                "external_api_error",
                provider=self.provider_name,
                operation=f"{entity_type}_fetch",
                **context,
            )

        if self.strict_error_handling and error is not None:
            wrapped = self._error_handler.wrap_error(
                error=error, provider=self.provider_name
            )
            raise wrapped from error
