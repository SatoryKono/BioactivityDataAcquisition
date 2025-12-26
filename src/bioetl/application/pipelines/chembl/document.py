"""ChEMBL Document Pipeline.

Fetches scientific documents from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Scientific Documents (publications, patents)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLDocumentPipeline(BasePipeline):
    """Pipeline for ChEMBL document data.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
