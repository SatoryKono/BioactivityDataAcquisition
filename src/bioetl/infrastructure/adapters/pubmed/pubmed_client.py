# src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

import structlog

from bioetl.domain.exceptions import ApiError
from bioetl.domain.types import HealthStatus, Watermark

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

ENTREZ_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
logger = structlog.get_logger()


@dataclass
class PubMedAdapter:
    """PubMed adapter using UnifiedHTTPClient.

    Implements DataSourcePort for PubMed data extraction.
    """

    http_client: UnifiedHTTPClient
    email: str
    api_key: str | None = None
    batch_size: int = 200

    provider_name: str = "pubmed"

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        await self.http_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager."""
        await self.http_client.__aexit__(exc_type, exc_val, exc_tb)

    async def _get_pmids(self, search_term: str, max_count: int) -> list[str]:
        """Get PMIDs for a search term."""
        search_url = f"{ENTREZ_API_BASE}esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": search_term,
            "retmax": str(max_count),
            "usehistory": "y",
            "retmode": "json",
            "email": self.email,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = await self.http_client.get(search_url, params=params)
            data = response.json()
            return data.get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            logger.error("Failed to fetch PMIDs", error=str(e))
            raise ApiError(f"PubMed search failed: {e}") from e

    async def fetch(
        self,
        entity_type: str,
        watermark: Watermark | None = None,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: set[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch PubMed records.

        Args:
            entity_type: Must be 'publication'
            watermark: Unused for now (required by protocol)
            limit: Max records to fetch
            query: PubMed search query (defaults to pharmacogenomics search)
            filter_ids: Optional set of IDs to filter by (unused in PubMed)
            filter_field: Optional field name to filter on (unused in PubMed)

        Yields:
            Dict containing pmid, article_title, and raw_xml
        """
        # Note: filter_ids and filter_field are ignored for PubMed -
        # filtering should be done via query parameter
        _ = filter_ids, filter_field  # Mark as intentionally unused
        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

        search_term = query or "pharmacogenomics[Title/Abstract]"
        pmids = await self._get_pmids(search_term, limit or 10000)

        if not pmids:
            return

        total_fetched = 0
        for i in range(0, len(pmids), self.batch_size):
            id_batch = pmids[i : i + self.batch_size]

            fetch_url = f"{ENTREZ_API_BASE}efetch.fcgi"
            params = {
                "db": "pubmed",
                "id": ",".join(id_batch),
                "retmode": "xml",
                "rettype": "abstract",
                "email": self.email,
            }
            if self.api_key:
                params["api_key"] = self.api_key

            try:
                response = await self.http_client.get(fetch_url, params=params)

                try:
                    root = ET.fromstring(response.text)
                except ET.ParseError as e:
                    logger.error(
                        "XML parse error", error=str(e), text_sample=response.text[:100]
                    )
                    continue  # Skip batch on XML error

                for article_node in root.findall(".//PubmedArticle"):
                    pmid_node = article_node.find(".//PMID")
                    title_node = article_node.find(".//ArticleTitle")

                    record = {
                        "pmid": pmid_node.text if pmid_node is not None else None,
                        "article_title": (
                            title_node.text
                            if title_node is not None
                            else "No title found"
                        ),
                        "_raw_xml": ET.tostring(article_node, encoding="unicode"),
                    }
                    yield record

                    total_fetched += 1
                    if limit and total_fetched >= limit:
                        return

            except Exception as e:
                logger.error("Batch fetch failed", error=str(e))
                # Depending on strictness, we might want to raise or continue
                # For now, we log and raise to stop the pipeline on API errors
                raise ApiError(f"PubMed fetch failed: {e}") from e

    async def health_check(self) -> HealthStatus:
        """Check PubMed API availability."""
        try:
            # Use esearch for a lightweight check
            params = {
                "db": "pubmed",
                "term": "health",
                "retmax": "1",
                "retmode": "json",
                "email": self.email,
            }
            if self.api_key:
                params["api_key"] = self.api_key

            response = await self.http_client.get(
                f"{ENTREZ_API_BASE}esearch.fcgi", params=params
            )
            return (
                HealthStatus.HEALTHY
                if response.status_code == 200
                else HealthStatus.UNHEALTHY
            )
        except Exception:
            return HealthStatus.UNHEALTHY

    async def aclose(self) -> None:
        """Close adapter resources.

        Safely closes the HTTP client if it's open. Idempotent - safe to call
        multiple times. Handles cases where client may already be closed.
        """
        if (
            self.http_client
            and hasattr(self.http_client, "_client")
            and self.http_client._client is not None
        ):
            await self.http_client._client.aclose()
            self.http_client._client = None
