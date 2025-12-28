"""Pandera schema for ChEMBL Molecule entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class MoleculeSchema(ETLRecordSchema):
    """Molecule validation schema for Silver/Gold layers."""

    # === Primary Key ===
    molecule_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="Primary key (ChEMBL identifier).",
    )

    # === Core Metadata ===
    pref_name: Optional[Series[str]] = pa.Field(
        nullable=True, description="Preferred name of the molecule."
    )
    molecule_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=["Small molecule", "Protein", "Antibody", "Oligosaccharide", "Oligonucleotide", "Cell", "Unknown"],
        description="Type of the molecule.",
    )
    structure_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=["MOL", "SEQ", "NONE", "BOTH"],
        description="Structure type (MOL file or Sequence).",
    )
    max_phase: Optional[Series[float]] = pa.Field(
        nullable=True,
        isin=[-1, 0, 0.5, 1, 2, 3, 4],
        description="Maximum clinical phase reached.",
    )
    first_approval: Optional[Series[int]] = pa.Field(
        nullable=True,
        ge=1900,
        le=2100,
        description="Year of first approval.",
    )
    chirality: Optional[Series[int]] = pa.Field(
        nullable=True,
        isin=[-1, 0, 1, 2],
        description="Chirality code.",
    )
    prodrug: Optional[Series[int]] = pa.Field(
        nullable=True, description="Prodrug flag (0/1)."
    )
    oral: Optional[Series[bool]] = pa.Field(
        nullable=True, description="Oral administration flag."
    )
    parenteral: Optional[Series[bool]] = pa.Field(
        nullable=True, description="Parenteral administration flag."
    )
    topical: Optional[Series[bool]] = pa.Field(
        nullable=True, description="Topical administration flag."
    )
    black_box_warning: Optional[Series[int]] = pa.Field(
        nullable=True, description="Black box warning flag (0/1)."
    )
    natural_product: Optional[Series[int]] = pa.Field(
        nullable=True, description="Natural product flag (0/1)."
    )
    first_in_class: Optional[Series[int]] = pa.Field(
        nullable=True, description="First in class flag (0/1)."
    )
    inorganic_flag: Optional[Series[int]] = pa.Field(
        nullable=True, description="Inorganic flag (0/1)."
    )
    polymer_flag: Optional[Series[int]] = pa.Field(
        nullable=True, description="Polymer flag (0/1)."
    )
    therapeutic_flag: Optional[Series[bool]] = pa.Field(
        nullable=True, description="Therapeutic flag."
    )
    withdrawn_flag: Optional[Series[bool]] = pa.Field(
        nullable=True, description="Withdrawn flag."
    )

    # === Complex Fields (JSON Strings) ===
    molecule_hierarchy: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of molecule hierarchy."
    )
    molecule_properties: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of molecule properties."
    )
    molecule_structures: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of molecule structures."
    )
    molecule_synonyms: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of molecule synonyms."
    )
    cross_references: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of cross references."
    )
    atc_classifications: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of ATC classifications."
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = False
        coerce = True
