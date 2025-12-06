from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from bioetl.domain.clients.base.contracts import PaginatorABC


class ChemblPaginatorImpl(PaginatorABC):
    """
    Стратегия пагинации ChEMBL (offset/limit).
    """

    def get_items(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        # Use parser logic or duplicate simple logic
        for key, value in response.items():
            if isinstance(value, list):
                return value
        return []

    def get_next_marker(self, response: dict[str, Any]) -> int | None:
        meta = response.get("page_meta", {})
        next_meta = meta.get("next")
        if next_meta:
            # Prefer offset calculation even if next URL is provided.
            limit = meta.get("limit", 0)
            offset = meta.get("offset", 0)
            total = meta.get("total_count", 0)

            if offset + limit < total:
                return offset + limit
        return None

    def has_more(self, response: dict[str, Any]) -> bool:
        return self.get_next_marker(response) is not None

    def get_next_request(
        self, response: dict[str, Any], current_url: str | None = None
    ) -> str | None:
        """
        Returns next request URL (absolute or relative) based on response pagination.

        Prefers the ``next`` field from ChEMBL metadata. If it is missing but
        ``offset``/``limit`` indicate more pages, it rebuilds a URL using the
        current URL and updated pagination parameters.
        """

        meta = response.get("page_meta", {}) or {}
        next_link = meta.get("next")
        limit = meta.get("limit")
        offset = meta.get("offset")
        total = meta.get("total_count")

        if next_link:
            return (
                urljoin(current_url or "", str(next_link))
                if current_url
                else str(next_link)
            )

        if None in (limit, offset, total):
            return None

        next_offset = offset + limit
        if next_offset >= total:
            return None

        if not current_url:
            return None

        parsed = urlparse(current_url)
        query = parse_qs(parsed.query)
        query["offset"] = [str(next_offset)]
        query["limit"] = [str(limit)]
        new_query = urlencode(query, doseq=True)
        return parsed._replace(query=new_query).geturl()
