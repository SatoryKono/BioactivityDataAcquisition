"""ChEMBL Activity Watermark Extractor.

Extracts watermark from records.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class ActivityWatermarkExtractor:
    """Extracts watermark from ChEMBL records."""

    def __init__(self, watermark_field: str | None = None):
        self.watermark_field = watermark_field

    def extract(self, _context: PipelineContext, record: dict[str, Any]) -> Watermark:
        """Extract watermark and return Watermark wrapper.

        Behavior:
        - if activity_id present: Watermark.from_id(str(activity_id));
        - else use config field (e.g. updated_on) and return
          Watermark.from_timestamp(datetime in UTC) if valid ISO8601;
        - if value not date-like — Watermark.from_id(str(value));
        - if nothing — Watermark.from_id("").
        """
        activity_id = record.get("activity_id")
        if activity_id is not None:
            return Watermark.from_id(str(activity_id))

        fallback_field = self.watermark_field
        fallback_value = record.get(fallback_field) if fallback_field else None

        if fallback_value is None:
            return Watermark.from_id("")

        if isinstance(fallback_value, datetime):
            return Watermark.from_timestamp(
                fallback_value.replace(tzinfo=fallback_value.tzinfo or UTC)
            )

        if isinstance(fallback_value, str):
            try:
                parsed = datetime.fromisoformat(fallback_value)
            except ValueError:
                return Watermark.from_id(fallback_value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return Watermark.from_timestamp(parsed)

        return Watermark.from_id(str(fallback_value))
