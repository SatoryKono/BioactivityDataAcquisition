"""NCBI Taxonomy ID Value Object.

Contains TaxonomyId Value Object for NCBI Taxonomy identifiers.
Used across multiple providers (ChEMBL, UniProt, PubMed) for organism
classification.

See: https://www.ncbi.nlm.nih.gov/taxonomy
"""

from __future__ import annotations

from bioetl.domain.value_objects.base import ValueObject

__all__ = [
    "TaxonomyId",
    "validate_taxonomy_id",
]


class TaxonomyId(ValueObject[int]):
    """NCBI Taxonomy ID.

    A positive integer uniquely identifying an organism in NCBI Taxonomy.
    Stored as integer for efficient storage and comparison.

    Examples: 9606 (Homo sapiens), 10090 (Mus musculus), 562 (E. coli)

    Invariants:
        - Must be a positive integer (>= 1)
        - Cannot exceed reasonable bounds (< 10^7)
        - Leading zeros are stripped if provided as string
    """

    __slots__ = ()
    _value: int
    _MIN_VALUE = 1
    _MAX_VALUE = 10_000_000  # Reasonable upper bound for NCBI taxonomy

    def __init__(self, value: str | int) -> None:
        """Create a TaxonomyId with validated value.

        Args:
            value: Raw value to validate and store (str or int).

        Raises:
            ValueError: If validation fails.
        """
        super().__init__(value)  # type: ignore[arg-type]

    def _coerce_to_int(self, value: str | int) -> int:
        """Coerce value to integer, raising ValueError on failure."""
        # bool is a subclass of int in Python, reject explicitly
        if isinstance(value, bool):
            raise ValueError("TaxonomyId must be str or int, got bool")

        # Handle int directly
        if isinstance(value, int):
            return value

        # Handle string: strip and parse
        stripped = str(value).strip()
        if not stripped:
            raise ValueError("TaxonomyId cannot be empty string")
        return self._parse_int(stripped)

    def _parse_int(self, value: str) -> int:
        """Parse string to integer, raising ValueError on failure."""
        try:
            return int(value)
        except ValueError as e:
            raise ValueError(f"Invalid TaxonomyId: {value!r}. Must be integer.") from e

    def _validate(self, value: str | int) -> int:
        """Validate and normalize Taxonomy ID to integer.

        Args:
            value: Raw taxonomy ID value (int or str).

        Returns:
            Validated integer value.

        Raises:
            ValueError: If format is invalid or value out of range.
        """
        int_value = self._coerce_to_int(value)

        if int_value < self._MIN_VALUE:
            raise ValueError(
                f"TaxonomyId must be >= {self._MIN_VALUE}, got {int_value}"
            )
        if int_value >= self._MAX_VALUE:
            raise ValueError(f"TaxonomyId must be < {self._MAX_VALUE}, got {int_value}")

        return int_value

    @property
    def as_str(self) -> str:
        """Get the taxonomy ID as string for JOIN operations."""
        return str(self._value)

    @property
    def ncbi_url(self) -> str:
        """Get the NCBI Taxonomy URL for this organism.

        Returns:
            Complete NCBI URL (e.g., 'https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=9606').
        """
        return (
            f"https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id={self._value}"
        )

    @classmethod
    def from_raw(cls, raw: object) -> TaxonomyId | None:
        """Create TaxonomyId from raw value with normalization.

        Handles common formats:
        - Integer: 9606
        - String: "9606"
        - String with whitespace: " 9606 "

        Args:
            raw: Raw taxonomy ID (string, integer, or None).

        Returns:
            TaxonomyId if valid, None if input is None, empty, or invalid.
        """
        if raw is None:
            return None
        if isinstance(raw, bool):
            return None

        normalized = cls._normalize_raw(raw)
        if normalized is None:
            return None
        return cls._build_or_none(normalized)

    @classmethod
    def _normalize_raw(cls, raw: object) -> str | int | None:
        """Normalize raw input into canonical str/int candidate."""
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            stripped = raw.strip()
            if stripped:
                return stripped
        return None

    @classmethod
    def _build_or_none(cls, candidate: str | int) -> TaxonomyId | None:
        """Create value object and convert validation failures to ``None``."""
        try:
            return cls(candidate)
        except ValueError:
            return None


# ============================================================================
# Helper functions for field converters
# ============================================================================


def validate_taxonomy_id(value: object) -> int | None:
    """Validate and convert raw value to taxonomy ID integer.

    Convenience function for use in field_specs converters where
    integer output is needed (e.g., AssayTransformer, TargetComponentTransformer).

    Args:
        value: Raw taxonomy ID value (string, integer, or None).

    Returns:
        Validated integer taxonomy ID, or None if invalid.

    Examples:
        >>> validate_taxonomy_id(9606)
        9606
        >>> validate_taxonomy_id("9606")
        9606
        >>> validate_taxonomy_id(None)
        None
        >>> validate_taxonomy_id("invalid")
        None
    """
    vo = TaxonomyId.from_raw(value)
    return vo.value if vo else None
