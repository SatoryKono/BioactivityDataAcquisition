"""PubChem domain entities.

Contains:
- PubchemMolecule: Domain entity (dataclass) with lineage fields
- PubchemMoleculeRecord: DTO (Pydantic) for type-safe data transfer at boundaries

DTO Design:
- Uses extra='forbid' to detect API changes early
- frozen=True ensures immutability
- Adapters return DTOs, transformers convert to Domain Entities

Deprecated aliases (ADR-024, glossary v2.0):
- Compound → PubchemMolecule
- CompoundRecord → PubchemMoleculeRecord
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.entities.base import BaseEntity

# === Pydantic DTO Model ===


class PubchemMoleculeRecord(BaseModel):
    """Chemical molecule DTO from PubChem.

    Represents a molecule (compound) from PubChem API via pubchempy.
    Required field: cid.
    At least one structural identifier (SMILES/InChI) should be present.

    Note: Renamed from PubChemCompoundRecord to align with Ubiquitous Language
    (ADR-024). 'Molecule' is the canonical term for chemical compounds.

    Example:
        >>> record = PubchemMoleculeRecord(
        ...     cid="2244",
        ...     molecular_formula="C9H8O4",
        ...     canonical_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
        ... )
        >>> record.model_dump()
        {'cid': '2244', 'molecular_formula': 'C9H8O4', ...}
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    cid: str = Field(description="PubChem Compound ID")

    # Molecular properties
    molecular_formula: str | None = Field(default=None, description="Molecular formula")
    molecular_weight: float | None = Field(
        default=None, description="Molecular weight in g/mol"
    )

    # Structure representations
    canonical_smiles: str | None = Field(
        default=None, description="Canonical SMILES (connectivity)"
    )
    isomeric_smiles: str | None = Field(
        default=None, description="Isomeric SMILES (with stereochemistry)"
    )
    inchi: str | None = Field(default=None, description="InChI string")
    inchikey: str | None = Field(default=None, description="InChI Key")

    # Names
    iupac_name: str | None = Field(default=None, description="IUPAC systematic name")

    # Physical/Chemical properties
    charge: int | None = Field(default=None, description="Formal charge")
    complexity: float | None = Field(
        default=None, description="Molecular complexity score"
    )
    h_bond_acceptor_count: int | None = Field(
        default=None, description="H-bond acceptor count"
    )
    h_bond_donor_count: int | None = Field(
        default=None, description="H-bond donor count"
    )
    rotatable_bond_count: int | None = Field(
        default=None, description="Rotatable bond count"
    )

    # Fingerprints
    fingerprint: str | None = Field(default=None, description="PubChem fingerprint")


# === Dataclass Domain Entity ===


@dataclass(frozen=True, kw_only=True)
class PubchemMolecule(BaseEntity):
    """Represents a chemical compound/molecule (PubChem Molecule).

    Domain entity with lineage fields (run_id, content_hash, etc.).
    For DTO without lineage, use PubchemMoleculeRecord.
    """

    cid: str
    molecular_formula: str | None = None
    molecular_weight: float | None = None

    # Structure representations
    canonical_smiles: str | None = None
    isomeric_smiles: str | None = None
    inchi: str | None = None
    inchikey: str | None = None
    iupac_name: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.cid:
            raise ValueError("PubchemMolecule cid is required")

        # Invariant: At least one structural representation should be present
        if not any([self.canonical_smiles, self.isomeric_smiles, self.inchi]):
            raise ValueError(
                "PubchemMolecule must have at least one structural identifier "
                "(SMILES/InChI)"
            )


__all__ = [
    "PubchemMolecule",
    "PubchemMoleculeRecord",
]
# Note: Deprecated aliases (Compound, PubChemCompoundRecord) are provided via __getattr__
# but not listed in __all__ since they are deprecated (ADR-024, glossary v2.0)


# === Deprecated Aliases (ADR-024, glossary v2.0) ===
# These aliases are retained for backward compatibility.
# Use PubchemMolecule and PubchemMoleculeRecord in new code.
#
# Note: `CompoundRecord` is NOT a deprecated PubChem alias because it's
# a valid ChEMBL entity (molecule-document link from /compound_record).
# The original PubChem DTO name was `PubChemCompoundRecord`.


def __getattr__(name: str) -> type:
    """Provide deprecated aliases with warnings.

    Deprecated:
        Compound: Use PubchemMolecule instead.
        PubChemCompoundRecord: Use PubchemMoleculeRecord instead.
    """
    import warnings

    if name == "Compound":
        warnings.warn(
            "Compound is deprecated, use PubchemMolecule instead (ADR-024, glossary v2.0)",
            DeprecationWarning,
            stacklevel=2,
        )
        return PubchemMolecule
    if name == "PubChemCompoundRecord":
        warnings.warn(
            "PubChemCompoundRecord is deprecated, use PubchemMoleculeRecord instead "
            "(ADR-024, glossary v2.0)",
            DeprecationWarning,
            stacklevel=2,
        )
        return PubchemMoleculeRecord
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
