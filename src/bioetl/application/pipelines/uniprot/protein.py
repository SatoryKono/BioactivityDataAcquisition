"""UniProt Protein Pipeline.

Fetches protein data from UniProt database and processes through
Bronze → Silver → Gold layers.

Entity: Proteins
Provider: UniProt (https://www.uniprot.org/)
"""

from bioetl.application.core.base import BasePipeline


class UniProtProteinPipeline(BasePipeline):
    """Pipeline for UniProt protein data.

    Transformer is injected via GenericPipelineFactory (DI pattern).
    transform_bronze_to_silver() and should_write_gold() are inherited from BasePipeline.
    """

    pass
