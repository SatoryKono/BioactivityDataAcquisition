"""Response parser for ChEMBL API responses."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel, TypeAdapter

from bioetl.domain.ports.parsing import (
    RawPayload,
    RawRecordList,
    ResponseParserPortABC,
)

if TYPE_CHECKING:
    from bioetl.domain.clients.base.contracts import ResponseParserABC
    from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel

T = TypeVar("T", bound=BaseModel)


# =============================================================================
# New Generic Parser (Recommended)
# =============================================================================


class ChemblGenericResponseParser(ResponseParserPortABC):
    """Generic parser that returns untyped dicts.

    This parser belongs to infrastructure because:
    - It handles HTTP response structure (page_meta, nested lists)
    - It doesn't know about domain models
    - It only extracts raw data from API-specific format

    Example:
        >>> parser = ChemblGenericResponseParser()
        >>> records = parser.parse_to_records({"activities": [{"id": "1"}]})
        >>> pagination = parser.extract_pagination(response)
    """

    def parse_to_records(self, raw_response: RawPayload) -> RawRecordList:
        """Extract list of records from ChEMBL response.

        Args:
            raw_response: Raw dictionary payload from ChEMBL API.

        Returns:
            List of record dictionaries without type validation.
            Returns empty list if no records found.
        """
        for key, value in raw_response.items():
            if isinstance(value, list):
                # Return as-is without validation
                return [
                    dict(item) if isinstance(item, dict) else {"value": item}
                    for item in value
                ]
        return []

    def extract_pagination(
        self, raw_response: RawPayload
    ) -> dict[str, int | str | None]:
        """Extract page_meta from ChEMBL response.

        Args:
            raw_response: Raw dictionary payload from ChEMBL API.

        Returns:
            Dictionary containing pagination metadata:
            total_count, offset, limit, next.
        """
        page_meta = raw_response.get("page_meta", {})
        if not isinstance(page_meta, dict):
            page_meta = {}
        return {
            "total_count": page_meta.get("total_count"),
            "offset": page_meta.get("offset"),
            "limit": page_meta.get("limit"),
            "next": page_meta.get("next"),
        }


# =============================================================================
# Factory Functions
# =============================================================================


def create_generic_parser() -> ResponseParserPortABC:
    """Create parser for generic dict output (recommended).

    Returns:
        ChemblGenericResponseParser instance that parses responses
        into untyped dictionaries.

    Example:
        >>> parser = create_generic_parser()
        >>> records = parser.parse_to_records(response)
    """
    return ChemblGenericResponseParser()


def create_activity_parser() -> ChemblResponseParserImpl[ActivityRawModel]:
    """Factory for creating activity parser.

    .. deprecated:: 1.0
        Use :func:`create_generic_parser` instead.
        This function will be removed in version 2.0.

    Returns:
        ChemblResponseParserImpl configured for ActivityRawModel.
    """
    warnings.warn(
        "create_activity_parser() is deprecated. "
        "Use create_generic_parser() and application-layer mapping instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Lazy import to avoid domain coupling at module level
    from bioetl.domain.schemas.chembl.raw_models import (
        ActivityRawModel as ActivityModel,
    )

    return ChemblResponseParserImpl(ActivityModel)


# =============================================================================
# Deprecated Classes (Backward Compatibility)
# =============================================================================


class ChemblResponseParserImpl(Generic[T]):
    """Generic parser for ChEMBL API responses.

    .. deprecated:: 1.0
        Use :class:`ChemblGenericResponseParser` instead.
        This class will be removed in version 2.0.

    Supports parsing any Pydantic model from ChEMBL API responses.

    Example:
        >>> parser = ChemblResponseParserImpl(ActivityRawModel)
        >>> records = parser.parse({"activities": [{"activity_id": "1", ...}]})
    """

    def __init__(self, model_class: type[T]) -> None:
        """Initialize parser with model class.

        Args:
            model_class: Pydantic model class to use for validation.
        """
        warnings.warn(
            "ChemblResponseParserImpl is deprecated. "
            "Use ChemblGenericResponseParser and application-layer mapping instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._model_class = model_class

    def parse(self, raw_response: dict[str, object]) -> list[T]:
        """Parse raw response into models.

        Args:
            raw_response: Raw dictionary payload from ChEMBL API.

        Returns:
            List of validated Pydantic model instances.
        """
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
        """Return pagination metadata section from response.

        Args:
            raw_response: Raw dictionary payload from ChEMBL API.

        Returns:
            Dictionary containing pagination metadata.
        """
        adapter: TypeAdapter[dict[str, int | str | None]] = TypeAdapter(
            dict[str, int | str | None]
        )
        page_meta = raw_response.get("page_meta", {})
        return adapter.validate_python(page_meta)


# Backward compatibility alias
def _get_activity_parser_alias() -> type[ChemblResponseParserImpl[Any]]:
    """Get ChemblActivityResponseParser type alias with lazy import."""
    return ChemblResponseParserImpl


# This alias is deprecated but kept for backward compatibility
ChemblActivityResponseParser = ChemblResponseParserImpl


__all__ = [
    # New recommended API
    "ChemblGenericResponseParser",
    "create_generic_parser",
    # Deprecated (backward compatibility)
    "ChemblResponseParserImpl",
    "ChemblActivityResponseParser",
    "create_activity_parser",
]
