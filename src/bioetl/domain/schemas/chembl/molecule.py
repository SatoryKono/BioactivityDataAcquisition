# pyright: reportIncompatibleVariableOverride=false
# Pandera/ETL nested Config override pattern (PD2-7).
"""Pandera schema for ChEMBL Molecule entity.

Aligned with RULES.md v5.24 and ChEMBL 34 schema.
RF-NORM-06: Nullable int strategy — pd.Int64Dtype for physicochemical counts.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    CHEMBL_ID_PATTERN,
    MAX_PHASE_VALUES,
    MOLECULE_TYPES,
    RO3_PASS_VALUES,
    STRUCTURE_TYPES,
)
from bioetl.domain.validation import (
    INCHI_KEY_REGEX_PATTERN,
    MAX_PUBLICATION_YEAR,
    MIN_PUBLICATION_YEAR,
)

__all__ = [
    "MoleculeSchema",
]


class MoleculeSchema(ETLRecordSchema):
    """Molecule validation schema for Silver layer."""

    # === Primary Key ===
    # `molecule_id` is the Silver-layer primary key; legacy `molregno` is omitted.

    # === Identifiers ===
    molecule_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="Canonical molecule ID (ChEMBL ID).",
    )

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
    molecule_type: Series[str] = pa.Field(
        nullable=False,
        isin=list(MOLECULE_TYPES),
        description="Molecule type.",
    )
    first_approval: Series[float] | None = pa.Field(
        nullable=True, description="Year of first approval (float for nullable int)."
    )

    # === Flags ===
    therapeutic_flag: Series[bool] | None = pa.Field(
        nullable=True, description="Therapeutic flag."
    )
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
        nullable=True, isin=[-1, 0, 1], description="First in class flag (-1=unknown)."
    )
    prodrug: Series[int] | None = pa.Field(
        nullable=True, isin=[-1, 0, 1], description="Prodrug flag (-1=unknown)."
    )
    inorganic_flag: Series[int] | None = pa.Field(
        nullable=True, isin=[-1, 0, 1], description="Inorganic flag (-1=unknown)."
    )
    polymer_flag: Series[int] | None = pa.Field(
        nullable=True, isin=[0, 1], description="Polymer flag."
    )
    withdrawn_flag: Series[bool] | None = pa.Field(
        nullable=True, description="Withdrawn flag."
    )

    # === Other Properties ===
    chirality: Series[int] | None = pa.Field(
        nullable=True,
        isin=[-1, 0, 1, 2],
        description="Chirality flag: -1=unknown, 0=achiral, 1=single, 2=racemic.",
    )
    dosed_ingredient: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, isin=[0, 1], description="Dosed ingredient flag."
    )
    availability_type: Series[float] | None = pa.Field(
        nullable=True,
        isin=[-2, -1, 0, 1, 2],
        description="Availability type (float for nullable int).",
    )
    usan_year: Series[float] | None = pa.Field(
        nullable=True,
        ge=MIN_PUBLICATION_YEAR,
        le=MAX_PUBLICATION_YEAR,
        description="USAN approval year (float for nullable int).",
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

    # === Property Fields (canonical alias names, unified for Gold) ===
    logp: Series[float] | None = pa.Field(
        nullable=True, description="Partition coefficient (ALogP/XlogP)."
    )
    logp_method: Series[str] | None = pa.Field(
        nullable=True,
        isin=["alogp", "xlogp"],
        description="Source method for logp.",
    )
    mw_freebase: Series[float] | None = pa.Field(
        nullable=True, description="Molecular weight of parent compound."
    )
    molecular_weight: Series[float] | None = pa.Field(
        nullable=True, description="Full molecular weight including salts."
    )
    hba_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, ge=0, description="Hydrogen bond acceptors count."
    )
    hbd_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, ge=0, description="Hydrogen bond donors count."
    )
    polar_surface_area: Series[float] | None = pa.Field(
        nullable=True, ge=0, description="Polar surface area (PSA/tPSA)."
    )
    rotatable_bond_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, ge=0, description="Rotatable bonds count."
    )
    ro5_violation_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=0,
        le=4,
        description="Number of Lipinski rule-of-5 violations.",
    )
    heavy_atom_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, ge=0, description="Heavy (non-hydrogen) atoms count."
    )
    aromatic_ring_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, ge=0, description="Aromatic rings count."
    )
    qed_score: Series[float] | None = pa.Field(
        nullable=True, ge=0, le=1, description="Quantitative Estimate of Drug-likeness."
    )
    molecular_formula: Series[str] | None = pa.Field(
        nullable=True, description="Full molecular formula."
    )
    ro3_pass: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(RO3_PASS_VALUES),
        description="Rule-of-3 compliance (Y/N).",
    )

    # === Structure Fields (flattened from molecule_structures) ===
    canonical_smiles: Series[str] | None = pa.Field(
        nullable=True, description="Canonical SMILES representation."
    )
    standard_inchi: Series[str] | None = pa.Field(
        nullable=True, description="Standard InChI representation."
    )
    inchi_key: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=INCHI_KEY_REGEX_PATTERN,
        description="Standard InChI Key (27 characters, NNNN-YYYY-Z format).",
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
