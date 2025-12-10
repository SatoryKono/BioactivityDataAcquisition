"""Response parser for ChEMBL API responses."""

import warnings
from typing import Generic, TypeVar

from pydantic import BaseModel, TypeAdapter

from bioetl.domain.clients.base.contracts import ResponseParserABC
from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel

T = TypeVar("T", bound=BaseModel)


class ChemblResponseParserImpl(ResponseParserABC[T], Generic[T]):
    """
    Generic parser for ChEMBL API responses.

    Supports parsing any Pydantic model from ChEMBL API responses.

    Example:
        >>> parser = ChemblResponseParserImpl(ActivityRawModel)
        >>> records = parser.parse({"activities": [{"activity_id": "1", ...}]})
    """

    def __init__(self, model_class: type[T]) -> None:
        """
        Initialize parser with model class.

        Args:
            model_class: Pydantic model class to use for validation.
        """
        self._model_class = model_class

    def parse(self, raw_response: dict[str, object]) -> list[T]:
        """Parse raw response into models."""
        for key, value in raw_response.items():
            if isinstance(value, list) and (not value or isinstance(value[0], dict)):
                return [self._model_class.model_validate(item) for item in value]
        return []

    def parse_response(self, raw_response: dict[str, object]) -> list[T]:
        """Deprecated alias for parse.

        .. deprecated:: 1.0
            Use :meth:`parse` instead. Will be removed in 2.0.
        """
        warnings.warn(
            "parse_response() is deprecated, use parse() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.parse(raw_response)

    def extract_metadata(
        self, raw_response: dict[str, object]
    ) -> dict[str, int | str | None]:
        """Return pagination metadata section from response."""
        adapter: TypeAdapter[dict[str, int | str | None]] = TypeAdapter(
            dict[str, int | str | None]
        )
        page_meta = raw_response.get("page_meta", {})
        return adapter.validate_python(page_meta)


# Backward compatibility alias
ChemblActivityResponseParser = ChemblResponseParserImpl[ActivityRawModel]


def create_activity_parser() -> ChemblResponseParserImpl[ActivityRawModel]:
    """Factory for creating activity parser (backward compatibility)."""
    return ChemblResponseParserImpl(ActivityRawModel)
