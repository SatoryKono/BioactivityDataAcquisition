# src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.exceptions import ApiError
from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

ENTREZ_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


@dataclass
class PubMedAdapter:
    """PubMed adapter using UnifiedHTTPClient.

    Implements DataSourcePort for PubMed data extraction.

    Args:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        logger: LoggerPort instance for structured logging.
        email: Email address for NCBI API (required).
        api_key: Optional NCBI API key for higher rate limits.
        batch_size: Number of records to fetch per batch.
    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
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
            self.logger.error("Failed to fetch PMIDs", error=str(e))
            raise ApiError(f"PubMed search failed: {e}") from e

    def _build_fetch_params(self, id_batch: list[str]) -> dict[str, str]:
        """Build parameters for efetch API call."""
        params = {
            "db": "pubmed",
            "id": ",".join(id_batch),
            "retmode": "xml",
            "rettype": "abstract",
            "email": self.email,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    @staticmethod
    def _extract_record_from_article(article_node: ET.Element) -> dict[str, Any]:
        """Extract record dict from a PubmedArticle XML node."""
        pmid_node = article_node.find(".//PMID")
        title_node = article_node.find(".//ArticleTitle")
        return {
            "pmid": pmid_node.text if pmid_node is not None else None,
            "article_title": (
                title_node.text if title_node is not None else "No title found"
            ),
            "_raw_xml": ET.tostring(article_node, encoding="unicode"),
        }

    async def _fetch_batch(self, id_batch: list[str]) -> ET.Element | None:
        """Fetch a batch of articles and return parsed XML root."""
        params = self._build_fetch_params(id_batch)
        try:
            response = await self.http_client.get(
                f"{ENTREZ_API_BASE}efetch.fcgi", params=params
            )
            return ET.fromstring(response.text)
        except ET.ParseError as e:
            self.logger.error("XML parse error", error=str(e))
            return None
        except Exception as e:
            self.logger.error("Batch fetch failed", error=str(e))
            raise ApiError(f"PubMed fetch failed: {e}") from e

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch PubMed records by ID list (bypass search)."""
        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

        if filter_field and filter_field != "pmid":
            self.logger.warning(
                "Unsupported filter_field: %s. Assuming PMIDs.", filter_field
            )

        total_fetched = 0
        # If limit is set, we can restrict the list of IDs upfront
        # assuming 1 ID -> 1 Record (which is true for PubMed efetch)
        pmids = filter_ids[:limit] if limit else filter_ids

        for i in range(0, len(pmids), self.batch_size):
            batch_ids = pmids[i : i + self.batch_size]
            root = await self._fetch_batch(batch_ids)
            if root is None:
                continue

            for article_node in root.findall(".//PubmedArticle"):
                yield self._extract_record_from_article(article_node)
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: set[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch PubMed records."""
        _ = filter_ids, filter_field  # Mark as intentionally unused
        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

        search_term = query or "pharmacogenomics[Title/Abstract]"
        pmids = await self._get_pmids(search_term, limit or 10000)

        if not pmids:
            return

        total_fetched = 0
        for i in range(0, len(pmids), self.batch_size):
            root = await self._fetch_batch(pmids[i : i + self.batch_size])
            if root is None:
                continue

            for article_node in root.findall(".//PubmedArticle"):
                yield self._extract_record_from_article(article_node)
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

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
