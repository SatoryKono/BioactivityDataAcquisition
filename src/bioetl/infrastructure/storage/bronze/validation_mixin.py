# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Validation and path helpers for BronzeWriter."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any, cast

import orjson

from bioetl.domain.ports import LoggerPort


class BronzeWriterValidationMixin:
    """Mixin with input/path validation helpers for Bronze writes."""

    _flat_structure: bool = cast(Any, None)  # Any: host attr default (PD3)
    logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)

    def _resolve_bronze_path(
        self, provider: str, entity: str, date_str: str, filename: str
    ) -> str:
        """Resolve Bronze file path based on flat_structure setting.

        Args:
            provider: Data provider name (e.g., "chembl").
            entity: Entity type name (e.g., "activity").
            date_str: Date string in YYYY-MM-DD format for path partitioning.
            filename: Output filename including extension.

        Returns:
            Relative file path string using flat or nested directory structure.
        """
        if self._flat_structure:
            return f"{date_str}/{filename}"
        return f"{provider}/{entity}/{date_str}/{filename}"

    def _validate_bronze_names(self, provider: str, entity: str) -> None:
        """Validate provider and entity names (alphanumeric + underscores only).

        Args:
            provider: Data provider name to validate.
            entity: Entity type name to validate.

        Raises:
            ValueError: If provider or entity contains invalid characters.
        """
        for name, label in [(provider, "provider"), (entity, "entity")]:
            if not name or not name.replace("_", "").isalnum():
                raise ValueError(
                    f"Invalid {label} name: '{name}'. "
                    "Use alphanumeric characters and underscores only."
                )

    def _validate_records_iterator(self, records: Iterator[bytes]) -> None:
        """Validate that records is an Iterator[bytes].

        Args:
            records: Records iterator to validate for type and non-None value.

        Raises:
            TypeError: If records is None or does not implement __iter__.
        """
        if records is None:
            raise TypeError("records cannot be None, expected Iterator[bytes]")
        if not hasattr(records, "__iter__"):
            raise TypeError(
                f"records must be an Iterator[bytes] (or Iterable), got {type(records).__name__}"
            )

    def _validate_utc_datetime(self, dt: datetime, param_name: str) -> None:
        """Validate that datetime is timezone-aware and in UTC.

        Args:
            dt: Datetime to validate for timezone awareness and UTC offset.
            param_name: Parameter name used in error messages.

        Raises:
            ValueError: If dt is timezone-naive or not in UTC.
        """
        if dt.tzinfo is None:
            raise ValueError(f"{param_name} must be timezone-aware (UTC).")
        if dt.tzinfo.utcoffset(dt) != timedelta(0):
            raise ValueError(f"{param_name} must be UTC (offset 0).")

    def _validate_json_records(self, records: Iterator[bytes]) -> Iterator[bytes]:
        """Validate that each record is valid JSON bytes (lazy generator).

        Args:
            records: Iterator of record bytes to validate one by one.

        Returns:
            Iterator of validated JSON bytes, raising BronzeValidationError on invalid JSON.

        Raises:
            BronzeValidationError: If any record cannot be parsed as valid JSON.
        """
        from bioetl.domain.exceptions import BronzeValidationError

        for index, record in enumerate(records):
            try:
                orjson.loads(record)
            except orjson.JSONDecodeError as exc:
                raise BronzeValidationError(
                    message="Invalid JSON in Bronze record",
                    record_index=index,
                    original_error=str(exc),
                ) from exc
            yield record


__all__ = ["BronzeWriterValidationMixin"]
