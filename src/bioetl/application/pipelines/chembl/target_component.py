"""ChEMBL Target Component Pipeline.

Fetches target components from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Target Components (protein sequences, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)

if TYPE_CHECKING:
    pass


class ChEMBLTargetComponentPipeline(BasePipeline[TargetComponentTransformer]):
    """Pipeline for ChEMBL target component data."""

    @property
    def transformer_class(self) -> Type[TargetComponentTransformer]:
        return TargetComponentTransformer

    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
