"""ChEMBL Molecule Pipeline.

Fetches molecules from ChEMBL database and processes through
Bronze -> Silver -> Gold layers.

Entity: Chemical Compounds (small molecules, antibodies, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer

if TYPE_CHECKING:
    pass


class ChEMBLMoleculePipeline(BasePipeline[MoleculeTransformer]):
    """Pipeline for ChEMBL molecule data."""

    @property
    def transformer_class(self) -> Type[MoleculeTransformer]:
        return MoleculeTransformer

    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
