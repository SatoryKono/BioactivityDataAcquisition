"""ChEMBL Target Component Transformer.

Transforms Bronze records to Silver format (Target Component entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import TargetComponent
from bioetl.domain.transformations import generate_entity_id, safe_int

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class TargetComponentTransformer(BaseTransformer):
    """Transforms ChEMBL bronze target component records to silver."""

    def __init__(self, provider: str = "chembl"):
        super().__init__(provider)

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL target component to normalized format using Domain Entity."""
        component_id = record.get("component_id")

        if not component_id:
            return None

        try:
            entity_id = generate_entity_id(
                record={"component_id": str(component_id)},
                provider=self.provider,
                id_field="component_id",
            )

            business_data: dict[str, Any] = {
                # Primary identifier
                "component_id": safe_int(component_id),
                # Core metadata
                "accession": record.get("accession"),
                "component_type": record.get("component_type"),
                "description": record.get("description"),
                "organism": record.get("organism"),
                "tax_id": safe_int(record.get("tax_id")),
                # Complex fields (JSON serialized)
                "target_component_synonyms": self.serialize_json(
                    record.get("target_component_synonyms")
                ),
                "target_component_xrefs": self.serialize_json(
                    record.get("target_component_xrefs")
                ),
            }

            content_hash = self.compute_content_hash(business_data, exclude_none=True)

            entity = TargetComponent(
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
                component_id=component_id,
            )
            return None

        # Convert Entity to SilverRecord for storage
        silver_record = self.entity_to_silver_record(entity)

        return cast("SilverRecord", silver_record)
