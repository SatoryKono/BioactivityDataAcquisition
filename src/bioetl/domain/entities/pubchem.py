"""PubChem domain entities.

Contains:
- PubchemMolecule: Domain entity (canonical name, dataclass) with lineage fields
- Compound: Deprecated alias for PubchemMolecule (backward compatibility)
- PubChemCompoundRecord: DTO (Pydantic) for type-safe data transfer at boundaries

DTO Design:
- Uses extra='forbid' to detect API changes early
- frozen=True ensures immutability
- Adapters return DTOs, transformers convert to Domain Entities

.. versionchanged:: 2.0.0
    Compound renamed to PubchemMolecule for Ubiquitous Language alignment.
    The deprecated Compound alias remains for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.entities.base import BaseEntity

# === Pydantic DTO Model ===


class PubChemCompoundRecord(BaseModel):
    """Chemical compound DTO from PubChem.

    Represents a compound from PubChem API via pubchempy.
    Required field: cid.
    At least one structural identifier (SMILES/InChI) should be present.

    Note: Named PubChemCompoundRecord to avoid conflict with
    ChEMBL's CompoundRecord (which links molecules to documents).

    Example:
        >>> record = PubChemCompoundRecord(
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
    """Represents a chemical compound/molecule (PubChem Compound).

    Canonical name for PubChem's Compound entity, aligned with Ubiquitous Language.
    Domain entity with lineage fields (run_id, content_hash, etc.).
    For DTO without lineage, use PubChemCompoundRecord.

    .. versionadded:: 2.0.0
        Replaces :class:`Compound` as the canonical entity name.
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


# === Deprecated Aliases (backward compatibility) ===

# Compound is a deprecated alias for PubchemMolecule.
# Use PubchemMolecule in new code for Ubiquitous Language alignment.
#
# .. deprecated:: 2.0.0
#     Use :class:`PubchemMolecule` instead.
#
# Migration:
#     # Before
#     from bioetl.domain.entities import Compound
#
#     # After
#     from bioetl.domain.entities import PubchemMolecule
Compound = PubchemMolecule


__all__ = ["Compound", "PubChemCompoundRecord", "PubchemMolecule"]
