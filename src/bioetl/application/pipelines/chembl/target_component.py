"""ChEMBL Target Component Pipeline.

Fetches target components from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Target Components (protein sequences, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from bioetl.application.core.base import BasePipeline


class ChEMBLTargetComponentPipeline(BasePipeline):
    """Pipeline for ChEMBL target component data.

    Transformer is injected via GenericPipelineFactory (DI pattern).
    transform_bronze_to_silver() and should_write_gold() are inherited from BasePipeline.
    """

    pass
