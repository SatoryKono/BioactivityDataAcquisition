"""Chemical structure Value Objects for BioETL domain.

Contains Value Objects for chemical structure identifiers:
- InChIKey: InChI Key identifiers (BSYNRYMUTXBXSQ-UHFFFAOYSA-N)
- SMILES: SMILES notation strings
- PublicationYear: Publication year with validation
- MolecularWeight: Molecular weight with validation and precision

These Value Objects encapsulate validation and normalization rules.
"""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.base import ValueObject

if TYPE_CHECKING:
    from bioetl.domain.config import ValidationConfig


class InChIKey(ValueObject[str]):
    """InChI Key value object.

    InChI Keys are 27-character strings in the format:
    XXXXXXXXXXXXXX-YYYYYYYYYY-Z

    Where:
    - First 14 characters: connectivity layer (molecular skeleton)
    - Middle 10 characters: stereochemistry and isotopes layer
    - Last character: protonation state (usually N for neutral)

    Examples: BSYNRYMUTXBXSQ-UHFFFAOYSA-N (aspirin)

    Invariants:
        - Must be exactly 27 characters
        - Format: 14 uppercase letters, hyphen, 10 uppercase letters, hyphen, 1 uppercase letter
        - Normalized to uppercase
    """

    __slots__ = ()
    _value: str

    _PATTERN = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")

    def _validate(self, value: str) -> str:
        """Validate and normalize InChI Key.

        Args:
            value: Raw InChI Key string.

        Returns:
            Normalized uppercase InChI Key.

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"InChIKey must be str, got {type(value).__name__}")

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("InChIKey cannot be empty")

        if not self._PATTERN.match(normalized):
            raise ValueError(
                f"Invalid InChI Key format: {value!r}. "
                "Expected: XXXXXXXXXXXXXX-YYYYYYYYYY-Z (27 chars)"
            )

        return normalized

    @property
    def connectivity_layer(self) -> str:
        """Get the connectivity layer (first 14 characters).

        The connectivity layer encodes the molecular skeleton,
        describing atom connections without stereochemistry.

        Returns:
            First 14 characters of the InChI Key.
        """
        return self._value[:14]

    @property
    def stereochemistry_layer(self) -> str:
        """Get the stereochemistry and isotopes layer (middle 10 characters).

        This layer encodes stereochemistry information and isotope labels.
        'UHFFFAOYSA' indicates no stereochemistry or isotopes.

        Returns:
            Middle 10 characters (positions 15-24) of the InChI Key.
        """
        return self._value[15:25]

    @property
    def protonation_layer(self) -> str:
        """Get the protonation layer (last character).

        Indicates the protonation state:
        - N: neutral
        - Other letters indicate charged states

        Returns:
            Last character of the InChI Key.
        """
        return self._value[-1]

    @classmethod
    def from_raw(cls, raw: str | None) -> InChIKey | None:
        """Create InChIKey from raw string with normalization.

        Args:
            raw: Raw InChI Key string or None.

        Returns:
            InChIKey if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class SMILES(ValueObject[str]):
    """SMILES notation value object.

    Simplified Molecular-Input Line-Entry System (SMILES) is a string
    notation for describing molecular structure.

    Examples:
    - CC(=O)OC1=CC=CC=C1C(=O)O (aspirin)
    - CN1C=NC2=C1C(=O)N(C(=O)N2C)C (caffeine)

    Invariants:
        - Must be a non-empty string
        - Normalized by stripping whitespace
        - Optionally can be marked as canonical
    """

    __slots__ = ("_is_canonical",)
    _value: str
    _is_canonical: bool

    def __init__(self, value: str, *, is_canonical: bool = False) -> None:
        """Create SMILES with validated value.

        Args:
            value: Raw SMILES string.
            is_canonical: Whether this is a canonical SMILES.

        Raises:
            ValueError: If validation fails.
        """
        validated = self._validate(value)
        object.__setattr__(self, "_value", validated)
        object.__setattr__(self, "_is_canonical", is_canonical)

    def _validate(self, value: str) -> str:
        """Validate and normalize SMILES.

        Args:
            value: Raw SMILES string.

        Returns:
            Normalized SMILES string.

        Raises:
            ValueError: If SMILES is empty.
        """
        if not isinstance(value, str):
            raise ValueError(f"SMILES must be str, got {type(value).__name__}")

        normalized = value.strip()
        if not normalized:
            raise ValueError("SMILES cannot be empty")

        return normalized

    @property
    def is_canonical(self) -> bool:
        """Check if this is a canonical SMILES representation.

        Canonical SMILES are unique representations where the same
        molecule always produces the same SMILES string.

        Returns:
            True if this is marked as canonical SMILES.
        """
        return self._is_canonical

    @classmethod
    def canonical(cls, smiles: str) -> SMILES:
        """Create a canonical SMILES.

        Args:
            smiles: Canonical SMILES string.

        Returns:
            SMILES marked as canonical.
        """
        return cls(smiles, is_canonical=True)

    @classmethod
    def from_raw(cls, raw: str | None, *, is_canonical: bool = False) -> SMILES | None:
        """Create SMILES from raw string with normalization.

        Args:
            raw: Raw SMILES string or None.
            is_canonical: Whether this is a canonical SMILES.

        Returns:
            SMILES if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw, is_canonical=is_canonical)
        except ValueError:
            return None

    def __eq__(self, other: object) -> bool:
        """Compare by value and canonical flag."""
        if not isinstance(other, SMILES):
            return NotImplemented
        return self._value == other._value and self._is_canonical == other._is_canonical

    def __hash__(self) -> int:
        """Hash based on class, value, and canonical flag."""
        return hash((self.__class__.__name__, self._value, self._is_canonical))

    def __repr__(self) -> str:
        """String representation showing class and value."""
        if self._is_canonical:
            return f"SMILES({self._value!r}, is_canonical=True)"
        return f"SMILES({self._value!r})"


class PublicationYear(ValueObject[int]):
    """Publication year value object with validation.

    Validates that the year falls within a configurable range for
    scientific publications.

    The validation range can be customized via ValidationConfig:
    - Default range: [1800, 2100] for standard scientific publications
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
    _DEFAULT_MIN_YEAR = 1800
    _DEFAULT_MAX_YEAR = 2100

    def __init__(
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
                pass
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


class MolecularWeight(ValueObject[float]):
    """Molecular weight value object with validation.

    Validates molecular weight against configurable range and rounds
    to specified precision per RULES.md §2.8.1.

    Default validation range: (10.0, 10000.0) Da - covers small molecules
    to large peptides. Range is exclusive (open interval).

    Attributes:
        _config: ValidationConfig for range and precision.

    Invariants:
        - Must be between config.min_molecular_weight and max_molecular_weight
        - Rounded to config.molecular_weight_precision decimals
        - Cannot be NaN or Inf

    Example:
        >>> mw = MolecularWeight(180.156)
        >>> mw.value
        180.156
        >>> # Rounding to precision
        >>> mw = MolecularWeight(180.15600000001)
        >>> mw.value
        180.156

    """

    __slots__ = ("_config",)
    _value: float
    _config: ValidationConfig

    def __init__(
        self,
        value: float | int | str,
        *,
        config: ValidationConfig | None = None,
    ) -> None:
        """Create MolecularWeight with validated value.

        Args:
            value: Raw molecular weight value.
            config: Optional ValidationConfig for custom ranges.
                If None, uses DEFAULT_VALIDATION_CONFIG.

        Raises:
            ValueError: If MW is outside valid range or invalid.

        """
        # Import here to avoid circular dependency
        from bioetl.domain.config import DEFAULT_VALIDATION_CONFIG

        resolved_config = config or DEFAULT_VALIDATION_CONFIG
        object.__setattr__(self, "_config", resolved_config)
        validated = self._validate(value)
        object.__setattr__(self, "_value", validated)

    def _validate(self, value: float | int | str) -> float:
        """Validate and normalize molecular weight.

        Args:
            value: Raw molecular weight value.

        Returns:
            Validated and rounded float.

        Raises:
            ValueError: If MW is invalid or outside range.
        """
        # Convert to float
        try:
            float_value = float(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid molecular weight: {value!r}") from e

        # Check for NaN/Inf
        if math.isnan(float_value) or math.isinf(float_value):
            raise ValueError(f"Invalid molecular weight: {value} (NaN or Inf)")

        # Validate range (exclusive bounds)
        min_mw = self._config.min_molecular_weight
        max_mw = self._config.max_molecular_weight
        if not min_mw < float_value < max_mw:
            raise ValueError(
                f"Molecular weight {float_value} outside range ({min_mw}, {max_mw})"
            )

        # Round to precision
        precision = self._config.molecular_weight_precision
        return round(float_value, precision)

    @property
    def min_weight(self) -> float:
        """Get the minimum valid molecular weight from config."""
        return self._config.min_molecular_weight

    @property
    def max_weight(self) -> float:
        """Get the maximum valid molecular weight from config."""
        return self._config.max_molecular_weight

    @classmethod
    def from_raw(
        cls,
        raw: float | int | str | None,
        *,
        config: ValidationConfig | None = None,
    ) -> MolecularWeight | None:
        """Create MolecularWeight from raw value with normalization.

        Args:
            raw: Raw molecular weight value or None.
            config: Optional ValidationConfig for custom ranges.

        Returns:
            MolecularWeight if valid, None if input is None or invalid.

        Example:
            >>> MolecularWeight.from_raw(180.156)
            MolecularWeight(180.156)
            >>> MolecularWeight.from_raw("342.30")  # String from API
            MolecularWeight(342.3)
            >>> MolecularWeight.from_raw(None)
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
        if not isinstance(other, MolecularWeight):
            return NotImplemented
        return bool(self._value == other._value)

    def __hash__(self) -> int:
        """Hash based on class and value only (ignoring config)."""
        return hash((self.__class__.__name__, self._value))
