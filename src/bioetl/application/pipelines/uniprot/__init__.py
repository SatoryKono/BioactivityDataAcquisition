"""UniProt pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the UniProt database.

Main Components:
- UniProtProteinPipeline: Pipeline for protein data
- UniProtProteinTransformer: Transformer for protein data
"""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer

__all__ = [
    "UniProtProteinPipeline",
    "UniProtProteinTransformer",
]
