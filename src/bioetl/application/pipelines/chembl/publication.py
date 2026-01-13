"""ChEMBL Publication Pipeline.

Fetches scientific publications from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Scientific Publications (journal articles, patents)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).

.. versionchanged:: 2.0.0
    Renamed from document to publication (ADR-024).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLPublicationPipeline(BasePipeline):
    """Pipeline for ChEMBL publication data.

    Transformer is injected via DI from GenericPipelineFactory.

    .. versionchanged:: 2.0.0
        Renamed from ChEMBLDocumentPipeline (ADR-024).
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)


# Backward-compatible alias (deprecated, ADR-024)
ChEMBLDocumentPipeline = ChEMBLPublicationPipeline
