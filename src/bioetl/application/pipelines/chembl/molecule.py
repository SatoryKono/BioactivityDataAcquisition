"""ChEMBL Molecule Pipeline.

Fetches molecules from ChEMBL database and processes through
Bronze -> Silver -> Gold layers.

Entity: Chemical Compounds (small molecules, antibodies, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLMoleculePipeline(BasePipeline):
    """Pipeline for ChEMBL molecule data.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
