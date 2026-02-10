"""Pandera schema for ChEMBL Molecule entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    CHEMBL_ID_PATTERN,
    MAX_PHASE_VALUES,
    MOLECULE_TYPES,
    STRUCTURE_TYPES,
)
from bioetl.domain.validation import (
    INCHI_KEY_REGEX_PATTERN,
    MAX_PUBLICATION_YEAR,
    MIN_PUBLICATION_YEAR,
)


class MoleculeSchema(ETLRecordSchema):
    """Molecule validation schema for Silver layer."""

    # === Primary Key ===
    # molregno: Series[int] = pa.Field(
    #     nullable=False, description="Primary key."
    # )
    # Removed molregno as it is not in Silver schema. molecule_chembl_id is the PK.

    # === Identifiers ===
    molecule_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL ID.",
    )
    structure_standard_inchi_key: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=INCHI_KEY_REGEX_PATTERN,
        description="Standard InChI Key (27 characters, format: XXXX-YYYY-Z).",
    )
    # chebi_id: Optional[Series[int]] = pa.Field(
    #     nullable=True, description="ChEBI ID."
    # )
    # chebi_par_id: Optional[Series[int]] = pa.Field(
    #     nullable=True, description="Parent ChEBI ID."
    # )

    # === Core Properties ===
    pref_name: Series[str] | None = pa.Field(
        nullable=True, description="Preferred name."
    )
    max_phase: Series[float] | None = pa.Field(
        nullable=True,
        isin=list(MAX_PHASE_VALUES),
        description="Maximum clinical phase.",
    )
    structure_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(STRUCTURE_TYPES),
        description="Structure type.",
    )
    molecule_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(MOLECULE_TYPES),
        description="Molecule type.",
    )
    first_approval: Series[int] | None = pa.Field(
        nullable=True, description="Year of first approval."
    )
    # chirality: Optional[Series[int]] = pa.Field(
    #     nullable=True,
    #     isin=[-1, 0, 1, 2],
    #     description="Chirality.",
    # )

    # === Flags ===
    therapeutic_flag: Series[bool] | None = pa.Field(
        nullable=True, description="Therapeutic flag."
    )
    # dosed_ingredient: Optional[Series[int]] = pa.Field(
    #     nullable=True, isin=[0, 1], description="Dosed ingredient flag."
    # )
    oral: Series[bool] | None = pa.Field(
        nullable=True, description="Oral administration flag."
    )
    parenteral: Series[bool] | None = pa.Field(
        nullable=True, description="Parenteral administration flag."
    )
    topical: Series[bool] | None = pa.Field(
        nullable=True, description="Topical administration flag."
    )
    black_box_warning: Series[int] | None = pa.Field(
        nullable=True, isin=[0, 1], description="Black box warning flag."
    )
    natural_product: Series[int] | None = pa.Field(
        nullable=True, isin=[-1, 0, 1], description="Natural product flag."
    )
    first_in_class: Series[int] | None = pa.Field(
        nullable=True, isin=[0, 1], description="First in class flag."
    )
    prodrug: Series[int] | None = pa.Field(
        nullable=True, isin=[0, 1], description="Prodrug flag."
    )
    inorganic_flag: Series[int] | None = pa.Field(
        nullable=True, isin=[0, 1], description="Inorganic flag."
    )
    polymer_flag: Series[int] | None = pa.Field(
        nullable=True, isin=[0, 1], description="Polymer flag."
    )
    withdrawn_flag: Series[bool] | None = pa.Field(
        nullable=True, description="Withdrawn flag."
    )
    # downgraded: Optional[Series[int]] = pa.Field(
    #     nullable=True, isin=[0, 1], description="Downgraded flag."
    # )
    # nomerge: Optional[Series[int]] = pa.Field(
    #     nullable=True, isin=[0, 1], description="No merge flag."
    # )

    # === Other Properties ===
    chirality: Series[int] | None = pa.Field(
        nullable=True,
        isin=[-1, 0, 1, 2],
        description="Chirality flag: -1=unknown, 0=achiral, 1=single, 2=racemic.",
    )
    dosed_ingredient: Series[int] | None = pa.Field(
        nullable=True, isin=[0, 1], description="Dosed ingredient flag."
    )
    availability_type: Series[int] | None = pa.Field(
        nullable=True, isin=[-2, -1, 0, 1, 2], description="Availability type."
    )
    usan_year: Series[int] | None = pa.Field(
        nullable=True,
        ge=MIN_PUBLICATION_YEAR,
        le=MAX_PUBLICATION_YEAR,
        description="USAN approval year.",
    )
    usan_stem: Series[str] | None = pa.Field(
        nullable=True, description="USAN stem name."
    )
    usan_substem: Series[str] | None = pa.Field(
        nullable=True, description="USAN substem name."
    )
    usan_stem_definition: Series[str] | None = pa.Field(
        nullable=True, description="USAN stem definition."
    )
    helm_notation: Series[str] | None = pa.Field(
        nullable=True, description="HELM notation for biopolymers."
    )
    molecule_species: Series[str] | None = pa.Field(
        nullable=True, description="Species for biologics."
    )

    # === Hierarchy Fields (flattened from molecule_hierarchy) ===
    hierarchy_parent_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="Parent molecule ChEMBL ID in hierarchy.",
    )
    hierarchy_active_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="Active molecule ChEMBL ID in hierarchy.",
    )
    hierarchy_child_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="Child molecule ChEMBL ID in hierarchy.",
    )

    # === Property Fields (flattened from molecule_properties) ===
    property_alogp: Series[float] | None = pa.Field(
        nullable=True, description="Calculated ALogP (partition coefficient)."
    )
    property_mw_freebase: Series[float] | None = pa.Field(
        nullable=True, description="Molecular weight of parent compound."
    )
    property_full_mwt: Series[float] | None = pa.Field(
        nullable=True, description="Full molecular weight including salts."
    )
    property_hba: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Hydrogen bond acceptors count."
    )
    property_hbd: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Hydrogen bond donors count."
    )
    property_psa: Series[float] | None = pa.Field(
        nullable=True, ge=0, description="Polar surface area (PSA)."
    )
    property_rtb: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Rotatable bonds count."
    )
    property_ro5_violations: Series[int] | None = pa.Field(
        nullable=True,
        ge=0,
        le=4,
        description="Number of Lipinski rule-of-5 violations.",
    )
    property_heavy_atoms: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Heavy (non-hydrogen) atoms count."
    )
    property_aromatic_rings: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Aromatic rings count."
    )
    property_qed_weighted: Series[float] | None = pa.Field(
        nullable=True, ge=0, le=1, description="Quantitative Estimate of Drug-likeness."
    )
    property_full_molformula: Series[str] | None = pa.Field(
        nullable=True, description="Full molecular formula."
    )
    property_ro3_pass: Series[str] | None = pa.Field(
        nullable=True, isin=["Y", "N"], description="Rule-of-3 compliance (Y/N)."
    )

    # === Structure Fields (flattened from molecule_structures) ===
    canonical_smiles: Series[str] | None = pa.Field(
        nullable=True, description="Canonical SMILES representation."
    )
    standard_inchi: Series[str] | None = pa.Field(
        nullable=True, description="Standard InChI representation."
    )
    inchikey: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=INCHI_KEY_REGEX_PATTERN,
        description="Standard InChI Key (27 characters, XXXX-YYYY-Z format).",
    )

    # === Complex Fields (JSON Strings) ===
    molecule_hierarchy: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of molecule hierarchy."
    )
    molecule_properties: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of molecule properties."
    )
    molecule_structures: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of molecule structures."
    )
    molecule_synonyms: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of molecule synonyms."
    )
    cross_references: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of cross references."
    )
    atc_classifications: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of ATC classifications."
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
