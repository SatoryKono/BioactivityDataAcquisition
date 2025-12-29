"""ChEMBL Document Similarity Pipeline.

Fetches document similarity matrix from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Document Similarity (pairwise similarity between documents)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLDocumentSimilarityPipeline(BasePipeline):
    """Pipeline for ChEMBL document similarity data.

    Pairwise similarity matrix for documents. Used for recommendations
    and publication clustering.

    Composite Key: (document_1_chembl_id, document_2_chembl_id)
    Normalized: doc1 < doc2 lexicographically (upper triangle only).

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
