# basedpyright residual burn-down (shrink-only product surface).
"""Publication year Value Object.

Contains PublicationYear — a bibliographic concept used by
publication pipeline transformers (ChEMBL, CrossRef, OpenAlex,
PubMed, Semantic Scholar).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.value_objects.base import ValueObject

if TYPE_CHECKING:
    from bioetl.domain.config import ValidationConfig

__all__ = [
    "PublicationYear",
]


class PublicationYear(ValueObject[int]):
    """Publication year value object with validation.

    Validates that the year falls within a configurable range for
    scientific publications.

    The validation range can be customized via ValidationConfig:
    - Default range: [1500, 2100] for standard scientific publications
    - Semantic Scholar: [1500, 2100] for historical publications

    Examples: 1953 (Watson & Crick), 2020 (COVID papers)

    Invariants:
        - Must be between config.min_publication_year and config.max_publication_year
        - Must be a positive integer

    Attributes:
        _config: ValidationConfig for year range validation.
    """

    __slots__ = ("_config",)
    _value: int
    _config: ValidationConfig

    # Class-level defaults for backward compatibility
    _DEFAULT_MIN_YEAR = 1500
    _DEFAULT_MAX_YEAR = 2100

    def __init__(  # pyright: ignore[reportMissingSuperCall]
        self,
        value: int | str,
        *,
        config: ValidationConfig | None = None,
    ) -> None:
        """Create PublicationYear with validated value.

        Args:
            value: Raw year value (int or string).
            config: Optional ValidationConfig for custom ranges.
                If None, uses DEFAULT_VALIDATION_CONFIG.

        Raises:
            ValueError: If year is outside valid range.

        Example:
            >>> year = PublicationYear(2020)
            >>> year.value
            2020
            >>> # With custom config for Semantic Scholar
            >>> from bioetl.domain.config import ValidationConfig
            >>> ss_config = ValidationConfig(min_publication_year=1500)
            >>> year = PublicationYear(1600, config=ss_config)

        """
        # Import here to avoid circular dependency
        from bioetl.domain.config import DEFAULT_VALIDATION_CONFIG

        resolved_config = config or DEFAULT_VALIDATION_CONFIG
        object.__setattr__(self, "_config", resolved_config)
        validated = self._validate(value)
        object.__setattr__(self, "_value", validated)

    def _coerce_to_int(self, value: int | str) -> int:
        """Coerce value to int, raising ValueError on failure.

        Also supports extracting year from date string format (YYYY-MM-DD).

        Args:
            value: Raw value to coerce.

        Returns:
            Integer year value.

        Raises:
            ValueError: If coercion fails.
        """
        if isinstance(value, bool):
            raise ValueError(f"PublicationYear must be int, got {type(value).__name__}")
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return self._parse_year_from_string(value)
        raise ValueError(f"PublicationYear must be int, got {type(value).__name__}")

    def _parse_year_from_string(self, value: str) -> int:
        """Parse year from string value.

        Supports direct integer strings and date formats (YYYY-MM-DD).

        Args:
            value: String value to parse.

        Returns:
            Parsed integer year.

        Raises:
            ValueError: If parsing fails.
        """
        stripped = value.strip()
        # Support date string format: "2024-01-15" → 2024
        if len(stripped) >= 4 and stripped[4:5] in ("-", "/", ""):
            try:
                return int(stripped[:4])
            except ValueError:
                pass  # Why: year prefix not parseable as int; fall through to full-string parse
        try:
            return int(stripped)
        except ValueError:
            raise ValueError(f"Invalid publication year: {value!r}") from None

    def _validate(self, value: int | str) -> int:
        """Validate publication year against config range.

        Args:
            value: Raw year value.

        Returns:
            Validated year.

        Raises:
            ValueError: If year is outside valid range.
        """
        int_value = self._coerce_to_int(value)
        min_year = self._config.min_publication_year
        max_year = self._config.max_publication_year
        if not min_year <= int_value <= max_year:
            raise ValueError(
                f"Year {int_value} outside valid range [{min_year}, {max_year}]"
            )
        return int_value

    @property
    def min_year(self) -> int:
        """Get the minimum valid year from config."""
        return self._config.min_publication_year

    @property
    def max_year(self) -> int:
        """Get the maximum valid year from config."""
        return self._config.max_publication_year

    @property
    def decade(self) -> int:
        """Get the decade of the publication year.

        Returns:
            Decade as integer (e.g., 1950 for year 1953).
        """
        return (self._value // 10) * 10

    @property
    def century(self) -> int:
        """Get the century of the publication year.

        Returns:
            Century as integer (e.g., 20 for year 1953).
        """
        return (self._value // 100) + 1

    @classmethod
    def from_raw(
        cls,
        raw: int | str | None,
        *,
        config: ValidationConfig | None = None,
    ) -> PublicationYear | None:
        """Create PublicationYear from raw value with normalization.

        Args:
            raw: Raw year integer, string, or None.
            config: Optional ValidationConfig for custom ranges.

        Returns:
            PublicationYear if valid, None if input is None, empty, or invalid.

        Example:
            >>> PublicationYear.from_raw("2020")
            PublicationYear(2020)
            >>> PublicationYear.from_raw("2024-01-15")  # Date string
            PublicationYear(2024)
            >>> PublicationYear.from_raw(None)
            None

        """
        if raw is None:
            return None
        if isinstance(raw, str) and not raw.strip():
            return None
        try:
            return cls(raw, config=config)
        except ValueError:
            return None

    def __eq__(self, other: object) -> bool:
        """Compare by value only (ignoring config)."""
        if not isinstance(other, PublicationYear):
            return NotImplemented
        return bool(self._value == other._value)

    def __hash__(self) -> int:
        """Hash based on class and value only (ignoring config)."""
        return hash((self.__class__.__name__, self._value))
