"""UniProt pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the UniProt database.

Main Components:
- UniProtProteinPipeline: Pipeline for protein data
- UniProtProteinTransformer: Transformer for protein data
- IDMappingTransformer: Transformer for ChEMBL → UniProt ID mapping
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.uniprot.idmapping_transformer import (
    IDMappingTransformer,
)
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer


class UniProtProteinPipeline(BasePipeline):
    """Pipeline for processing UniProt proteins.

    Transformer is injected via DI from GenericPipelineFactory.
    """

__all__ = [
    "IDMappingTransformer",
    "UniProtProteinPipeline",
    "UniProtProteinTransformer",
]
