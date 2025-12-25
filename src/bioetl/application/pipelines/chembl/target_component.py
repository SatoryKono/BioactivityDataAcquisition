"""ChEMBL Target Component Pipeline.

Fetches target components from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Target Components (protein sequences, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Refactored: Uses default_transformer_class for fallback (eliminates __init__ boilerplate).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)


class ChEMBLTargetComponentPipeline(BasePipeline):
    """Pipeline for ChEMBL target component data.

    Transformer is injected via DI from GenericPipelineFactory.
    Falls back to TargetComponentTransformer if not injected.
    """

    default_transformer_class = TargetComponentTransformer

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
