"""ChEMBL Publication Similarity Pipeline.

Fetches publication similarity data from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Publication Similarity (Tanimoto coefficients between publications)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).

.. versionchanged:: 2.0.0
    Renamed from document_similarity to publication_similarity (ADR-024).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLPublicationSimilarityPipeline(BasePipeline):
    """Pipeline for ChEMBL publication similarity data.

    Extracts precomputed similarity relationships between publications
    based on Tanimoto coefficients calculated from:
    - Molecules described in publications (mol_tani)
    - Targets described in publications (tid_tani)

    Transformer is injected via DI from GenericPipelineFactory.

    .. versionchanged:: 2.0.0
        Renamed from ChEMBLDocumentSimilarityPipeline (ADR-024).
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)


# Backward-compatible alias (deprecated, ADR-024)
ChEMBLDocumentSimilarityPipeline = ChEMBLPublicationSimilarityPipeline
