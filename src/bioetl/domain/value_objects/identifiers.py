"""Identifier Value Objects for BioETL domain.

Contains Value Objects for database identifiers:
- ChemblId: ChEMBL database identifiers (CHEMBL123)
- UniProtId: UniProt accession numbers (P12345)
- PubChemCid: PubChem Compound IDs

For publication identifiers (DOI, PubMedId), see the `publications` module.
For chemical structure identifiers (InChIKey, SMILES) and metadata
(PublicationYear), see the `chemical` module.

These Value Objects encapsulate validation and normalization rules.
"""

from __future__ import annotations

import re

from bioetl.domain.value_objects.base import ValueObject

__all__ = [
    "ChemblId",
    "PubChemCid",
    "UniProtId",
]


class ChemblId(ValueObject[str]):
    """ChEMBL identifier for molecules, targets, assays, documents, etc.

    Format: CHEMBL followed by a positive integer.
    Examples: CHEMBL25, CHEMBL1234567, CHEMBL941

    Invariants:
        - Starts with "CHEMBL" (case-insensitive, normalized to uppercase)
        - Followed by a positive integer
        - No leading zeros in the numeric part
    """

    __slots__ = ()
    _value: str
    _PATTERN = re.compile(r"^CHEMBL(\d+)$", re.IGNORECASE)

    def _validate(self, value: str) -> str:
        """Validate and normalize ChEMBL ID.

        Args:
            value: Raw ChEMBL ID string.

        Returns:
            Normalized uppercase ChEMBL ID.

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"ChemblId must be str, got {type(value).__name__}")

        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("ChemblId cannot be empty")

        match = self._PATTERN.match(normalized)
        if not match:
            raise ValueError(
                f"Invalid ChEMBL ID format: {value!r}. Expected: CHEMBL<number>"
            )

        numeric_part = int(match.group(1))
        if numeric_part <= 0:
            raise ValueError(f"ChEMBL ID number must be positive: {value!r}")

        # Normalize to remove leading zeros
        return f"CHEMBL{numeric_part}"

    @property
    def numeric_id(self) -> int:
        """Get the numeric part of the ChEMBL ID.

        Returns:
            Integer portion of the identifier (e.g., 25 for CHEMBL25).
        """
        return int(self._value[6:])

    @classmethod
    def from_raw(cls, raw: str | None) -> ChemblId | None:
        """Create ChemblId from raw string with normalization.

        Args:
            raw: Raw ChEMBL ID string or None.

        Returns:
            ChemblId if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class UniProtId(ValueObject[str]):
    """UniProt accession number.

    UniProt accession numbers follow specific patterns:
    - Primary format: [OPQ][0-9][A-Z0-9]{3}[0-9] (e.g., P12345, Q9Y6K9)
    - Extended format: [A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2} (e.g., A0A1B2C3D4)

    See: https://www.uniprot.org/help/accession_numbers

    Invariants:
        - Matches UniProt accession pattern
        - Normalized to uppercase
    """

    __slots__ = ()
    _value: str

    # Primary accession pattern (6 characters)
    _PRIMARY_PATTERN = re.compile(r"^[OPQ]\d[A-Z\d]{3}\d$")

    # Secondary accession pattern for other letters (6 or 10 characters)
    _SECONDARY_PATTERN = re.compile(r"^[A-NR-Z]\d([A-Z][A-Z\d]{2}\d){1,2}$")

    def _validate_format(self, normalized: str) -> bool:
        """Check if normalized string matches UniProt format."""
        return bool(
            self._PRIMARY_PATTERN.match(normalized)
            or self._SECONDARY_PATTERN.match(normalized)
        )

    def _validate(self, value: str) -> str:
        """Validate and normalize UniProt accession.

        Args:
            value: Raw UniProt accession string.

        Returns:
            Normalized uppercase UniProt accession.

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"UniProtId must be str, got {type(value).__name__}")

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("UniProtId cannot be empty")

        if len(normalized) not in (6, 10):
            raise ValueError(
                f"Invalid UniProt accession length: {value!r}. "
                f"Expected 6 or 10 characters."
            )

        if not self._validate_format(normalized):
            raise ValueError(f"Invalid UniProt accession format: {value!r}")
        return normalized

    @property
    def is_primary_format(self) -> bool:
        """Check if this is a primary (6-character) accession.

        Primary format accessions (e.g., P12345) are 6 characters.
        Extended format accessions (e.g., A0A1B2C3D4) are 10 characters.

        Returns:
            True if primary format (6 chars), False if extended (10 chars).
        """
        return len(self._value) == 6

    @classmethod
    def from_raw(cls, raw: str | None) -> UniProtId | None:
        """Create UniProtId from raw string with normalization.

        Args:
            raw: Raw UniProt accession string or None.

        Returns:
            UniProtId if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class PubChemCid(ValueObject[int]):
    """PubChem Compound Identifier (CID).

    A positive integer uniquely identifying a compound in PubChem.
    Examples: 2244 (aspirin), 5988 (caffeine)

    Invariants:
        - Must be a positive integer
        - Cannot exceed reasonable bounds (< 10^11)
    """

    __slots__ = ()
    _value: int

    _MAX_CID = 100_000_000_000  # Reasonable upper bound

    def _coerce_to_int(self, value: int | str) -> int:
        """Coerce value to int, raising ValueError on failure."""
        if isinstance(value, bool):
            raise ValueError(f"PubChemCid must be int, got {type(value).__name__}")
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                raise ValueError(f"Invalid PubChem CID: {value!r}") from None
        raise ValueError(f"PubChemCid must be int, got {type(value).__name__}")

    def _validate(self, value: int | str) -> int:
        """Validate PubChem CID.

        Args:
            value: Raw CID value.

        Returns:
            Validated CID.

        Raises:
            ValueError: If CID is invalid.
        """
        int_value = self._coerce_to_int(value)
        if int_value <= 0:
            raise ValueError(f"PubChem CID must be positive: {int_value}")
        if int_value >= self._MAX_CID:
            raise ValueError(f"PubChem CID too large: {int_value}")
        return int_value

    @classmethod
    def from_raw(cls, raw: int | str | None) -> PubChemCid | None:
        """Create PubChemCid from raw value with normalization.

        Args:
            raw: Raw CID integer, string, or None.

        Returns:
            PubChemCid if valid, None if input is None, empty, or invalid.
        """
        if raw is None:
            return None
        if isinstance(raw, str) and not raw.strip():
            return None
        try:
            # int() is idempotent on ints, converts str to int
            return cls(int(raw))
        except ValueError:
            return None
