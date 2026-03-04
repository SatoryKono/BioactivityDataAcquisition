"""OpenAlex response mapping helpers."""

from __future__ import annotations

__all__ = ["OpenAlexResponseMapper"]

from dataclasses import dataclass
from typing import cast

from bioetl.domain.types import BronzeRecord


@dataclass(slots=True, frozen=True)
class OpenAlexResponseMapper:
    """Maps raw OpenAlex payloads/records to adapter-facing records."""

    def extract_results(self, payload: dict[str, object]) -> list[BronzeRecord]:
        """Extract API `results` array as BronzeRecord list."""
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            return []
        return [
            cast("BronzeRecord", item) for item in raw_results if isinstance(item, dict)
        ]

    def extract_next_cursor(self, payload: dict[str, object]) -> str | None:
        """Extract cursor from `meta.next_cursor`."""
        raw_meta = payload.get("meta")
        if not isinstance(raw_meta, dict):
            return None
        raw_cursor = raw_meta.get("next_cursor")
        if isinstance(raw_cursor, str):
            return raw_cursor
        return None

    def mark_lookup(
        self,
        record: BronzeRecord,
        *,
        lookup_method: str,
        original_id: str | None = None,
        search_title: str | None = None,
    ) -> BronzeRecord:
        """Return copied record with standardized lookup metadata fields."""
        mapped = dict(record)
        mapped["_lookup_method"] = lookup_method
        if original_id is not None:
            mapped["_original_id"] = original_id
        if search_title is not None:
            mapped["_search_title"] = search_title
        return mapped
