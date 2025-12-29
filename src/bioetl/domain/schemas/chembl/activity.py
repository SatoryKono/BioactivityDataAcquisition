"""Pandera schema for ChEMBL Activity entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class ActivitySchema(ETLRecordSchema):
    """Activity validation schema for Silver layer."""

    # === Primary Key ===
    activity_id: Series[str] = pa.Field(nullable=False, description="Primary key.")

    # === Foreign Keys ===
    assay_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to assay.",
    )
    molecule_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to molecule.",
    )
    target_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to target.",
    )
    document_chembl_id: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^CHEMBL\d+$",
        description="Foreign key to document.",
    )

    # === Standardized Values ===
    standard_relation: Series[str] | None = pa.Field(
        nullable=True,
        isin=["=", "<", "<=", ">", ">="],
        description="Standardized operator.",
    )
    standard_value: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Standardized value.",
    )
    standard_units: Series[str] | None = pa.Field(
        nullable=True, description="Standardized units."
    )
    standard_type: Series[str] | None = pa.Field(
        nullable=True,
        # Expanded list to avoid false positives on valid data
        isin=[
            "IC50",
            "EC50",
            "Ki",
            "Kd",
            "AC50",
            "GI50",
            "Potency",
            "Inhibition",
            "% Inhibition",
            "Activity",
            "Ratio",
            "ED50",
            "ID50",
        ],
        description="Standardized measurement type.",
    )
    standard_flag: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Standardization flag.",
    )

    # === Derived Metrics ===
    pchembl_value: Series[float] | None = pa.Field(
        nullable=True,
        ge=0,
        le=14,
        description="-log10 of molar activity.",
    )

    # === Comments & Quality ===
    data_validity_comment: Series[str] | None = pa.Field(
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
    activity_comment: Series[str] | None = pa.Field(
        nullable=True, description="Textual comment."
    )
    potential_duplicate: Series[int] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Duplicate flag.",
    )

    # === Ontologies ===
    bao_endpoint: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^BAO:\d+$",
        description="BAO ID.",
    )
    uo_units: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^UO:\d+$",
        description="Units Ontology ID.",
    )
    qudt_units: Series[str] | None = pa.Field(nullable=True, description="QUDT unit.")

    # === Original Values & Other Fields ===
    src_id: Series[int] | None = pa.Field(nullable=True, description="Source ID.")
    record_id: Series[int] | None = pa.Field(
        nullable=True, description="FK to compound_record."
    )
    type: Series[str] | None = pa.Field(nullable=True, description="Original type.")
    relation: Series[str] | None = pa.Field(
        nullable=True, description="Original operator."
    )
    value: Series[float] | None = pa.Field(nullable=True, description="Original value.")
    units: Series[str] | None = pa.Field(nullable=True, description="Original units.")
    text_value: Series[str] | None = pa.Field(nullable=True, description="Text value.")
    standard_text_value: Series[str] | None = pa.Field(
        nullable=True, description="Standardized text value."
    )
    upper_value: Series[float] | None = pa.Field(
        nullable=True, description="Upper bound."
    )
    standard_upper_value: Series[float] | None = pa.Field(
        nullable=True, description="Standardized upper bound."
    )
    toid: Series[int] | None = pa.Field(nullable=True, description="Test Occasion ID.")
    # manual_curation_flag: Optional[Series[int]] = pa.Field(
    #     nullable=True,
    #     isin=[0, 1],
    #     description="Manual curation flag.",
    # )
    # original_activity_id: Optional[Series[int]] = pa.Field(
    #     nullable=True, description="Original activity ID."
    # )
    # ridx: Optional[Series[str]] = pa.Field(
    #     nullable=True, description="Record index."
    # )

    # === Flattened Fields (from JSON) ===
    ligand_efficiency_bei: Series[float] | None = pa.Field(nullable=True)
    ligand_efficiency_le: Series[float] | None = pa.Field(nullable=True)
    ligand_efficiency_lle: Series[float] | None = pa.Field(nullable=True)
    ligand_efficiency_sei: Series[float] | None = pa.Field(nullable=True)

    action_type_action_type: Series[str] | None = pa.Field(nullable=True)
    action_type_description: Series[str] | None = pa.Field(nullable=True)
    action_type_parent_type: Series[str] | None = pa.Field(nullable=True)

    activity_properties: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of activity properties."
    )

    # === Additional Fields from Silver Schema ===
    canonical_smiles: Series[str] | None = pa.Field(nullable=True)
    molecule_pref_name: Series[str] | None = pa.Field(nullable=True)
    parent_molecule_chembl_id: Series[str] | None = pa.Field(nullable=True)
    target_pref_name: Series[str] | None = pa.Field(nullable=True)
    target_organism: Series[str] | None = pa.Field(nullable=True)
    target_tax_id: Series[str] | None = pa.Field(nullable=True)
    assay_type: Series[str] | None = pa.Field(nullable=True)
    assay_description: Series[str] | None = pa.Field(nullable=True)
    assay_variant_accession: Series[str] | None = pa.Field(nullable=True)
    assay_variant_mutation: Series[str] | None = pa.Field(nullable=True)
    bao_format: Series[str] | None = pa.Field(nullable=True)
    bao_label: Series[str] | None = pa.Field(nullable=True)
    document_journal: Series[str] | None = pa.Field(nullable=True)
    document_year: Series[float] | None = pa.Field(nullable=True)

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
