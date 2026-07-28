# pyright: reportMissingSuperCall=false
# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods provided by concrete composition.
"""Chemical structure identifier Value Objects.

Contains validated and normalized InChIKey and SMILES identifiers."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from bioetl.domain.validation import validate_smiles

if TYPE_CHECKING:

    class _ValueObjectBase[ValueT]:
        """Typing-only stand-in for ValueObject under skipped imports."""

        _value: ValueT

        def __init__(self, value: ValueT) -> None: ...

        @property
        def value(self) -> ValueT: ...

else:
    from bioetl.domain.value_objects.base import ValueObject as _ValueObjectBase

__all__ = [
    "SMILES",
    "InChIKey",
]

SMILESNormalizationMode = Literal["soft", "strict"]


class InChIKey(_ValueObjectBase[str]):
    """InChI Key value object.

    InChI Keys are 27-character strings in the format:
    AAAAAAAAAAAAAA-BBBBBBBBBB-Z

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
                "Expected: AAAAAAAAAAAAAA-BBBBBBBBBB-Z (27 chars)"
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


class SMILES(_ValueObjectBase[str]):
    """SMILES notation value object.

    Simplified Molecular-Input Line-Entry System (SMILES) is a string
    notation for describing molecular structure.

    Examples:
    - CC(=O)OC1=CC=CC=C1C(=O)O (aspirin)
    - CN1C=NC2=C1C(=O)N(C(=O)N2C)C (caffeine)

    Invariants:
        - Must be a non-empty string
        - Must satisfy the domain-level basic SMILES syntax contract
        - Normalized by stripping outer whitespace
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
        if not validate_smiles(normalized):
            raise ValueError(f"Invalid SMILES format: {value!r}")

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
    def from_raw(
        cls,
        raw: str | None,
        *,
        is_canonical: bool = False,
        mode: SMILESNormalizationMode = "soft",
    ) -> SMILES | None:
        """Create SMILES from raw string with normalization.

        Args:
            raw: Raw SMILES string or None.
            is_canonical: Whether this is a canonical SMILES.
            mode: ``soft`` returns None for invalid inputs; ``strict`` raises.

        Returns:
            SMILES if valid. In ``soft`` mode returns None when the input is
            empty or invalid.
        """
        _validate_smiles_normalization_mode(mode)
        if _is_blank_smiles(raw):
            return _handle_blank_smiles(mode)
        assert raw is not None
        return _build_smiles_from_raw(
            cls,
            raw,
            is_canonical=is_canonical,
            mode=mode,
        )

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


def _validate_smiles_normalization_mode(mode: SMILESNormalizationMode) -> None:
    """Reject unsupported SMILES normalization modes."""
    if mode in {"soft", "strict"}:
        return
    raise ValueError(f"Unsupported SMILES normalization mode: {mode!r}")


def _is_blank_smiles(raw: str | None) -> bool:
    """Return whether the raw SMILES value is empty after trimming."""
    return raw is None or not raw.strip()


def _handle_blank_smiles(mode: SMILESNormalizationMode) -> SMILES | None:
    """Handle an empty raw SMILES input according to normalization mode."""
    if mode == "soft":
        return None
    raise ValueError("SMILES cannot be empty")


def _build_smiles_from_raw(
    cls: type[SMILES],
    raw: str,
    *,
    is_canonical: bool,
    mode: SMILESNormalizationMode,
) -> SMILES | None:
    """Build a SMILES value object, honoring soft/strict error behavior."""
    try:
        return cls(raw, is_canonical=is_canonical)
    except ValueError:
        if mode == "strict":
            raise
        return None
