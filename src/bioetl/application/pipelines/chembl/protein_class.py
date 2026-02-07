"""ChEMBL Protein Classification Pipeline.

Fetches protein classification hierarchy from ChEMBL database and processes
through Bronze -> Silver -> Gold layers.

Entity: Protein Classification hierarchy (enzyme classes, receptor types, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLProteinClassPipeline(BasePipeline):
    """Pipeline for ChEMBL protein classification data.

    Hierarchical classification of protein targets (enzymes, receptors,
    ion channels, transporters, etc.). Self-referencing structure with
    up to 8 levels of depth. Reference table (~1,500 records).

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
