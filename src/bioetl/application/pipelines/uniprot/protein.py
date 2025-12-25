"""UniProt Protein Pipeline Implementation.

Refactored: Uses default_transformer_class for fallback (eliminates __init__ boilerplate).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer


class UniProtProteinPipeline(BasePipeline):
    """Pipeline for processing UniProt proteins.

    Transformer is injected via DI from GenericPipelineFactory.
    Falls back to UniProtProteinTransformer if not injected.
    """

    default_transformer_class = UniProtProteinTransformer

    # transform_bronze_to_silver() is inherited from BasePipeline
