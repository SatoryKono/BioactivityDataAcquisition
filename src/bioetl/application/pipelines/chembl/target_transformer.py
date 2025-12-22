"""ChEMBL Target Transformer.

Transforms Bronze records to Silver format (Target entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import Target
from bioetl.domain.transformations import (
    generate_entity_id,
    safe_int,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class TargetTransformer(BaseTransformer):
    """Transforms ChEMBL bronze target records to silver."""

    def __init__(self, provider: str = "chembl"):
        super().__init__(provider)

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL target to normalized format using Domain Entity."""
        target_chembl_id = record.get("target_chembl_id")

        if not target_chembl_id:
            return None

        try:
            entity_id = generate_entity_id(
                record={"target_chembl_id": str(target_chembl_id)},
                provider=self.provider,
                id_field="target_chembl_id",
            )

            business_data: dict[str, Any] = {
                # Primary identifier
                "target_chembl_id": str(target_chembl_id),
                # Core metadata
                "pref_name": record.get("pref_name"),
                "target_type": record.get("target_type"),
                "organism": record.get("organism"),
                "tax_id": safe_int(record.get("tax_id")),
                "species_group_flag": record.get("species_group_flag"),
                # Complex fields (JSON serialized)
                "target_components": self.serialize_json(record.get("target_components")),
                "cross_references": self.serialize_json(record.get("cross_references")),
            }

            content_hash = self.compute_content_hash(business_data, exclude_none=True)

            entity = Target(
                entity_id=entity_id,
                content_hash=content_hash,
                run_id=context.run_id,
                run_type=context.run_type,
                source_batch_id=None,
                **business_data,
            )

        except ValueError as e:
            context.logger.warning(
                "entity_validation_failed",
                error=str(e),
                target_chembl_id=target_chembl_id,
            )
            return None

        # Convert Entity to SilverRecord for storage
        silver_record = self.entity_to_silver_record(entity)

        return cast("SilverRecord", silver_record)
