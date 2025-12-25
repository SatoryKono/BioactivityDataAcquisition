"""ChEMBL Document Pipeline.

Fetches scientific documents from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Scientific Documents (publications, patents)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Refactored: Uses default_transformer_class for fallback (eliminates __init__ boilerplate).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.document_transformer import DocumentTransformer


class ChEMBLDocumentPipeline(BasePipeline):
    """Pipeline for ChEMBL document data.

    Transformer is injected via DI from GenericPipelineFactory.
    Falls back to DocumentTransformer if not injected.
    """

    default_transformer_class = DocumentTransformer

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
