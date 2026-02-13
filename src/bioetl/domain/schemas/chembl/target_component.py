"""Pandera schema for ChEMBL Target Component entity.

Aligned with TargetComponent entity and TargetComponentTransformer output.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class TargetComponentSchema(ETLRecordSchema):
    """Target Component validation schema for Silver layer."""

    # === Primary Key ===
    component_id: Series[int] = pa.Field(
        nullable=False, description="Component ID (primary key)."
    )

    # === Core Metadata ===
    accession: Series[str] | None = pa.Field(
        nullable=True, description="UniProt accession."
    )
    component_type: Series[str] | None = pa.Field(
        nullable=True, description="Component type (PROTEIN, DNA, RNA, etc.)."
    )
    description: Series[str] | None = pa.Field(
        nullable=True, description="Component description."
    )
    organism: Series[str] | None = pa.Field(
        nullable=True, description="Source organism."
    )
    taxonomy_id: Series[float] | None = pa.Field(
        nullable=True, description="NCBI Taxonomy ID (float for nullable int)."
    )

    # === Complex Fields (JSON Strings) ===
    target_component_synonyms: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of component synonyms."
    )
    target_component_xrefs: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of cross references."
    )
    protein_classifications: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of protein classifications (forensic)."
    )

    # === Flattened Fields ===
    protein_classification_id: Series[float] | None = pa.Field(
        nullable=True,
        coerce=True,
        description="Primary protein classification ID (first from list).",
    )
    protein_classification_ids: Series[object] | None = pa.Field(  # type: ignore[type-var]
        nullable=True, description="List of protein classification IDs."
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
