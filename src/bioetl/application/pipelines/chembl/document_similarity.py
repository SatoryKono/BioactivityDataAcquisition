"""ChEMBL Document Similarity Pipeline.

Fetches document similarity data from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Document Similarity (Tanimoto coefficients between documents)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLDocumentSimilarityPipeline(BasePipeline):
    """Pipeline for ChEMBL document similarity data.

    Extracts precomputed similarity relationships between documents
    based on Tanimoto coefficients calculated from:
    - Molecules described in documents (mol_tani)
    - Targets described in documents (tid_tani)

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
