"""Value Objects for temporal primitives.

Contains type-safe wrappers for timestamps.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class Timestamp:
    """Value Object for timezone-aware timestamp (always UTC).

    Ensures that all timestamps are stored in UTC.
    """

    __slots__ = ("_value",)

    def __init__(self, value: datetime) -> None:
        if value.tzinfo is None:
            raise ValueError(
                "Timestamp must be timezone-aware. "
                "Use Timestamp.now() or Timestamp.from_iso() for convenience."
            )
        # Convert to UTC for consistency
        self._value = value.astimezone(timezone.utc)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_value" and hasattr(self, "_value"):
            raise AttributeError("Timestamp is immutable")
        super().__setattr__(name, value)

    @property
    def value(self) -> datetime:
        """Internal datetime object (timezone-aware, UTC)."""
        return self._value

    def to_iso(self) -> str:
        """Return ISO 8601 string with timezone."""
        return self._value.isoformat()

    def to_epoch(self) -> float:
        """Return Unix timestamp (seconds since epoch)."""
        return self._value.timestamp()

    def __str__(self) -> str:
        return self.to_iso()

    def __repr__(self) -> str:
        return f"Timestamp({self.to_iso()!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Timestamp):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Timestamp):
            return self._value < other._value
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Timestamp):
            return self._value <= other._value
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Timestamp):
            return self._value > other._value
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Timestamp):
            return self._value >= other._value
        return NotImplemented

    @classmethod
    def now(cls) -> Self:
        """Create Timestamp with current time in UTC."""
        return cls(datetime.now(timezone.utc))

    @classmethod
    def from_iso(cls, iso_string: str) -> Self:
        """Create Timestamp from ISO 8601 string.

        Args:
            iso_string: ISO 8601 formatted datetime string.
                       If no timezone info, assumes UTC.

        Returns:
            Timestamp instance.

        Raises:
            ValueError: If the string cannot be parsed.
        """
        try:
            dt = datetime.fromisoformat(iso_string)
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 format: '{iso_string}'") from e

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return cls(dt)

    @classmethod
    def from_epoch(cls, epoch: float) -> Self:
        """Create Timestamp from Unix timestamp."""
        return cls(datetime.fromtimestamp(epoch, tz=timezone.utc))

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.from_iso,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda ts: ts.to_iso()
            ),
        )
