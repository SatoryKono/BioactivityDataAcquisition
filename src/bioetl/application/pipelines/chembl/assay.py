"""ChEMBL Assay Pipeline.

Fetches assay definitions from ChEMBL database and processes them through
Bronze → Silver → Gold layers.

Entity: Bioassay definitions (binding, functional, ADMET, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Refactored: Uses default_transformer_class for fallback (eliminates __init__ boilerplate).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer


class ChEMBLAssayPipeline(BasePipeline):
    """Pipeline for ChEMBL assay data.

    Transformer is injected via DI from GenericPipelineFactory.
    Falls back to AssayTransformer if not injected.
    """

    default_transformer_class = AssayTransformer

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
