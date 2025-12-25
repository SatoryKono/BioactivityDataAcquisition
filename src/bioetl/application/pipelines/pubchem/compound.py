"""PubChem Compound Pipeline Implementation.

Refactored: Uses default_transformer_class for fallback (eliminates __init__ boilerplate).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer


class PubChemCompoundPipeline(BasePipeline):
    """Pipeline for processing PubChem compounds.

    Transformer is injected via DI from GenericPipelineFactory.
    Falls back to PubChemCompoundTransformer if not injected.
    """

    default_transformer_class = PubChemCompoundTransformer

    # transform_bronze_to_silver() is inherited from BasePipeline
