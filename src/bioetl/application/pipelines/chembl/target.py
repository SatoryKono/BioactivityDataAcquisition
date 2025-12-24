"""ChEMBL Target Pipeline.

Fetches biological targets from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Biological Targets (proteins, complexes, organisms)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer

if TYPE_CHECKING:
    pass


class ChEMBLTargetPipeline(BasePipeline[TargetTransformer]):
    """Pipeline for ChEMBL target data."""

    @property
    def transformer_class(self) -> Type[TargetTransformer]:
        return TargetTransformer

    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
