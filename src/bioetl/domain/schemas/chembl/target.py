"""Pandera schema for ChEMBL Target entity.

Aligned with RULES.md v5.24 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import CHEMBL_ID_PATTERN, TARGET_TYPES

__all__ = [
    "TargetSchema",
]


class TargetSchema(ETLRecordSchema):
    """Target validation schema for Silver layer."""

    # === Primary Key ===
    # tid: Series[int] = pa.Field(
    #     nullable=False, description="Primary key."
    # )
    # Removed tid as it is not in Silver schema. target_id is the PK.

    # === Identifiers ===
    target_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL ID.",
    )

    # === Classification ===
    target_type: Series[str] = pa.Field(
        nullable=False,
        isin=list(TARGET_TYPES),
        description="Target type.",
    )
    # target_parent_type: Optional[Series[str]] = pa.Field(
    #     nullable=True,
    #     isin=["MOLECULAR", "NON-MOLECULAR", "PROTEIN", "UNDEFINED"],
    #     description="Target parent type.",
    # )

    # === Metadata ===
    pref_name: Series[str] = pa.Field(nullable=False, description="Preferred name.")
    taxonomy_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="NCBI Taxonomy ID."
    )
    organism: Series[str] = pa.Field(nullable=False, description="Organism.")
    organism_class: Series[str] | None = pa.Field(
        nullable=True,
        isin=["acellular", "unicellular", "multicellular"],
        description="Organism cellularity classification.",
    )
    species_group_flag: Series[bool] = pa.Field(
        nullable=False,
        coerce=False,
        description="Species group flag.",
    )
    description: Series[str] | None = pa.Field(
        nullable=True, description="Target description."
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

    # === Flattened Component Fields (JSON Arrays) ===
    component_accessions: Series[str] | None = pa.Field(
        nullable=True, description="Canonical JSON array of component accessions."
    )
    component_descriptions: Series[str] | None = pa.Field(
        nullable=True, description="Canonical JSON array of component descriptions."
    )
    primary_component_id: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Primary component ID (first from list).",
    )
    component_ids: Series[str] | None = pa.Field(
        nullable=True, description="Canonical JSON array of component IDs."
    )
    component_types: Series[str] | None = pa.Field(
        nullable=True, description="Canonical JSON array of component types."
    )
    component_relationships: Series[str] | None = pa.Field(
        nullable=True, description="Canonical JSON array of component relationships."
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = False
