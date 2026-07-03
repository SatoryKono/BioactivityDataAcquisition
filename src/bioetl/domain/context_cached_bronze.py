"""Cached bronze context value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CachedBronzeContext:
    """Configuration for loading data from cached Bronze layer."""

    enabled: bool = False
    bronze_path: str | None = None
    bronze_date: str | None = None

    @classmethod
    def disabled(cls) -> CachedBronzeContext:
        """Create a disabled context (use API, not cache)."""
        return cls(enabled=False, bronze_path=None, bronze_date=None)

    @classmethod
    def from_options(
        cls,
        path: str | None = None,
        date: str | None = None,
    ) -> CachedBronzeContext:
        """Create an enabled context from CLI/config options.

        Args:
            path: Optional file system path to the cached Bronze layer directory.
            date: Optional date string in YYYY-MM-DD format identifying the cache snapshot.

        Returns:
            CachedBronzeContext with enabled=True and the provided path and date.
        """
        return cls(enabled=True, bronze_path=path, bronze_date=date)

    def __post_init__(self) -> None:
        """Validate cached bronze configuration."""
        if not self.enabled:
            return
        if self.bronze_date is not None:
            self._validate_date_format()

    def _validate_date_format(self) -> None:
        """Validate bronze_date is in YYYY-MM-DD format."""
        if self.bronze_date is None:
            return
        try:
            datetime.strptime(self.bronze_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"bronze_date must be in YYYY-MM-DD format, got '{self.bronze_date}'"
            ) from e


__all__ = ["CachedBronzeContext"]
