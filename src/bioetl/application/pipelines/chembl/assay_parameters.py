# src/bioetl/application/pipelines/chembl/assay_parameters.py
"""ChEMBL Assay Parameters Pipeline.

Fetches assay parameters from ChEMBL database and processes through
Bronze -> Silver -> Gold layers.

Entity: Assay Parameters (experimental conditions for bioassays)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLAssayParametersPipeline(BasePipeline):
    """Pipeline for ChEMBL assay parameters data.

    Assay parameters contain experimental conditions such as concentrations,
    pH, temperature, incubation time, etc. for bioassays.
    M:1 relationship with Assay (many parameters -> one assay via assay_chembl_id FK).

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
