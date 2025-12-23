"""ChEMBL Document Pipeline.

Fetches scientific documents from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Scientific Documents (publications, patents)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from bioetl.application.core.base import BasePipeline


class ChEMBLDocumentPipeline(BasePipeline):
    """Pipeline for ChEMBL document data.

    Transformer is injected via GenericPipelineFactory (DI pattern).
    transform_bronze_to_silver() and should_write_gold() are inherited from BasePipeline.
    """

    pass
