"""PubChem Compound Pipeline.

Fetches compound data from PubChem database and processes through
Bronze → Silver → Gold layers.

Entity: Chemical Compounds
Provider: PubChem (https://pubchem.ncbi.nlm.nih.gov/)
"""

from bioetl.application.core.base import BasePipeline


class PubChemCompoundPipeline(BasePipeline):
    """Pipeline for PubChem compound data.

    Transformer is injected via GenericPipelineFactory (DI pattern).
    transform_bronze_to_silver() and should_write_gold() are inherited from BasePipeline.
    """

    pass
