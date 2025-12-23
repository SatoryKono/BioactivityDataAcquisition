"""UniProt pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the UniProt database.
"""

from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer

__all__ = [
    "UniProtProteinPipeline",
    "UniProtProteinTransformer",
]
