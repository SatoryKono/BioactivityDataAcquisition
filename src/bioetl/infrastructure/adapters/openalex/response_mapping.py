"""OpenAlex response mapping helpers."""

from __future__ import annotations

__all__ = ["OpenAlexResponseMapper"]

from dataclasses import dataclass
from typing import cast

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.response_shapes import (
    extract_response_items,
    extract_response_mapping,
    extract_response_text,
)


@dataclass(slots=True, frozen=True)
class OpenAlexResponseMapper:
    """Maps raw OpenAlex payloads/records to adapter-facing records."""

    def extract_results(self, payload: dict[str, object]) -> list[BronzeRecord]:
        """Extract API `results` array as BronzeRecord list.

        Args:
            payload: Decoded JSON payload dict from the OpenAlex API response.

        Returns:
            List of BronzeRecord dictionaries from the results array, or empty list if absent.
        """
        raw_results = extract_response_items(payload, "results")
        return [
            cast("BronzeRecord", item) for item in raw_results if isinstance(item, dict)
        ]

    def extract_next_cursor(self, payload: dict[str, object]) -> str | None:
        """Extract cursor from `meta.next_cursor`.

        Args:
            payload: Decoded JSON payload dict from the OpenAlex API response.

        Returns:
            Next cursor string if present, None if last page or meta is missing.
        """
        raw_meta = extract_response_mapping(payload, "meta")
        if raw_meta is None:
            return None
        return extract_response_text(raw_meta, "next_cursor")

    def mark_lookup(
        self,
        record: BronzeRecord,
        *,
        lookup_method: str,
        original_id: str | None = None,
        search_title: str | None = None,
    ) -> BronzeRecord:
        """Return copied record with standardized lookup metadata fields.

        Args:
            record: Source BronzeRecord to copy and annotate.
            lookup_method: Lookup method label to set in _lookup_method field (e.g., "doi", "title").
            original_id: Optional original ID string to embed in _original_id field.
            search_title: Optional search title string to embed in _search_title field.

        Returns:
            Copy of the record with _lookup_method and optional _original_id and _search_title fields set.
        """
        mapped = dict(record)
        mapped["_lookup_method"] = lookup_method
        if original_id is not None:
            mapped["_original_id"] = original_id
        if search_title is not None:
            mapped["_search_title"] = search_title
        return mapped
