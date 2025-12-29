"""ChEMBL Target Relation Pipeline.

Fetches target relations from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Target Relations (graph of relationships between biological targets)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLTargetRelationPipeline(BasePipeline):
    """Pipeline for ChEMBL target relation data.

    Target relations form a directed graph describing relationships between
    biological targets (subtypes, variants, complexes).

    Relationship types:
    - SUPERSET OF: target contains related_target
    - SUBSET OF: target is part of related_target
    - OVERLAPS WITH: partial intersection
    - EQUIVALENT TO: equivalence

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
