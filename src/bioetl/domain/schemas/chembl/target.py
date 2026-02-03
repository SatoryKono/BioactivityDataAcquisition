"""Pandera schema for ChEMBL Target entity.

Aligned with RULES.md v5.0 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class TargetSchema(ETLRecordSchema):
    """Target validation schema for Silver layer."""

    # === Primary Key ===
    # tid: Series[int] = pa.Field(
    #     nullable=False, description="Primary key."
    # )
    # Removed tid as it is not in Silver schema. target_chembl_id is the PK.

    # === Identifiers ===
    target_chembl_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL ID.",
    )

    # === Classification ===
    target_type: Series[str] | None = pa.Field(
        nullable=True,
        isin=[
            "SINGLE PROTEIN",
            "PROTEIN FAMILY",
            "PROTEIN COMPLEX",
            "PROTEIN COMPLEX GROUP",
            "SELECTIVITY GROUP",
            "CHIMERIC PROTEIN",
            "CELL-LINE",
            "TISSUE",
            "ORGANISM",
            "MACROMOLECULE",
            "SMALL MOLECULE",
            "LIPID",
            "METAL",
            "UNKNOWN",
        ],
        description="Target type.",
    )
    # target_parent_type: Optional[Series[str]] = pa.Field(
    #     nullable=True,
    #     isin=["MOLECULAR", "NON-MOLECULAR", "PROTEIN", "UNDEFINED"],
    #     description="Target parent type.",
    # )

    # === Metadata ===
    pref_name: Series[str] | None = pa.Field(
        nullable=True, description="Preferred name."
    )
    taxonomy_id: Series[int] | None = pa.Field(
        nullable=True, description="NCBI Taxonomy ID. Standardized name (was tax_id)."
    )
    organism: Series[str] | None = pa.Field(nullable=True, description="Organism.")
    species_group_flag: Series[bool] | None = pa.Field(
        nullable=True,
        description="Species group flag.",
    )
    downgraded: Series[bool] | None = pa.Field(
        nullable=True,
        description="Downgraded flag.",
    )

    # === Complex Fields (JSON Strings) ===
    target_components: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of target components."
    )
    cross_references: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of cross references."
    )
    pipeline_stages: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of pipeline stages."
    )
    target_component_synonyms: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of aggregated component synonyms."
    )

    # === Flattened Component Fields (Lists) ===
    # Note: Pandera Series[object] is used for lists, validation is limited
    component_accessions: Series[object] | None = pa.Field(
        nullable=True, description="List of component accessions."
    )
    component_id: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Primary component ID (first from list).",
    )
    component_ids: Series[object] | None = pa.Field(
        nullable=True, description="List of component IDs."
    )
    component_types: Series[object] | None = pa.Field(
        nullable=True, description="List of component types."
    )
    component_relationships: Series[object] | None = pa.Field(
        nullable=True, description="List of component relationships."
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
