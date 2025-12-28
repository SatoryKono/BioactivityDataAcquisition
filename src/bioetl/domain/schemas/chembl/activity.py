"""Pandera schema for ChEMBL Activity entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class ActivitySchema(ETLRecordSchema):
    """Activity validation schema for Silver/Gold layers."""

    # === Primary Key ===
    activity_id: Series[int] = pa.Field(
        nullable=False, ge=1, description="Primary key (integer identifier)."
    )

    # === Foreign Keys ===
    assay_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to Assay entity.",
    )
    molecule_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to Molecule entity.",
    )
    target_chembl_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to Target entity.",
    )
    document_chembl_id: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to Document entity.",
    )
    record_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="Foreign key to compound_record."
    )
    src_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="Source ID."
    )
    toid: Optional[Series[int]] = pa.Field(
        nullable=True, description="Test Occasion ID."
    )

    # === Standardized Values ===
    standard_relation: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=["=", "<", "<=", ">", ">="],
        description="Standardized operator.",
    )
    standard_value: Optional[Series[float]] = pa.Field(
        nullable=True, ge=0, description="Standardized value."
    )
    standard_units: Optional[Series[str]] = pa.Field(
        nullable=True, description="Standardized units (e.g., nM, uM)."
    )
    standard_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        # Common types, list can be extended based on data analysis
        isin=["IC50", "EC50", "Ki", "Kd", "AC50", "GI50", "Potency", "Inhibition", "% Inhibition"],
        description="Standardized measurement type.",
    )
    standard_flag: Optional[Series[bool]] = pa.Field(
        nullable=True, description="Standardization flag (0 or 1)."
    )
    standard_text_value: Optional[Series[str]] = pa.Field(
        nullable=True, description="Standardized text value."
    )
    standard_upper_value: Optional[Series[float]] = pa.Field(
        nullable=True, description="Standardized upper value for ranges."
    )

    # === Derived Metrics ===
    pchembl_value: Optional[Series[float]] = pa.Field(
        nullable=True,
        ge=0,
        le=14,  # Typical range, can be relaxed if needed
        description="-log10 of molar activity.",
    )

    # === Original Values ===
    type: Optional[Series[str]] = pa.Field(
        nullable=True, description="Original measurement type."
    )
    relation: Optional[Series[str]] = pa.Field(
        nullable=True, description="Original operator."
    )
    value: Optional[Series[float]] = pa.Field(
        nullable=True, description="Original value."
    )
    units: Optional[Series[str]] = pa.Field(
        nullable=True, description="Original units."
    )
    text_value: Optional[Series[str]] = pa.Field(
        nullable=True, description="Original text value."
    )
    upper_value: Optional[Series[float]] = pa.Field(
        nullable=True, description="Original upper value for ranges."
    )

    # === Comments & Quality ===
    data_validity_comment: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=[
            "Potential missing data",
            "Potential author error",
            "Manually validated",
            "Potential transcription error",
            "Outside typical range",
            "Non standard unit for type",
            "Author confirmed error",
        ],
        description="Data quality comment.",
    )
    activity_comment: Optional[Series[str]] = pa.Field(
        nullable=True, description="General activity comment."
    )
    potential_duplicate: Optional[Series[bool]] = pa.Field(
        nullable=True, description="Flag indicating a potential duplicate record."
    )

    # === Ontologies ===
    bao_endpoint: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^BAO:\d+$",
        description="BioAssay Ontology endpoint ID.",
    )
    uo_units: Optional[Series[str]] = pa.Field(
        nullable=True,
        str_matches=r"^UO:\d+$",
        description="Units Ontology ID.",
    )
    qudt_units: Optional[Series[str]] = pa.Field(
        nullable=True, description="QUDT unit identifier."
    )

    # === Flattened Fields (from JSON) ===
    # Ligand Efficiency
    ligand_efficiency_bei: Optional[Series[float]] = pa.Field(nullable=True)
    ligand_efficiency_le: Optional[Series[float]] = pa.Field(nullable=True)
    ligand_efficiency_lle: Optional[Series[float]] = pa.Field(nullable=True)
    ligand_efficiency_sei: Optional[Series[float]] = pa.Field(nullable=True)

    # Action Type
    action_type_action_type: Optional[Series[str]] = pa.Field(nullable=True)
    action_type_description: Optional[Series[str]] = pa.Field(nullable=True)
    action_type_parent_type: Optional[Series[str]] = pa.Field(nullable=True)

    # Activity Properties (JSON string)
    activity_properties: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of activity properties."
    )

    # === Additional Fields from Silver Schema ===
    canonical_smiles: Optional[Series[str]] = pa.Field(nullable=True)
    molecule_pref_name: Optional[Series[str]] = pa.Field(nullable=True)
    parent_molecule_chembl_id: Optional[Series[str]] = pa.Field(nullable=True)
    target_pref_name: Optional[Series[str]] = pa.Field(nullable=True)
    target_organism: Optional[Series[str]] = pa.Field(nullable=True)
    target_tax_id: Optional[Series[str]] = pa.Field(nullable=True)
    assay_type: Optional[Series[str]] = pa.Field(nullable=True)
    assay_description: Optional[Series[str]] = pa.Field(nullable=True)
    assay_variant_accession: Optional[Series[str]] = pa.Field(nullable=True)
    assay_variant_mutation: Optional[Series[str]] = pa.Field(nullable=True)
    bao_format: Optional[Series[str]] = pa.Field(nullable=True)
    bao_label: Optional[Series[str]] = pa.Field(nullable=True)
    document_journal: Optional[Series[str]] = pa.Field(nullable=True)
    document_year: Optional[Series[float]] = pa.Field(nullable=True)

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = False  # Allow arbitrary column order
        coerce = True
