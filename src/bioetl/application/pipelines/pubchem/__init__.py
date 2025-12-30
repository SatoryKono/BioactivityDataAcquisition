"""PubChem pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the PubChem database.

Main Components:
- PubChemCompoundTransformer: Transformer for compound data
- PubChemCompoundPipeline: Deprecated alias (use GenericPipeline)
"""

from __future__ import annotations

from bioetl.application.pipelines.compat import PubChemCompoundPipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer

__all__ = [
    "PubChemCompoundPipeline",
    "PubChemCompoundTransformer",
]
