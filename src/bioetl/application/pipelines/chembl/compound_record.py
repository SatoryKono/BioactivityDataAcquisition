"""ChEMBL Compound Record Pipeline.

Fetches compound records from ChEMBL database and processes through
Bronze -> Silver -> Gold layers.

Entity: Compound Records (links molecules to documents with original names)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLCompoundRecordPipeline(BasePipeline):
    """Pipeline for ChEMBL compound record data.

    Compound records link molecules to documents and contain the original
    compound name as it appears in the publication.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
