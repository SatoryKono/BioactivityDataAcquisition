"""Response parser for ChEMBL API responses."""

from __future__ import annotations

import warnings

from bioetl.domain.ports.parsing import (
    ApiPayload,
    RawRecord,
    RecordBatch,
    ResponseParserPortABC,
)

# =============================================================================
# New Generic Parser (Recommended)
# =============================================================================


class ChemblGenericResponseParser(ResponseParserPortABC[RawRecord]):
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

    def parse_to_records(self, raw_response: ApiPayload) -> RecordBatch:
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
        self, raw_response: ApiPayload
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


# =============================================================================
# Deprecated Aliases (Backward Compatibility)
# =============================================================================

# Legacy class name that was previously typed on ActivityRawModel.
# Available via __getattr__ to emit deprecation warning on first access.
_DEPRECATED_ALIASES = {
    "ChemblResponseParserImpl": "ChemblGenericResponseParser",
}


def __getattr__(name: str) -> object:
    """Emit deprecation warning for legacy class name imports.

    Enables backward-compatible imports like:
        from bioetl.infrastructure.clients.chembl.response_parser import (
            ChemblResponseParserImpl
        )

    But emits a DeprecationWarning directing users to the new class name.
    """
    if name in _DEPRECATED_ALIASES:
        new_name = _DEPRECATED_ALIASES[name]
        warnings.warn(
            f"{name} is deprecated, use {new_name} instead. "
            "ChemblResponseParserImpl was removed in v2.0 as part of hexagonal "
            "architecture refactoring. See docs/migration/2.0-hexagonal-architecture.md",
            DeprecationWarning,
            stacklevel=2,
        )
        return ChemblGenericResponseParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ChemblGenericResponseParser",
    "create_generic_parser",
    # Deprecated aliases (available via __getattr__)
    "ChemblResponseParserImpl",
]
