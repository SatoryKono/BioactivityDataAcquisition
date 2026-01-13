"""ChEMBL Publication Term Pipeline.

Extracts terms (MeSH headings, keywords, concepts) from ChEMBL Publication
records and processes through Bronze → Silver → Gold layers.

Entity: Publication Terms (derived from Publication)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

This is a derived entity pipeline - it extracts nested term data
from Publication (ChEMBL Document) API responses and flattens the 1:M relationship.

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).

.. versionchanged:: 2.0.0
    Renamed from document_term to publication_term (ADR-024).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLPublicationTermPipeline(BasePipeline):
    """Pipeline for ChEMBL publication term data.

    This pipeline extracts and flattens term data from Publication records:
    - MeSH headings and qualifiers
    - Author keywords
    - ChEMBL concepts

    Each Publication may produce multiple Term records (1:M relationship).

    Transformer is injected via DI from GenericPipelineFactory.

    .. versionchanged:: 2.0.0
        Renamed from ChEMBLDocumentTermPipeline (ADR-024).
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)


# Backward-compatible alias (deprecated, ADR-024)
ChEMBLDocumentTermPipeline = ChEMBLPublicationTermPipeline
