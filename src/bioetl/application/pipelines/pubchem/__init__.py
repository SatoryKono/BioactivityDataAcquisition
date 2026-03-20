"""PubChem pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the PubChem database.

Main Components:
- PubChemCompoundPipeline: Pipeline for compound data
- PubChemCompoundTransformer: Transformer for compound data

Naming note:
- Application/public pipeline surface intentionally keeps `Compound` to match the
  stable external identifier `pubchem_compound`.
- Canonical domain entity naming still uses `PubchemMolecule`.
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer


class PubChemCompoundPipeline(BasePipeline):
    """Pipeline for processing PubChem compounds.

    Transformer is injected via DI from GenericPipelineFactory.
    """


PIPELINES = (PubChemCompoundPipeline,)

__all__ = [
    "PubChemCompoundPipeline",
    "PubChemCompoundTransformer",
]
