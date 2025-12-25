"""ChEMBL Target Pipeline.

Fetches biological targets from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Biological Targets (proteins, complexes, organisms)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Refactored: Uses default_transformer_class for fallback (eliminates __init__ boilerplate).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer


class ChEMBLTargetPipeline(BasePipeline):
    """Pipeline for ChEMBL target data.

    Transformer is injected via DI from GenericPipelineFactory.
    Falls back to TargetTransformer if not injected.
    """

    default_transformer_class = TargetTransformer

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
