"""Response parser for ChEMBL API responses."""

from __future__ import annotations

from bioetl.domain.ports.parsing import (
    RawPayload,
    RawRecordList,
    ResponseParserPortABC,
)

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


__all__ = [
    "ChemblGenericResponseParser",
    "create_generic_parser",
]
