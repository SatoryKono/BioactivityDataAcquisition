"""ChEMBL Document Term Pipeline.

Fetches document terms from ChEMBL database and processes through
Bronze -> Silver -> Gold layers.

Entity: Document Terms (keywords extracted from documents for text search)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLDocumentTermPipeline(BasePipeline):
    """Pipeline for ChEMBL document term data.

    Document terms are keywords extracted from documents for text search.
    They use a composite key of (document_chembl_id, term).

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
