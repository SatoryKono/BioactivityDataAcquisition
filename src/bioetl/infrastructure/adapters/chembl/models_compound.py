# mypy: disable-error-code="misc"
"""ChEMBL molecule/compound endpoint models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.chembl.models_common import ChemblPageMeta

__all__ = [
    "ChemblMoleculeRecord",
    "ChemblMoleculeResponse",
    "MoleculeHierarchy",
    "MoleculeProperties",
    "MoleculeStructures",
]


class MoleculeHierarchy(BaseModel):
    """Molecule hierarchy information."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    molecule_chembl_id: str | None = Field(default=None)
    parent_chembl_id: str | None = Field(default=None)
    active_chembl_id: str | None = Field(default=None)


class MoleculeProperties(BaseModel):
    """Molecule calculated properties."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    alogp: float | None = Field(default=None, description="ALogP value")
    aromatic_rings: int | None = Field(default=None)
    cx_logd: float | None = Field(default=None)
    cx_logp: float | None = Field(default=None)
    cx_most_apka: float | None = Field(default=None)
    cx_most_bpka: float | None = Field(default=None)
    full_molformula: str | None = Field(default=None)
    full_mwt: float | None = Field(default=None)
    hba: int | None = Field(default=None, description="H-bond acceptors")
    hba_lipinski: int | None = Field(default=None)
    hbd: int | None = Field(default=None, description="H-bond donors")
    hbd_lipinski: int | None = Field(default=None)
    heavy_atoms: int | None = Field(default=None)
    molecular_species: str | None = Field(default=None)
    mw_freebase: float | None = Field(default=None)
    mw_monoisotopic: float | None = Field(default=None)
    np_likeness_score: float | None = Field(default=None)
    num_lipinski_ro5_violations: int | None = Field(default=None)
    num_ro5_violations: int | None = Field(default=None)
    psa: float | None = Field(default=None, description="Polar surface area")
    qed_weighted: float | None = Field(default=None)
    ro3_pass: str | None = Field(default=None)
    rtb: int | None = Field(default=None, description="Rotatable bonds")


class MoleculeStructures(BaseModel):
    """Molecule structure representations."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    canonical_smiles: str | None = Field(default=None)
    molfile: str | None = Field(default=None)
    standard_inchi: str | None = Field(default=None)
    standard_inchi_key: str | None = Field(default=None)


class ChemblMoleculeRecord(BaseModel):
    """Individual molecule record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    molecule_chembl_id: str = Field(description="ChEMBL ID of the molecule")
    pref_name: str | None = Field(default=None, description="Preferred name")
    max_phase: float | None = Field(default=None, description="Maximum clinical phase")
    structure_type: str | None = Field(default=None, description="Structure type")
    molecule_type: str | None = Field(default=None, description="Molecule type")
    first_approval: int | None = Field(
        default=None, description="Year of first approval"
    )
    therapeutic_flag: bool | None = Field(default=None)
    oral: bool | None = Field(default=None)
    parenteral: bool | None = Field(default=None)
    topical: bool | None = Field(default=None)
    black_box_warning: int | None = Field(default=None)
    natural_product: int | None = Field(default=None)
    first_in_class: int | None = Field(default=None)
    prodrug: int | None = Field(default=None)
    inorganic_flag: int | None = Field(default=None)
    polymer_flag: int | None = Field(default=None)
    withdrawn_flag: bool | None = Field(default=None)
    chirality: int | None = Field(default=None)
    availability_type: int | None = Field(default=None)
    molecule_hierarchy: MoleculeHierarchy | None = Field(default=None)
    molecule_properties: MoleculeProperties | None = Field(default=None)
    molecule_structures: MoleculeStructures | None = Field(default=None)
    molecule_synonyms: list[JsonDict] | None = (  # Any: untyped API JSON record
        Field(  # Any: nested API JSON has heterogeneous values
            default_factory=list
        )
    )  # Any: nested ChEMBL JSON with provider-specific schema
    cross_references: list[JsonDict] | None = (  # Any: untyped API JSON record
        Field(  # Any: nested API JSON has heterogeneous values
            default_factory=list
        )
    )  # Any: nested ChEMBL JSON with provider-specific schema
    atc_classifications: list[str] | None = Field(default_factory=list)
    usan_year: int | None = Field(default=None)
    usan_stem: str | None = Field(default=None)
    usan_substem: str | None = Field(default=None)
    usan_stem_definition: str | None = Field(default=None)
    indication_class: str | None = Field(default=None)
    withdrawn_year: int | None = Field(default=None)
    withdrawn_country: str | None = Field(default=None)
    withdrawn_reason: str | None = Field(default=None)
    withdrawn_class: str | None = Field(default=None)


class ChemblMoleculeResponse(BaseModel):
    """Complete ChEMBL Molecule API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    molecules: list[ChemblMoleculeRecord] = Field(
        default_factory=list, description="List of molecule records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description="Pagination metadata"
    )
