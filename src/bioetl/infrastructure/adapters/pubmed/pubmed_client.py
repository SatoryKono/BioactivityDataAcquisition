# src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py
"""PubMed adapter for Entrez E-utilities API.

Implements DataSourcePort for PubMed article metadata extraction.

DTO Support:
- fetch_as_models(): Returns typed DTO models (ArticleRecord)
- fetch(): Returns raw dicts (backward compatible)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from bioetl.domain.entities.pubmed import ArticleRecord
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.error_handling import ErrorHandler
from bioetl.infrastructure.adapters.pubmed.xml_processor import PubMedXmlProcessor

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

ENTREZ_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# Mapping from entity_type to DTO model class
PUBMED_DTO_MODELS: dict[str, type[BaseModel]] = {
    "publication": ArticleRecord,
}


@dataclass
class PubMedAdapter(BaseHttpAdapter):
    """PubMed adapter using UnifiedHTTPClient.

    Inherits from BaseHttpAdapter for standardized lifecycle management
    and Template Method pattern for health checks.

    Implements DataSourcePort and FilterableDataSourcePort for PubMed data extraction
    with optional server-side filtering by PMID lists.

    Args:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        logger: LoggerPort instance for structured logging.
        email: Technical email for NCBI API tool identification (required).
            NOTE: This is NOT PII (Personally Identifiable Information).
            NCBI requires this for API usage tracking and rate limiting.
            Typically set to application/developer contact email, not end-user data.
            See: https://www.ncbi.nlm.nih.gov/books/NBK25497/
        api_key: Optional NCBI API key for higher rate limits.
        batch_size: Number of records to fetch per batch.
        metrics: Optional MetricsPort for recording adapter metrics.

    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    email: str
    api_key: str | None = None
    batch_size: int = 200
    metrics: MetricsPort | None = None

    provider_name: str = field(init=False, default="pubmed")
    """Provider identifier (required by DataSourcePort)."""

    def __post_init__(self) -> None:
        """Initialize adapter metrics and error handler after dataclass init."""
        # Initialize error handler from base class
        self._error_handler = ErrorHandler(self.logger)

        metrics_port = self.metrics if self.metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)

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
        # Only send API key if it's not a dummy value
        if self.api_key and "your_" not in self.api_key:
            params["api_key"] = self.api_key

        try:
            with self._adapter_metrics.measure_request("/esearch"):
                response = await self.http_client.get(search_url, params=params)
            data = response.json()
            idlist: list[str] = data.get("esearchresult", {}).get("idlist", [])
            return idlist
        except Exception as e:
            # Use unified error handler
            wrapped = self._error_handler.handle_error(
                error=e,
                provider=self.provider_name,
                operation="search",
                context={"search_term": search_term, "max_count": max_count},
            )
            raise wrapped from e

    def _build_fetch_params(self, id_batch: list[str]) -> dict[str, str]:
        """Build parameters for efetch API call."""
        params = {
            "db": "pubmed",
            "id": ",".join(id_batch),
            "retmode": "xml",
            "rettype": "abstract",
            "email": self.email,
        }
        # Only send API key if it's not a dummy value
        if self.api_key and "your_" not in self.api_key:
            params["api_key"] = self.api_key
        return params

    async def _fetch_batch(self, id_batch: list[str]) -> list[dict[str, Any]]:
        """Fetch a batch of articles and return parsed records."""
        params = self._build_fetch_params(id_batch)
        try:
            with self._adapter_metrics.measure_request("/efetch"):
                response = await self.http_client.get(
                    f"{ENTREZ_API_BASE}efetch.fcgi", params=params
                )
            root = PubMedXmlProcessor.parse_response(response.text)
            if root is None:
                self.logger.error(
                    "external_api_error",
                    provider=self.provider_name,
                    operation="batch_fetch",
                    error_category="DATA_QUALITY",
                    error="XML parse error",
                    batch_size=len(id_batch),
                )
                return []
            return PubMedXmlProcessor.extract_all_records(root)
        except Exception as e:
            # Use unified error handler
            wrapped = self._error_handler.handle_error(
                error=e,
                provider=self.provider_name,
                operation="batch_fetch",
                context={"batch_size": len(id_batch)},
            )
            raise wrapped from e

    async def _yield_articles_from_pmids(
        self, pmids: list[str], limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield article records from a list of PMIDs."""
        total_fetched = 0
        for i in range(0, len(pmids), self.batch_size):
            records = await self._fetch_batch(pmids[i : i + self.batch_size])
            for record in records:
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch PubMed records by ID list (bypass search).

        Implements FilterableDataSourcePort.fetch_filtered().

        Args:
            entity_type: Must be 'publication'.
            filter_ids: List of PMIDs to fetch.
            filter_field: Field name (expected 'pmid', others logged as warning).
            limit: Maximum number of records to fetch.

        Yields:
            Dictionary records for each article.

        Raises:
            ValueError: If entity_type is not 'publication'.

        """
        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

        if filter_field != "pmid":
            self.logger.warning(
                "unsupported_filter_field",
                field=filter_field,
                msg="Assuming PMIDs",
            )

        pmids = filter_ids[:limit] if limit else filter_ids
        async for record in self._yield_articles_from_pmids(pmids, limit):
            yield record

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch PubMed records."""
        if filter_ids:
            # Default to 'pmid' if filter_field not specified
            effective_filter_field = filter_field or "pmid"
            async for record in self.fetch_filtered(
                entity_type, filter_ids, effective_filter_field, limit
            ):
                yield record
            return

        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

        search_term = query or "pharmacogenomics[Title/Abstract]"
        pmids = await self._get_pmids(search_term, limit or 10000)

        if not pmids:
            return

        async for record in self._yield_articles_from_pmids(pmids, limit):
            yield record

    async def fetch_as_models(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        *,
        validate: bool = True,
    ) -> AsyncIterator[BaseModel]:
        """Fetch PubMed records as typed DTO models.

        Returns Pydantic DTO models instead of raw dicts for type safety.
        Uses domain DTOs with extra='forbid' to detect API changes.

        Args:
            entity_type: Type of entity (publication)
            limit: Maximum number of records to fetch
            query: Search query string
            filter_ids: List of PMIDs to filter by
            filter_field: Field name to filter on
            validate: If True, validate with model_validate (strict).
                     If False, use model_construct (skip validation, faster).

        Yields:
            Typed DTO models (ArticleRecord for publication)

        Raises:
            ValueError: If entity_type is not supported for DTO conversion

        Example:
            >>> async for article in adapter.fetch_as_models("publication", limit=10):
            ...     print(article.pmid, article.title)

        """
        model_class = PUBMED_DTO_MODELS.get(entity_type)
        if model_class is None:
            raise ValueError(
                f"No DTO model for entity_type '{entity_type}'. "
                f"Supported: {', '.join(PUBMED_DTO_MODELS.keys())}"
            )

        async for record in self.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            # Map field names from XML processor output to ArticleRecord DTO
            dto_data = {
                "pmid": record.get("pmid"),
                "title": record.get("article_title"),
                "raw_xml": record.get("_raw_xml"),
            }

            if validate:
                yield model_class.model_validate(dto_data)
            else:
                yield model_class.model_construct(**dto_data)

    async def _probe_health(self) -> HealthStatus:
        """Perform PubMed-specific health probe.

        Overrides BaseHttpAdapter._probe_health() to use PubMed esearch endpoint.

        Выполняет lightweight запрос к esearch endpoint.

        Returns:
            HealthStatus.HEALTHY — API доступен
            HealthStatus.DEGRADED — медленный отклик (>5 сек)
            HealthStatus.UNHEALTHY — non-200 response

        Raises:
            Exception: On request failure (logged before raising).

        """
        try:
            # Use esearch for a lightweight check
            params = {
                "db": "pubmed",
                "term": "health",
                "retmax": "1",
                "retmode": "json",
                "email": self.email,
            }
            # Only send API key if it's not a dummy value
            if self.api_key and "your_" not in self.api_key:
                params["api_key"] = self.api_key

            start_time = time.monotonic()
            with self._adapter_metrics.measure_request("/health"):
                response = await self.http_client.get(
                    f"{ENTREZ_API_BASE}esearch.fcgi", params=params
                )
            elapsed = time.monotonic() - start_time

            if response.status_code != 200:
                self.logger.warning(
                    "pubmed_health_check_failed",
                    status_code=response.status_code,
                )
                return HealthStatus.UNHEALTHY

            # Медленный отклик = degraded
            if elapsed > 5.0:
                self.logger.warning(
                    "pubmed_health_check_slow",
                    elapsed_seconds=round(elapsed, 2),
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
            raise  # Let health_check() return _fallback_health_status()

    def _fallback_health_status(self) -> HealthStatus:
        """Get fallback health status on probe failure.

        Overrides BaseHttpAdapter._fallback_health_status().
        PubMed doesn't use circuit breaker assessment, so returns UNHEALTHY.

        Returns:
            HealthStatus.UNHEALTHY

        """
        return HealthStatus.UNHEALTHY

    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint for PubMed.

        Returns:
            PubMed esearch endpoint used for health probe.

        """
        return "/entrez/eutils/esearch.fcgi"

    async def aclose(self) -> None:
        """Close adapter resources.

        Overrides BaseHttpAdapter.aclose() to properly close the HTTP client.
        Safely closes via the public context manager interface.
        Idempotent - safe to call multiple times.
        """
        if self.http_client:
            await self.http_client.__aexit__(None, None, None)


def _create_pubmed_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,
) -> PubMedAdapter:
    """Custom creator для PubMed адаптера.

    Обрабатывает логику получения email и api_key из settings.

    Args:
        http_client: HTTP клиент
        logger: Логгер
        settings: Настройки приложения
        **kwargs: Дополнительные параметры (email, api_key, metrics)

    Returns:
        Инициализированный PubMedAdapter

    Raises:
        ValueError: Если email не указан и не найден в settings
    """
    # Email: из kwargs или settings
    email = kwargs.get("email")
    if not email and settings:
        email = getattr(settings, "default_email", None)
    if not email:
        raise ValueError(
            "PubMed adapter requires email. "
            "Provide via 'email' kwarg or settings.default_email"
        )

    # API key: из kwargs или settings
    api_key = kwargs.get("api_key")
    if not api_key and settings and hasattr(settings, "pubmed_api_key"):
        pubmed_key = settings.pubmed_api_key
        if pubmed_key:
            api_key = pubmed_key.get_secret_value()

    if http_client is None:
        raise ValueError("PubMed adapter requires http_client")
    if logger is None:
        raise ValueError("PubMed adapter requires logger")

    return PubMedAdapter(
        http_client=http_client,
        logger=logger,
        email=email,
        api_key=api_key,
        batch_size=kwargs.get("batch_size", 200),
        metrics=kwargs.get("metrics"),
    )
