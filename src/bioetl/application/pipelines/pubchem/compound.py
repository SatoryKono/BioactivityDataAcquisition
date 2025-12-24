"""PubChem Compound Pipeline Implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from bioetl.application.core.base import BasePipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer

if TYPE_CHECKING:
    pass


class PubChemCompoundPipeline(BasePipeline[PubChemCompoundTransformer]):
    """Pipeline for processing PubChem compounds."""

    @property
    def transformer_class(self) -> Type[PubChemCompoundTransformer]:
        return PubChemCompoundTransformer
