from typing import Any
from bioetl.infrastructure.clients.base.contracts import ResponseParserABC


class ChemblResponseParser(ResponseParserABC):
    """
    Парсер ответов ChEMBL API.
    """

    def parse(self, raw_response: dict[str, Any]) -> list[dict[str, Any]]:
        # ChEMBL responses are usually { "activities": [...], "page_meta": ... }
        # We need to find the list key.
        # Heuristic: find the key that holds a list of dicts.
        for key, value in raw_response.items():
            if isinstance(value, list) and (not value or isinstance(value[0], dict)):
                return value
        return []

    def extract_metadata(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        return raw_response.get("page_meta", {})

