"""Response parser for ChEMBL API responses."""

from pydantic import TypeAdapter

from bioetl.domain.clients.base.contracts import ResponseParserABC
from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel


class ChemblResponseParserImpl(ResponseParserABC[ActivityRawModel]):
    """
    Парсер ответов ChEMBL API.
    """

    def parse_response(self, raw_response: dict[str, object]) -> list[ActivityRawModel]:
        """Extract and validate activity payloads from ChEMBL response."""
        # ChEMBL responses are usually { "activities": [...], "page_meta": ... }
        # We need to find the list key.
        # Heuristic: find the key that holds a list of dicts.
        for key, value in raw_response.items():
            if isinstance(value, list) and (not value or isinstance(value[0], dict)):
                return [ActivityRawModel.model_validate(item) for item in value]
        return []

    def extract_metadata(
        self, raw_response: dict[str, object]
    ) -> dict[str, int | str | None]:
        """Return pagination metadata section from response."""
        adapter: TypeAdapter[dict[str, int | str | None]] = TypeAdapter(
            dict[str, int | str | None]
        )
        page_meta = raw_response.get("page_meta", {})
        return adapter.validate_python(page_meta)
