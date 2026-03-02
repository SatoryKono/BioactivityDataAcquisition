"""Concrete pipeline implementations.

This package provides pipelines for extracting and processing data from
various bioinformatics data sources.

Main Components:
- GenericPipeline: Universal pipeline class for all provider/entity combinations
- Provider-specific pipelines: ChEMBL, PubChem, UniProt, PubMed
- Provider-specific transformers: Implement Bronze→Silver transformation logic

Usage:
    # Direct instantiation (for testing)
    from bioetl.application.pipelines.generic import GenericPipeline
    pipeline = GenericPipeline.create(...)

    # Provider-specific pipelines
    from bioetl.application.pipelines.chembl import ChEMBLActivityPipeline
"""

from __future__ import annotations

from bioetl.application.pipelines.generic import GenericPipeline

__all__ = [
    "GenericPipeline",
]
