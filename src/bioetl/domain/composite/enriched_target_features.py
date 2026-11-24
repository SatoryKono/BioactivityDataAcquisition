"""Explicit feature contract for classification after composite target joins.

Historical M columns named ``L1`` and ``L2`` are not the modern ChEMBL
protein-classification fields that share those tokens. Stage-0 records their
provenance as unestablished. ChEMBL ``target_protein_class_name_L*`` values
are release-scoped labels from the protein-classification tree. A shared
name is not a field mapping.
"""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
)

COMPOSITE_CLASSIFICATION_OWNER = "composite.target_classification"
COMPOSITE_CLASSIFICATION_BATCH_ID = "composite-target-classification"

HISTORICAL_M_HIERARCHY_COLUMNS: tuple[str, ...] = ("L1", "L2")
MODERN_CHEMBL_HIERARCHY_COLUMNS: Mapping[str, str] = {
    "L1": "chembl.target_protein_classification.target_protein_class_name_L1",
    "L2": "chembl.target_protein_classification.target_protein_class_name_L2",
}

OPTIONAL_ENRICHED_FEATURES: tuple[str, ...] = (
    "ec",
    "protein_hierarchy",
    "keywords",
    "uniprot_accession",
)


def composite_classification_run_id(run_id: str) -> str:
    """Deterministic occurrence id for one composite classification stage."""
    if not run_id.strip():
        raise ValueError("composite classification requires a run id")
    # The evidence store accepts only path segments of letters, digits, and ._-
    return f"{run_id}.{COMPOSITE_CLASSIFICATION_BATCH_ID}"


def composite_classification_row_id(target_id: str) -> str:
    """Deterministic row occurrence id. The ChEMBL id is not an IUPHAR id."""
    if not target_id.strip():
        raise ValueError("composite classification row requires a target id")
    return f"composite.target:{target_id}"


def hierarchy_fields_are_equivalent(
    historical_column: str,
    modern_column: str,
    *,
    chembl_release: str | None,
) -> bool:
    """Return whether a historical M column is the named modern ChEMBL field.

    The answer stays false. Equivalence needs a release-bound mapping, and
    none is declared for the watched M columns.
    """
    del historical_column, modern_column, chembl_release
    return False


def hierarchy_mapping_records(
    *,
    chembl_release: str | None,
    release_status: str,
) -> tuple[dict[str, object], ...]:
    """Describe the checked M-to-ChEMBL columns without treating names as equal."""
    records: list[dict[str, object]] = []
    for historical in HISTORICAL_M_HIERARCHY_COLUMNS:
        modern = MODERN_CHEMBL_HIERARCHY_COLUMNS[historical]
        record: dict[str, object] = {
            "historical_column": historical,
            "modern_qualified_column": modern,
            "release_status": release_status,
            "equivalent_by_name": hierarchy_fields_are_equivalent(
                historical,
                modern,
                chembl_release=chembl_release,
            ),
        }
        if chembl_release is not None:
            record["chembl_release"] = chembl_release
        records.append(record)
    return tuple(records)


__all__ = [
    "COMPOSITE_CLASSIFICATION_BATCH_ID",
    "COMPOSITE_CLASSIFICATION_OWNER",
    "HISTORICAL_M_HIERARCHY_COLUMNS",
    "MODERN_CHEMBL_HIERARCHY_COLUMNS",
    "OPTIONAL_ENRICHED_FEATURES",
    "TARGET_CLASSIFICATION_DETAIL_FIELDS",
    "TARGET_CLASSIFICATION_FIELDS",
    "composite_classification_row_id",
    "composite_classification_run_id",
    "hierarchy_fields_are_equivalent",
    "hierarchy_mapping_records",
]
