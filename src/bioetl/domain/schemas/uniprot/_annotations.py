# mypy: disable-error-code="misc"
"""Functional annotations and biochemical property fields.

Part of UniprotTargetSchema split to comply with LOC limits.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

__all__ = [
    "UniprotAnnotationSchema",
]


class UniprotAnnotationSchema(pa.DataFrameModel):  # Pandera typing limitation
    """Functional annotations, cofactors and biophysicochemical properties."""

    # === Functional Annotation ===
    function_comment: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of function descriptions"
    )
    catalytic_activity: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of catalytic reactions"
    )
    activity_regulation: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of activity regulation info"
    )
    subunit: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of subunit structure info"
    )
    pathway: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of pathways"
    )
    subcellular_location: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of subcellular locations"
    )
    tissue_specificity: Series[str] | None = pa.Field(
        nullable=True, description="Tissue expression pattern"
    )
    alternative_products: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of alternative splicing/isoforms"
    )
    alternative_products_raw_json: Series[str] | None = pa.Field(
        nullable=True,
        description="Raw provider JSON for alternative-products comments",
    )
    alternative_products_canonical_json: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical JSON companion for alternative-products comments",
    )
    disease_involvement: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of disease associations"
    )
    pharmaceutical_use: Series[str] | None = pa.Field(
        nullable=True, description="Pharmaceutical applications"
    )
    similarity_comment: Series[str] | None = pa.Field(
        nullable=True, description="Family and domain information"
    )
    caution: Series[str] | None = pa.Field(
        nullable=True, description="Warnings about this entry"
    )

    # === Biochemical Properties ===
    cofactors: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of cofactors with name and ChEBI ID",
    )
    cofactors_raw_json: Series[str] | None = pa.Field(
        nullable=True,
        description="Raw provider JSON for cofactor comments",
    )
    cofactors_canonical_json: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical JSON companion for cofactor comments",
    )
    biophysicochemical_properties: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON object with pH/temp optima, kinetics, redox potential",
    )
    biophysicochemical_properties_raw_json: Series[str] | None = pa.Field(
        nullable=True,
        description="Raw provider JSON for biophysicochemical-property comments",
    )
    biophysicochemical_properties_canonical_json: Series[str] | None = pa.Field(
        nullable=True,
        description=(
            "Canonical JSON companion for biophysicochemical-property comments"
        ),
    )
    induction: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of gene expression induction conditions",
    )
