"""PubChem pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the PubChem database.

Main Components:
- PubChemCompoundPipeline: Pipeline for compound data
- PubChemCompoundTransformer: Transformer for compound data
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer


class PubChemCompoundPipeline(BasePipeline):
    """Pipeline for processing PubChem compounds.

    Transformer is injected via DI from GenericPipelineFactory.
    """


__all__ = [
    "PubChemCompoundPipeline",
    "PubChemCompoundTransformer",
]
