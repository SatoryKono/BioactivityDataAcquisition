"""ChEMBL Cell Line Pipeline.

Fetches cell lines from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Cell Lines (biological objects for in vitro experiments)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLCellLinePipeline(BasePipeline):
    """Pipeline for ChEMBL cell line data.

    Cell lines are biological objects used for in vitro experiments.
    They have M:N relationship with Assay (via assay.cell_chembl_id FK).

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
