"""ChEMBL Tissue Pipeline.

Fetches tissues from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Tissues (anatomical structures for assay experiments)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLTissuePipeline(BasePipeline):
    """Pipeline for ChEMBL tissue data.

    Tissues are anatomical structures used in assay experiments.
    They have 1:M relationship with Assay (via assay.tissue_chembl_id FK).

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
