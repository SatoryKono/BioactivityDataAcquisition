"""Pandera schema for ChEMBL Target entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""
from __future__ import annotations

from typing import Optional

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class TargetSchema(ETLRecordSchema):
    """Target validation schema for Silver layer."""

    # === Primary Key ===
    tid: Series[int] = pa.Field(
        nullable=False, description="Primary key."
    )

    # === Identifiers ===
    target_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL ID.",
    )

    # === Classification ===
    target_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=[
            "SINGLE PROTEIN", "PROTEIN FAMILY", "PROTEIN COMPLEX", "PROTEIN COMPLEX GROUP",
            "SELECTIVITY GROUP", "CHIMERIC PROTEIN", "CELL-LINE", "TISSUE", "ORGANISM",
            "MACROMOLECULE", "SMALL MOLECULE", "LIPID", "METAL", "UNKNOWN",
        ],
        description="Target type.",
    )
    target_parent_type: Optional[Series[str]] = pa.Field(
        nullable=True,
        isin=["MOLECULAR", "NON-MOLECULAR", "PROTEIN", "UNDEFINED"],
        description="Target parent type.",
    )

    # === Metadata ===
    pref_name: Optional[Series[str]] = pa.Field(
        nullable=True, description="Preferred name."
    )
    tax_id: Optional[Series[int]] = pa.Field(
        nullable=True, description="NCBI Taxonomy ID."
    )
    organism: Optional[Series[str]] = pa.Field(
        nullable=True, description="Organism."
    )
    species_group_flag: Optional[Series[int]] = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Species group flag.",
    )
    downgraded: Optional[Series[int]] = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Downgraded flag.",
    )

    class Config:
        """Pandera configuration."""
        strict = True
        ordered = True
        coerce = True
