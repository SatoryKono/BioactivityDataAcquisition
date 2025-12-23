"""PubMed Publications Pipeline.

Fetches publication data from PubMed database and processes through
Bronze → Silver → Gold layers.

Entity: Scientific Publications
Provider: PubMed (https://pubmed.ncbi.nlm.nih.gov/)
"""

from bioetl.application.core.base import BasePipeline


class PubMedPublicationsPipeline(BasePipeline):
    """Pipeline for PubMed publication data.

    Transformer is injected via GenericPipelineFactory (DI pattern).
    transform_bronze_to_silver() and should_write_gold() are inherited from BasePipeline.
    """

    pass
