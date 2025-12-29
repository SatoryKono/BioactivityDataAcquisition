"""ChEMBL Protein Classification Pipeline.

Fetches protein classification hierarchy from ChEMBL database and processes through
Bronze -> Silver -> Gold layers.

Entity: Protein Classification (hierarchical protein family tree)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLProteinClassificationPipeline(BasePipeline):
    """Pipeline for ChEMBL protein classification data.

    Protein classifications form a hierarchical tree (ChEMBL protein family tree).
    They are reference data (~10K records) used for target classification.
    Self-referential hierarchy via parent_id FK.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
