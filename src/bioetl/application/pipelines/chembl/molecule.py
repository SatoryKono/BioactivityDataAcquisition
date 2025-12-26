"""ChEMBL Molecule Pipeline.

Fetches molecules from ChEMBL database and processes through
Bronze -> Silver -> Gold layers.

Entity: Chemical Compounds (small molecules, antibodies, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

Refactored: Uses default_transformer_class for fallback (eliminates __init__ boilerplate).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer


class ChEMBLMoleculePipeline(BasePipeline):
    """Pipeline for ChEMBL molecule data.

    Transformer is injected via DI from GenericPipelineFactory.
    Falls back to MoleculeTransformer if not injected.
    """

    default_transformer_class = MoleculeTransformer

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
