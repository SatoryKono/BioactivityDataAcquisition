"""Pandera schema for derived ChEMBL target protein classifications."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema

__all__ = ["TargetProteinClassificationSchema"]


class TargetProteinClassificationSchema(ETLRecordSchema):
    """Derived target-to-protein-classification relation schema."""

    target_id: Series[str] = pa.Field(nullable=False, description="ChEMBL target ID.")
    classification_status: Series[str] = pa.Field(
        nullable=False,
        isin=["resolved", "missing_classification", "quarantined"],
        description="Resolution status for this target classification row.",
    )
    component_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        description="Target component ID that supplied the classification.",
    )
    leaf_id: Series[str] | None = pa.Field(
        nullable=True,
        description="Resolved leaf protein classification ID.",
    )
    path_ids: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical JSON array of root-to-leaf protein class IDs.",
    )
    path_names: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical JSON array of root-to-leaf protein class names.",
    )
    path_labels: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical JSON array of root-to-leaf display labels.",
    )
    depth: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Zero-based depth of the resolved leaf in the hierarchy.",
    )
    root_id: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=1,
        description="Root protein classification ID for the resolved path.",
    )
    is_leaf: Series[bool] | None = pa.Field(
        nullable=True,
        description="Whether the row represents a resolved leaf classification.",
    )
    l1_id: Series[str] | None = pa.Field(
        nullable=True, description="Level 1 protein classification ID."
    )
    l1_name: Series[str] | None = pa.Field(
        nullable=True, description="Level 1 protein classification name."
    )
    l1_desc: Series[str] | None = pa.Field(
        nullable=True, description="Level 1 protein classification description."
    )
    l2_id: Series[str] | None = pa.Field(
        nullable=True, description="Level 2 protein classification ID."
    )
    l2_name: Series[str] | None = pa.Field(
        nullable=True, description="Level 2 protein classification name."
    )
    l2_desc: Series[str] | None = pa.Field(
        nullable=True, description="Level 2 protein classification description."
    )
    l3_id: Series[str] | None = pa.Field(
        nullable=True, description="Level 3 protein classification ID."
    )
    l3_name: Series[str] | None = pa.Field(
        nullable=True, description="Level 3 protein classification name."
    )
    l3_desc: Series[str] | None = pa.Field(
        nullable=True, description="Level 3 protein classification description."
    )
    l4_id: Series[str] | None = pa.Field(
        nullable=True, description="Level 4 protein classification ID."
    )
    l4_name: Series[str] | None = pa.Field(
        nullable=True, description="Level 4 protein classification name."
    )
    l4_desc: Series[str] | None = pa.Field(
        nullable=True, description="Level 4 protein classification description."
    )
    l5_id: Series[str] | None = pa.Field(
        nullable=True, description="Level 5 protein classification ID."
    )
    l5_name: Series[str] | None = pa.Field(
        nullable=True, description="Level 5 protein classification name."
    )
    l5_desc: Series[str] | None = pa.Field(
        nullable=True, description="Level 5 protein classification description."
    )
    dataset_version: Series[str] | None = pa.Field(
        nullable=True,
        description="Version of the local target classification dictionary build.",
    )
    source_url: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical ChEMBL source resource for protein classifications.",
    )
    chembl_release: Series[str] | None = pa.Field(
        nullable=True,
        description="ChEMBL release captured in the local snapshot when available.",
    )
    chembl_api_version: Series[str] | None = pa.Field(
        nullable=True,
        description="ChEMBL API version captured in the local snapshot when available.",
    )
    source_manifest_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=["release_metadata_available", "release_metadata_unavailable"],
        description="Availability status for ChEMBL release/API metadata.",
    )
    source_snapshot_fingerprint: Series[str] | None = pa.Field(
        nullable=True,
        description="SHA-256 fingerprint of local snapshot identifiers.",
    )
    target_snapshot_row_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Source target snapshot row count used to build the relation.",
    )
    target_component_snapshot_row_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Source target_component snapshot row count used to build relation.",
    )
    protein_class_snapshot_row_count: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        ge=0,
        description="Source protein_class snapshot row count used to build relation.",
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = False
        coerce = True
