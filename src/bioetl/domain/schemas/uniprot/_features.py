# mypy: disable-error-code="misc,untyped-decorator"
"""Sequence features, keywords, PTMs and counts.

Part of UniprotTargetSchema split to comply with LOC limits.
"""

from __future__ import annotations

from typing import cast

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

__all__ = [
    "UniprotFeatureSchema",
]

class UniprotFeatureSchema(pa.DataFrameModel):  # Pandera typing limitation
    """Sequence features, keywords, PTMs, isoforms and counts."""

    # === Features & Keywords ===
    features_json: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of all sequence features"
    )
    domains: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of protein domain features"
    )
    binding_sites: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of binding site features"
    )
    active_sites: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of active site features"
    )
    keywords: Series[str] | None = pa.Field(
        nullable=True, description="JSON array of UniProt keywords"
    )

    # === Structural Features ===
    topology: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of topological domain features (TOPO_DOM)",
    )
    transmembrane: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of transmembrane regions (TRANSMEM)",
    )
    intramembrane: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of intramembrane regions (INTRAMEM)",
    )
    signal_peptide: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of signal peptide features (SIGNAL)",
    )
    propeptide: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of propeptide features (PROPEP)",
    )

    # === PTM Features ===
    glycosylation: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of glycosylation sites (CARBOHYD)",
    )
    lipidation: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of lipidation sites (LIPID)",
    )
    disulfide_bond: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of disulfide bonds (DISULFID)",
    )
    modified_residue: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of all modified residues (MOD_RES)",
    )
    phosphorylation: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of phosphorylation sites",
    )
    acetylation: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of acetylation sites",
    )
    ubiquitination: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of ubiquitination sites",
    )

    # === Isoform Details ===
    isoform_names: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of isoform names",
    )
    isoform_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of isoform IDs (e.g., P12345-2)",
    )
    isoform_synonyms: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of isoform synonyms",
    )

    # === Reaction Data ===
    reactions: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of reaction names from catalytic activity",
    )
    reaction_ec_numbers: Series[str] | None = pa.Field(
        nullable=True,
        description="JSON array of EC numbers from catalytic activity reactions",
    )

    # === Counts ===
    cross_reference_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of database cross-references"
    )

    @pa.check("cross_reference_count", name="cross_reference_count_non_negative")
    def _check_cross_reference_count(
        cls, series: Series[pd.Int64Dtype]
    ) -> Series[bool]:
        """Validate cross-reference count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    feature_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of sequence features"
    )

    @pa.check("feature_count", name="feature_count_non_negative")
    def _check_feature_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate feature count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    keyword_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of keywords"
    )

    @pa.check("keyword_count", name="keyword_count_non_negative")
    def _check_keyword_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate keyword count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    publication_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of publications"
    )

    @pa.check("publication_count", name="publication_count_non_negative")
    def _check_publication_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate publication count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))

    isoform_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True, description="Number of isoforms"
    )

    @pa.check("isoform_count", name="isoform_count_non_negative")
    def _check_isoform_count(cls, series: Series[pd.Int64Dtype]) -> Series[bool]:
        """Validate isoform count is non-negative."""
        return cast(Series[bool], series.isna() | (series >= 0))
