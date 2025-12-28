"""Pandera schema for ChEMBL Molecule entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class MoleculeSchema(ETLRecordSchema):
    """Molecule validation schema for Silver layer."""

    # === Primary Key ===
    molregno: Series[int] = pa.Field(
        nullable=False, description="Primary key."
    )

    # === Identifiers ===
    molecule_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL ID.",
    )
    chebi_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="ChEBI ID."
    )
    chebi_par_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="Parent ChEBI ID."
    )
    structure_key: Optional[Series[str]] = pa.Field(
        nullable=True, description="InChI Key."
    )

    # === Core Properties ===
    pref_name: Optional[Series[str]] = pa.Field(
        nullable=True, description="Preferred name."
    )
    max_phase: Optional[Series[float]] = pa.Field(
        nullable=True,
        isin=[-1, 0.5, 1, 2, 3, 4],
        description="Maximum clinical phase.",
    )
    structure_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=["MOL", "SEQ", "BOTH", "NONE"],
        description="Structure type.",
    )
    molecule_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=[
            "Small molecule", "Inorganic small molecule", "Polymeric small molecule",
            "Antibody", "Antibody drug conjugate", "Protein", "Oligonucleotide",
            "Oligosaccharide", "Cell", "Enzyme", "Unknown", "Unclassified",
        ],
        description="Molecule type.",
    )
    first_approval: Optional[Series[int]] = pa.Field(
        nullable=True, description="Year of first approval."
    )
    chirality: Optional[Series[int]] = pa.Field(
        nullable=True,
        isin=[-1, 0, 1, 2],
        description="Chirality.",
    )

    # === Flags ===
    therapeutic_flag: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Therapeutic flag."
    )
    dosed_ingredient: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Dosed ingredient flag."
    )
    oral: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Oral administration flag."
    )
    parenteral: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Parenteral administration flag."
    )
    topical: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Topical administration flag."
    )
    black_box_warning: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Black box warning flag."
    )
    natural_product: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[-1, 0, 1], description="Natural product flag."
    )
    first_in_class: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="First in class flag."
    )
    prodrug: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Prodrug flag."
    )
    inorganic_flag: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Inorganic flag."
    )
    polymer_flag: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Polymer flag."
    )
    withdrawn_flag: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Withdrawn flag."
    )
    downgraded: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="Downgraded flag."
    )
    nomerge: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1], description="No merge flag."
    )

    # === Other Properties ===
    availability_type: Optional[Series[int]] = pa.Field(
        nullable=True, isin=[0, 1, 2], description="Availability type."
    )
    usan_year: Optional[Series[int]] = pa.Field(
        nullable=True, description="USAN year."
    )
    usan_stem: Optional[Series[str]] = pa.Field(
        nullable=True, description="USAN stem."
    )
    usan_substem: Optional[Series[str]] = pa.Field(
        nullable=True, description="USAN substem."
    )
    usan_stem_definition: Optional[Series[str]] = pa.Field(
        nullable=True, description="USAN stem definition."
    )
    indication_class: Optional[Series[str]] = pa.Field(
        nullable=True, description="Indication class."
    )
    withdrawn_year: Optional[Series[int]] = pa.Field(
        nullable=True, description="Withdrawn year."
    )
    withdrawn_country: Optional[Series[str]] = pa.Field(
        nullable=True, description="Withdrawn country."
    )
    withdrawn_reason: Optional[Series[str]] = pa.Field(
        nullable=True, description="Withdrawn reason."
    )
    withdrawn_class: Optional[Series[str]] = pa.Field(
        nullable=True, description="Withdrawn class."
    )
    downgrade_reason: Optional[Series[str]] = pa.Field(
        nullable=True, description="Downgrade reason."
    )
    replacement_mrn: Optional[Series[int]] = pa.Field(
        nullable=True, description="Replacement molregno."
    )
    nomerge_reason: Optional[Series[str]] = pa.Field(
        nullable=True, description="No merge reason."
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
