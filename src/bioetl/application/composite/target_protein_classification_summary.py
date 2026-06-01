"""Shared ChEMBL target classification summary exports for composite joins."""

from __future__ import annotations

from bioetl.application.pipelines.chembl.target_protein_classification_summary import (
    MULTIFUNCTIONAL_TARGET_NAME,
    TARGET_PROTEIN_CLASSIFICATION_PIPELINE,
    empty_target_protein_classification_summary,
    summarize_target_protein_classification_dependency,
    summarize_target_protein_classification_rows,
)

__all__ = [
    "MULTIFUNCTIONAL_TARGET_NAME",
    "TARGET_PROTEIN_CLASSIFICATION_PIPELINE",
    "empty_target_protein_classification_summary",
    "summarize_target_protein_classification_dependency",
    "summarize_target_protein_classification_rows",
]
