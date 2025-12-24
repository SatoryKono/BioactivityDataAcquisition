"""UniProt Protein Pipeline Implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer

if TYPE_CHECKING:
    pass


class UniProtProteinPipeline(BasePipeline[UniProtProteinTransformer]):
    """Pipeline for processing UniProt proteins."""

    @property
    def transformer_class(self) -> Type[UniProtProteinTransformer]:
        return UniProtProteinTransformer
