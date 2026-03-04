"""ChEMBL Tissue Transformer.

Transforms Bronze records to Silver format (Tissue entity inflation).
"""

from __future__ import annotations

__all__ = ["TissueTransformer"]


from typing import TYPE_CHECKING, Any

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities.chembl_tissue import Tissue

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId, SilverRecord


class TissueTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze tissue records to silver.

    Tissues are anatomical structures used in assay experiments.
    They have 1:M relationship with Assay (via assay.tissue_chembl_id FK).
    """

    entity_class = Tissue
    primary_id_field = "tissue_id"

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Support both unified and legacy tissue identifier field names."""
        if "tissue_id" not in record and record.get("tissue_chembl_id") is not None:
            record_with_alias = dict(record)
            record_with_alias["tissue_id"] = record_with_alias.get("tissue_chembl_id")
            record = record_with_alias
        return await super()._transform_impl(context, record, index)

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> dict[str, Any]:  # Any: transformer record has heterogeneous values
        """Extract Tissue business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated tissue_id value.

        Returns:
            Dictionary of Tissue business fields.
        """
        normalizer = self._data_normalizer

        return {
            # Primary identifier
            "tissue_id": str(primary_id),
            # Core metadata (required)
            "pref_name": normalizer.normalize_to_string(record.get("pref_name")),
            # External ontology identifiers (optional)
            "bto_id": normalizer.normalize_to_string(record.get("bto_id")),
            "caloha_id": normalizer.normalize_to_string(record.get("caloha_id")),
            "efo_id": normalizer.normalize_to_string(record.get("efo_id")),
            "uberon_id": normalizer.normalize_to_string(record.get("uberon_id")),
        }
