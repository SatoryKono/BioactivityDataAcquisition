# basedpyright residual burn-down (shrink-only product surface).
"""Compound identifier Value Objects for BioETL domain.

Contains Value Objects for compound identification across sources:
- CompoundId: Universal compound identifier (supports ChEMBL, PubChem)
- AssayId: Bioassay identifier (ChEMBL format)

These Value Objects encapsulate source-specific validation and normalization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Self, override

from bioetl.domain.value_objects.base import ValueObject
from bioetl.domain.value_objects.identifiers import ChemblId, PubChemCid

__all__ = [
    "AssayId",
    "CompoundId",
    "CompoundIdUnion",
    "CompoundSource",
]


class CompoundSource(StrEnum):
    """Source database for compound identifiers.

    Represents the origin database of a compound identifier.
    """

    CHEMBL = "chembl"
    PUBCHEM = "pubchem"


@dataclass(frozen=True, slots=True)
class CompoundId:
    """Universal compound identifier supporting multiple sources.

    A Value Object that encapsulates compound identifiers from
    different databases (ChEMBL, PubChem) with source-specific
    validation.

    Invariants:
        - value is validated according to source format
        - source is one of the supported databases
        - immutable after creation

    Examples:
        >>> cid = CompoundId.from_chembl("CHEMBL25")
        >>> cid.source
        <CompoundSource.CHEMBL: 'chembl'>
        >>> cid.value
        'CHEMBL25'
        >>> cid = CompoundId.from_pubchem(2244)
        >>> cid.source
        <CompoundSource.PUBCHEM: 'pubchem'>
    """

    value: str
    source: CompoundSource
    _validated_id: ChemblId | PubChemCid | None = None

    def __post_init__(self) -> None:
        """Validate compound identifier based on source."""
        validated_id: ChemblId | PubChemCid
        if self.source == CompoundSource.CHEMBL:
            validated_id = ChemblId(self.value)
            object.__setattr__(self, "_validated_id", validated_id)
            # Normalize value to canonical form
            object.__setattr__(self, "value", validated_id.value)
        elif self.source == CompoundSource.PUBCHEM:
            # For PubChem, value should be numeric string
            try:
                cid_int = int(self.value)
                validated_id = PubChemCid(cid_int)
                object.__setattr__(self, "_validated_id", validated_id)
                object.__setattr__(self, "value", str(validated_id.value))
            except ValueError as e:
                raise ValueError(f"Invalid PubChem CID: {self.value}") from e
        else:
            raise ValueError(f"Unsupported compound source: {self.source!r}")

    @classmethod
    def from_chembl(cls, chembl_id: str) -> Self:
        """Create CompoundId from ChEMBL identifier.

        Args:
            chembl_id: ChEMBL ID string (e.g., "CHEMBL25").

        Returns:
            CompoundId with CHEMBL source.

        Raises:
            ValueError: If ChEMBL ID format is invalid.
        """
        return cls(value=chembl_id, source=CompoundSource.CHEMBL)

    @classmethod
    def from_pubchem(cls, cid: int | str) -> Self:
        """Create CompoundId from PubChem CID.

        Args:
            cid: PubChem compound ID (integer or numeric string).

        Returns:
            CompoundId with PUBCHEM source.

        Raises:
            ValueError: If CID is invalid.
        """
        return cls(value=str(cid), source=CompoundSource.PUBCHEM)

    @classmethod
    def from_raw(
        cls,
        value: str | int,
        source: Literal["chembl", "pubchem"] | CompoundSource,
    ) -> Self:
        """Create CompoundId from raw value and source string.

        Args:
            value: Identifier value.
            source: Source database name or enum.

        Returns:
            Validated CompoundId.

        Raises:
            ValueError: If source or value is invalid.
        """
        if isinstance(source, str):
            source = CompoundSource(source.lower())

        return cls(value=str(value), source=source)

    @property
    def is_chembl(self) -> bool:
        """Check if this is a ChEMBL identifier."""
        return self.source == CompoundSource.CHEMBL

    @property
    def is_pubchem(self) -> bool:
        """Check if this is a PubChem identifier."""
        return self.source == CompoundSource.PUBCHEM

    @property
    def numeric_id(self) -> int:
        """Get the numeric part of the identifier.

        For ChEMBL: extracts number from CHEMBLNNN
        For PubChem: returns the CID as integer

        Returns:
            Numeric identifier value.
        """
        if self._validated_id is None:
            raise ValueError("Identifier was not properly validated")

        if isinstance(self._validated_id, ChemblId):
            return self._validated_id.numeric_id
        return self._validated_id.value

    @property
    def as_chembl_id(self) -> ChemblId | None:
        """Get as ChemblId if source is ChEMBL.

        Returns:
            ChemblId or None if source is not ChEMBL.
        """
        if self.is_chembl and isinstance(self._validated_id, ChemblId):
            return self._validated_id
        return None

    @property
    def as_pubchem_cid(self) -> PubChemCid | None:
        """Get as PubChemCid if source is PubChem.

        Returns:
            PubChemCid or None if source is not PubChem.
        """
        if self.is_pubchem and isinstance(self._validated_id, PubChemCid):
            return self._validated_id
        return None

    @property
    def as_pubchem_molecule_id(self) -> PubChemCid | None:
        """Backward-compatible alias for PubChem CID accessor."""
        return self.as_pubchem_cid

    @override
    def __str__(self) -> str:
        """Return string representation with source prefix."""
        return f"{self.source.value}:{self.value}"

    @override
    def __eq__(self, other: object) -> bool:
        """Compare equality by value and source."""
        if not isinstance(other, CompoundId):
            return NotImplemented
        return self.value == other.value and self.source == other.source

    @override
    def __hash__(self) -> int:
        """Hash based on value and source."""
        return hash((self.value, self.source))


class AssayId(ValueObject[str]):
    """ChEMBL assay identifier.

    Assay IDs in ChEMBL follow the same format as other ChEMBL IDs
    (CHEMBL followed by a positive integer), but represent bioassays
    rather than compounds.

    Format: CHEMBL followed by a positive integer.
    Examples: CHEMBL1217643, CHEMBL829394

    Invariants:
        - Follows ChEMBL ID format (CHEMBLNNN)
        - Normalized to uppercase
        - No leading zeros in numeric part
    """

    __slots__ = ("_chembl_id",)
    _value: str
    _chembl_id: ChemblId

    def __init__(self, value: str) -> None:  # pyright: ignore[reportMissingSuperCall]
        """Create AssayId with validated value.

        Args:
            value: Raw assay ID string.

        Raises:
            ValueError: If format is invalid.
        """
        # Validate using ChemblId
        chembl_id = ChemblId(value)
        object.__setattr__(self, "_chembl_id", chembl_id)
        object.__setattr__(self, "_value", chembl_id.value)

    @override
    def _validate(self, value: str) -> str:
        """Validate using ChemblId validation.

        This method exists for compatibility with ValueObject base class
        but actual validation is done in __init__.
        """
        return ChemblId(value).value

    @classmethod
    def from_string(cls, value: str | None) -> AssayId | None:
        """Create from string, returning None if input is None or empty.

        Args:
            value: Assay ID string.

        Returns:
            AssayId or None if input is None/empty.

        Raises:
            ValueError: If format is invalid.
        """
        if value is None or not value.strip():
            return None
        return cls(value)

    @property
    def numeric_id(self) -> int:
        """Get the numeric part of the assay ID.

        Returns:
            Integer portion of the identifier (e.g., 1217643 for CHEMBL1217643).
        """
        return self._chembl_id.numeric_id

    @property
    def as_chembl_id(self) -> ChemblId:
        """Get the underlying ChemblId.

        Returns:
            ChemblId representation of this assay ID.
        """
        return self._chembl_id


# Type alias for compound identifier union
CompoundIdUnion = ChemblId | PubChemCid | CompoundId
