# mypy: disable-error-code="misc"
"""Extended PubChem molecule/detail and bioactivity record models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict

__all__ = [
    "PubChemBioactivityRecord",
    "PubchemMoleculeDetailRecord",
]


class PubchemMoleculeDetailRecord(BaseModel):
    """Extended molecule record with additional computed properties.

    Used when fetching detailed compound information from PubChem PUG REST API.

    Note: Renamed from PubChemCompoundDetailRecord per ADR-024.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    cid: int = Field(description="PubChem Compound ID")

    # Basic Properties (from PubchemMoleculeApiRecord)
    molecular_formula: str | None = Field(default=None)
    molecular_weight: float | None = Field(default=None)
    canonical_smiles: str | None = Field(default=None)
    isomeric_smiles: str | None = Field(default=None)
    inchi: str | None = Field(default=None)
    inchikey: str | None = Field(default=None)
    iupac_name: str | None = Field(default=None)
    charge: int | None = Field(default=None)

    # Extended Properties
    xlogp: float | None = Field(
        default=None, description="XLogP3 partition coefficient"
    )
    exact_mass: float | None = Field(
        default=None, description="Exact monoisotopic mass"
    )
    monoisotopic_mass: float | None = Field(
        default=None, description="Monoisotopic mass"
    )
    tpsa: float | None = Field(
        default=None, description="Topological polar surface area"
    )
    heavy_atom_count: int | None = Field(
        default=None, description="Number of heavy (non-hydrogen) atoms"
    )
    atom_stereo_count: int | None = Field(
        default=None, description="Number of stereocenters"
    )
    defined_atom_stereo_count: int | None = Field(
        default=None, description="Number of defined stereocenters"
    )
    undefined_atom_stereo_count: int | None = Field(
        default=None, description="Number of undefined stereocenters"
    )
    bond_stereo_count: int | None = Field(
        default=None, description="Number of stereogenic bonds"
    )
    covalent_unit_count: int | None = Field(
        default=None, description="Number of covalently bonded units"
    )

    # Identifiers
    cactvs_fingerprint: str | None = Field(
        default=None, description="CACTVS fingerprint"
    )

    # Synonyms
    synonyms: list[str] | None = Field(
        default_factory=list, description="Common names and synonyms"
    )


class PubChemBioactivityRecord(BaseModel):
    """Bioactivity data from PubChem BioAssay.

    Represents activity data for a compound-assay pair.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # IDs
    cid: int | None = Field(default=None, description="Compound ID")
    sid: int | None = Field(default=None, description="Substance ID")
    aid: int | None = Field(default=None, description="Assay ID")

    # Activity Outcome
    activity_outcome: str | None = Field(
        default=None, description="Activity outcome (Active, Inactive, etc.)"
    )
    activity_score: float | None = Field(default=None, description="Activity score")

    # Target Info
    target_gi: int | None = Field(default=None, description="Target GI number")
    target_name: str | None = Field(default=None, description="Target name")

    # Activity Values
    activity_values: list[JsonDict] | None = Field(
        default_factory=list, description="List of activity measurements"
    )
