"""ChEMBL Document Pipeline.

Fetches scientific documents from ChEMBL database and processes through
Bronze → Silver → Gold layers.

Entity: Scientific Documents (publications, patents)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.chembl.document_transformer import DocumentTransformer

if TYPE_CHECKING:
    pass


class ChEMBLDocumentPipeline(BasePipeline[DocumentTransformer]):
    """Pipeline for ChEMBL document data."""

    @property
    def transformer_class(self) -> Type[DocumentTransformer]:
        return DocumentTransformer

    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
