"""Composition facade for protein-classification source manifests (#11250)."""

from __future__ import annotations

from bioetl.infrastructure.adapters.chembl.protein_classification_source_manifest import (
    source_manifest,
    with_source_manifest,
)

__all__ = ["source_manifest", "with_source_manifest"]
