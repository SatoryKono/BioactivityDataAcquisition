"""Shared activity schema for Delta write performance measurements."""

from __future__ import annotations

import pyarrow as pa


def create_activity_schema() -> pa.Schema:
    """Return the synthetic activity schema used by Delta performance tests."""
    return pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("molecule_id", pa.string()),
            pa.field("assay_id", pa.string()),
            pa.field("target_id", pa.string()),
            pa.field("standard_value", pa.float64()),
            pa.field("standard_units", pa.string()),
            pa.field("pchembl_value", pa.float64()),
            pa.field("canonical_smiles", pa.string()),
            pa.field("content_hash", pa.string()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.timestamp("us")),
        ]
    )
