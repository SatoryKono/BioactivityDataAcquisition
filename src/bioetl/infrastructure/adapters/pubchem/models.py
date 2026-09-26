# mypy: disable-error-code="misc"
"""Pydantic models for PubChem API responses.

These models provide type-safe parsing and validation for PubChem data.
They are infrastructure-layer models (not domain models) for normalized adapter output.

Note: PubChem uses pubchempy library which returns Compound/Substance objects.
These models validate the dictionary representation returned by adapter methods.

See RULES.md §8.2 for JSON response modeling guidelines.
"""

from __future__ import annotations

__all__ = [
    "PubChemAssayRecord",
    "PubChemBioactivityRecord",
    "PubChemSubstanceRecord",
    "PubchemMoleculeApiRecord",
    "PubchemMoleculeDetailRecord",
]


from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.pubchem._detail_models import (
    PubChemBioactivityRecord,
    PubchemMoleculeDetailRecord,
)


class PubchemMoleculeApiRecord(BaseModel):
    """Normalized molecule record from PubChem API (infrastructure model).

    This is the infrastructure-layer API response model with extra='ignore'
    and cid as int. NOT the same as the domain entity PubchemMoleculeRecord
    (domain/entities/pubchem.py) which uses extra='forbid', cid as str,
    and has 35+ fields vs ~15 here.

    Represents data extracted from a pubchempy.Compound object
    via the adapter's _compound_to_dict method.

    Note: Renamed from PubChemCompoundRecord per ADR-024.
    'Molecule' is the canonical term for chemical compounds.
    Renamed from PubchemMoleculeRecord to PubchemMoleculeApiRecord
    to resolve naming collision with the domain entity.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    cid: int = Field(description="PubChem Compound ID")

    # Molecular Properties
    molecular_formula: str | None = Field(default=None, description="Molecular formula")
    molecular_weight: float | None = Field(
        default=None, description="Molecular weight in g/mol"
    )

    # Structure Representations
    canonical_smiles: str | None = Field(
        default=None, description="Canonical SMILES (from connectivity_smiles)"
    )
    isomeric_smiles: str | None = Field(
        default=None, description="Isomeric SMILES (from smiles property)"
    )
    inchi: str | None = Field(default=None, description="InChI string")
    inchikey: str | None = Field(default=None, description="InChI Key")

    # Names
    iupac_name: str | None = Field(default=None, description="IUPAC systematic name")

    # Physical/Chemical Properties
    charge: int | None = Field(default=None, description="Formal charge")
    complexity: float | None = Field(
        default=None, description="Molecular complexity score"
    )
    h_bond_acceptor_count: int | None = Field(
        default=None, description="Number of hydrogen bond acceptors"
    )
    h_bond_donor_count: int | None = Field(
        default=None, description="Number of hydrogen bond donors"
    )
    rotatable_bond_count: int | None = Field(
        default=None, description="Number of rotatable bonds"
    )

    # Fingerprints
    fingerprint: str | None = Field(default=None, description="PubChem fingerprint")


class PubChemSubstanceRecord(BaseModel):
    """Normalized substance record from PubChem.

    Represents data extracted from a pubchempy.Substance object
    via the adapter's _substance_to_dict method.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    sid: int = Field(description="PubChem Substance ID")

    # Source Information
    source_name: str | None = Field(
        default=None, description="Name of the depositing source"
    )
    source_id: str | None = Field(
        default=None, description="ID from the source database"
    )

    # Associated Compounds
    cids: list[int] | None = Field(
        default_factory=list, description="List of standardized compound IDs"
    )

    # Names
    synonyms: list[str] | None = Field(
        default_factory=list, description="List of substance synonyms"
    )


class PubChemAssayRecord(BaseModel):
    """Normalized assay record from PubChem.

    Represents data from PubChem BioAssay.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    aid: int | None = Field(default=None, description="PubChem Assay ID")

    # Core Fields
    name: str | None = Field(default=None, description="Assay name")
    description: str | None = Field(default=None, description="Assay description")
    protocol: str | None = Field(default=None, description="Assay protocol")
    target: JsonDict | None = (  # Any: untyped API JSON record
        Field(  # Any: nested API JSON has heterogeneous values
            default=None, description="Target information"
        )
    )


# === Record Type Mapping ===

# Mapping from entity type to record model (keys match PubChem entity types, not Ubiquitous Language)
PUBCHEM_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "compound": PubchemMoleculeApiRecord,  # ADR-024: Molecule is canonical
    "molecule": PubchemMoleculeApiRecord,  # Canonical alias
    "substance": PubChemSubstanceRecord,
    "assay": PubChemAssayRecord,
}
