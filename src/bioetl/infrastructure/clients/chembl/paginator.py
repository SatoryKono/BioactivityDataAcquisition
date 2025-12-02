from typing import Any
from bioetl.infrastructure.clients.base.contracts import PaginatorABC


class ChemblPaginator(PaginatorABC):
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
            # ChEMBL returns metadata but simple offset calculation is safer if we control state
            # Here we just return offset + limit if next is present, or parse "next" url.
            # For simplicity, we'll assume the caller manages offset state or we parse it.
            # Let's parse offset from next URL if possible, or just return a signal.
            # Since SourceClient usually manages loop, Paginator should return next state.
            # But contracts say get_next_marker(response).
            
            limit = meta.get("limit", 0)
            offset = meta.get("offset", 0)
            total = meta.get("total_count", 0)
            
            if offset + limit < total:
                return offset + limit
        return None

    def has_more(self, response: dict[str, Any]) -> bool:
        return self.get_next_marker(response) is not None

