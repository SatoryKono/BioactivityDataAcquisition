"""Pandera schema for ChEMBL Target entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class TargetSchema(ETLRecordSchema):
    """Target validation schema for Silver/Gold layers."""

    # === Primary Key ===
    target_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="Primary key (ChEMBL identifier).",
    )

    # === Core Metadata ===
    pref_name: Optional[Series[str]] = pa.Field(
        nullable=True, description="Preferred name of the target."
    )
    target_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=[
            "SINGLE PROTEIN",
            "PROTEIN FAMILY",
            "PROTEIN COMPLEX",
            "PROTEIN COMPLEX GROUP",
            "SELECTIVITY GROUP",
            "CELL-LINE",
            "TISSUE",
            "ORGANISM",
            "ADMET",
            "SUBCELLULAR",
            "UNKNOWN",
            "NUCLEIC-ACID",
            "SMALL MOLECULE",
            "METAL",
        ],
        description="Type of the target.",
    )
    organism: Optional[Series[str]] = pa.Field(
        nullable=True, description="Organism of the target."
    )
    tax_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="Taxonomy ID of the organism."
    )
    species_group_flag: Optional[Series[bool]] = pa.Field(
        nullable=True, description="Species group flag."
    )

    # === Complex Fields (JSON Strings) ===
    target_components: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of target components."
    )
    cross_references: Optional[Series[str]] = pa.Field(
        nullable=True, description="JSON string of cross references."
    )

    # === Flattened Component Fields (Lists) ===
    # Note: Pandera Series[object] is used for lists, validation is limited
    component_accessions: Optional[Series[object]] = pa.Field(
        nullable=True, description="List of component accessions."
    )
    component_ids: Optional[Series[object]] = pa.Field(
        nullable=True, description="List of component IDs."
    )
    component_types: Optional[Series[object]] = pa.Field(
        nullable=True, description="List of component types."
    )
    component_relationships: Optional[Series[object]] = pa.Field(
        nullable=True, description="List of component relationships."
    )
    component_descriptions: Optional[Series[object]] = pa.Field(
        nullable=True, description="List of component descriptions."
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = False
        coerce = True
