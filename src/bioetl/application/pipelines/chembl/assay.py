"""ChEMBL Assay Pipeline.

Fetches assay definitions from ChEMBL database and processes them through
Bronze → Silver → Gold layers.

Entity: Bioassay definitions (binding, functional, ADMET, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer

if TYPE_CHECKING:
    pass


class ChEMBLAssayPipeline(BasePipeline[AssayTransformer]):
    """Pipeline for ChEMBL assay data."""

    @property
    def transformer_class(self) -> Type[AssayTransformer]:
        return AssayTransformer

    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
