# src/bioetl/infrastructure/adapters/pubmed_client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncIterator
import xml.etree.ElementTree as ET

from bioetl.domain.exceptions import ApiError
from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

ENTREZ_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

@dataclass
class PubMedAdapter:
    """Адаптер для извлечения данных из PubMed с использованием Entrez E-utilities."""
    http_client: UnifiedHTTPClient
    email: str  # NCBI просит указывать email в запросах
    api_key: str | None = None
    batch_size: int = 200  # Количество ID для одного запроса efetch

    provider_name: str = "pubmed"

    async def _get_pmids(self, search_term: str, max_count: int) -> list[str]:
        """Получает список ID статей (PMID) по поисковому запросу."""
        search_url = f"{ENTREZ_API_BASE}esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": search_term,
            "retmax": str(max_count),
            "usehistory": "y",
            "retmode": "json",
        }
        response = await self.http_client.get(search_url, params=params)
        data = response.json()
        return data.get("esearchresult", {}).get("idlist", [])

    async def fetch(
        self,
        entity_type: str, # будет "publication"
        search_term: str = "pharmacogenomics[Title/Abstract]", # Пример поискового запроса
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Извлекает полные записи статей из PubMed."""
        if entity_type != "publication":
            raise ValueError("PubMedAdapter поддерживает только 'publication'")

        pmids = await self._get_pmids(search_term, limit or 10000)
        
        if not pmids:
            return

        total_fetched = 0
        for i in range(0, len(pmids), self.batch_size):
            id_batch = pmids[i:i + self.batch_size]
            
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
                # Простая обработка XML
                root = ET.fromstring(response.text)
                for article_node in root.findall(".//PubmedArticle"):
                    # Здесь должна быть более сложная логика парсинга XML
                    # для извлечения нужных полей.
                    # Для примера извлечем только PMID и заголовок.
                    pmid_node = article_node.find(".//PMID")
                    title_node = article_node.find(".//ArticleTitle")
                    
                    record = {
                        "pmid": pmid_node.text if pmid_node is not None else None,
                        "article_title": title_node.text if title_node is not None else "No title found",
                        "_raw_xml": ET.tostring(article_node, encoding='unicode')
                    }
                    yield record
                    total_fetched += 1
                    if limit and total_fetched >= limit:
                        return

            except Exception as e:
                raise ApiError(f"Ошибка API PubMed (efetch): {e}") from e

    async def health_check(self) -> HealthStatus:
        """Проверяет доступность API PubMed."""
        try:
            # Простой запрос к esearch для проверки
            response = await self.http_client.get(f"{ENTREZ_API_BASE}esearch.fcgi", params={"db": "pubmed", "term": "health", "retmax": "1"})
            return HealthStatus.HEALTHY if response.status_code == 200 else HealthStatus.UNHEALTHY
        except Exception:
            return HealthStatus.UNHEALTHY

    async def aclose(self) -> None:
        pass
