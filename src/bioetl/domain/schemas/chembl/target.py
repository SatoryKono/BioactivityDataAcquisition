"""Pandera schema for ChEMBL Target entity.

Aligned with RULES.md v5.24 and ChEMBL 34 schema.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.normalization.rules import normalize_boolean
from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    CHEMBL_ID_PATTERN,
    TARGET_ORGANISM_CLASSES,
    TARGET_TYPES,
)

__all__ = [
    "TargetSchema",
]


class TargetSchema(ETLRecordSchema):
    """Target validation schema for Silver layer."""

    @staticmethod
    def _normalize_nullable_boolean_series(series: pd.Series) -> pd.Series:
        """Normalize sparse bool-like values without masking invalid lexemes."""
        normalized_values: list[object] = []
        can_cast_to_boolean = True

        for value in series.tolist():
            if pd.isna(value):
                normalized_values.append(pd.NA)
                continue

            normalized = normalize_boolean(value)
            if normalized is None:
                normalized_values.append(value)
                can_cast_to_boolean = False
                continue

            normalized_values.append(normalized)

        if can_cast_to_boolean:
            return pd.Series(
                normalized_values,
                index=series.index,
                dtype=pd.BooleanDtype(),
            )

        return pd.Series(normalized_values, index=series.index, dtype="object")

    @pa.dataframe_parser
    def _normalize_sparse_nullable_booleans(
        cls,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """Normalize nullable bool-like target fields before dtype validation."""
        if "downgraded" not in dataframe.columns:
            return dataframe

        normalized = dataframe.copy()
        normalized["downgraded"] = cls._normalize_nullable_boolean_series(
            normalized["downgraded"]
        )
        return normalized

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
        isin=list(TARGET_ORGANISM_CLASSES),
        description="Organism cellularity classification.",
    )
    species_group_flag: Series[bool] = pa.Field(
        nullable=False,
        coerce=False,
        description="Species group flag.",
    )
    target_description: Series[str] | None = pa.Field(
        nullable=True, description="Target description."
    )
    downgraded: Series[pd.BooleanDtype] | None = pa.Field(
        nullable=True,
        coerce=False,
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
    target_protein_synonyms: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited UNIPROT-derived target synonyms or unknown.",
    )
    target_gene_synonyms: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited gene-symbol-derived target synonyms or unknown.",
    )
    target_ec_numbers: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited EC-number-derived target synonyms or unknown.",
    )
    target_xref_pdb_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited PDB/PDBe xref IDs or unknown.",
    )
    target_xref_go_component: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited GO cellular component xref names or unknown.",
    )
    target_xref_go_function: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited GO molecular function xref names or unknown.",
    )
    target_xref_go_process: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited GO biological process xref names or unknown.",
    )
    target_xref_reactome_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Pipe-delimited Reactome xref IDs or unknown.",
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
