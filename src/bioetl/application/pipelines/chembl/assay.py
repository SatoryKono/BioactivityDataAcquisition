"""ChEMBL Assay Pipeline.

Fetches assay definitions from ChEMBL database and processes them through
Bronze → Silver → Gold layers.

Entity: Bioassay definitions (binding, functional, ADMET, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from bioetl.application.core.base import BasePipeline


class ChEMBLAssayPipeline(BasePipeline):
    """Pipeline for ChEMBL assay data.

    Transformer is injected via GenericPipelineFactory (DI pattern).
    transform_bronze_to_silver() and should_write_gold() are inherited from BasePipeline.
    """

    pass
