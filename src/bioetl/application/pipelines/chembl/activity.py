"""ChEMBL Activity Pipeline.

Fetches bioactivity data from ChEMBL database and processes it through
Bronze → Silver → Gold layers.

Entity: Bioactivity measurements (IC50, Ki, EC50, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer

if TYPE_CHECKING:
    pass


class ChEMBLActivityPipeline(BasePipeline[ActivityTransformer]):
    """Pipeline for ChEMBL bioactivity data."""

    @property
    def transformer_class(self) -> Type[ActivityTransformer]:
        return ActivityTransformer

    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
