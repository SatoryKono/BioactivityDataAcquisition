"""ChEMBL Document Term Pipeline.

Extracts terms (MeSH headings, keywords, concepts) from ChEMBL Document
records and processes through Bronze → Silver → Gold layers.

Entity: Document Terms (derived from Document)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

This is a derived entity pipeline - it extracts nested term data
from Document API responses and flattens the 1:M relationship.

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLDocumentTermPipeline(BasePipeline):
    """Pipeline for ChEMBL document term data.

    This pipeline extracts and flattens term data from Document records:
    - MeSH headings and qualifiers
    - Author keywords
    - ChEMBL concepts

    Each Document may produce multiple Term records (1:M relationship).

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
