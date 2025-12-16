"""ChEMBL Activity Pipeline.

Fetches bioactivity data from ChEMBL database and processes it through
Bronze -> Silver -> Gold layers.

Entity: Bioactivity measurements (IC50, Ki, EC50, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from typing import Any

from bioetl.application.pipeline.base import BasePipeline
from bioetl.domain.transformations import generate_content_hash, generate_entity_id
from bioetl.domain.types import Watermark


class ChEMBLActivityPipeline(BasePipeline):
    """Pipeline for ChEMBL bioactivity data.

    Transforms raw ChEMBL activity records into normalized format:
    - Bronze: Raw JSON from ChEMBL API
    - Silver: Normalized with entity_id, content_hash, metadata
    - Gold: Filtered high-quality activities (optional)
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            **kwargs,
        )

    async def transform_bronze_to_silver(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Transform raw ChEMBL activity to normalized format."""
        if not record.get("activity_id"):
            return None

        activity_id = str(record["activity_id"])
        entity_id = generate_entity_id(
            record={"activity_id": activity_id},
            provider=self.provider,
            id_field="activity_id",
        )

        standard_value = record.get("standard_value")
        if standard_value is not None:
            try:
                standard_value = float(standard_value)
            except (ValueError, TypeError):
                standard_value = None

        normalized = {
            "entity_id": entity_id,
            "activity_id": activity_id,
            "molecule_chembl_id": record.get("molecule_chembl_id"),
            "target_chembl_id": record.get("target_chembl_id"),
            "assay_chembl_id": record.get("assay_chembl_id"),
            "standard_type": record.get("standard_type"),
            "standard_value": standard_value,
            "standard_units": record.get("standard_units"),
            "standard_relation": record.get("standard_relation"),
            "assay_type": record.get("assay_type"),
            "assay_description": record.get("assay_description"),
            "document_chembl_id": record.get("document_chembl_id"),
            "document_year": record.get("document_year"),
            "pchembl_value": record.get("pchembl_value"),
            "activity_comment": record.get("activity_comment"),
            "data_validity_comment": record.get("data_validity_comment"),
        }

        normalized["content_hash"] = generate_content_hash(normalized, self.provider)
        return normalized

    def should_write_gold(self, record: dict[str, Any]) -> bool:
        """Filter records for Gold layer."""
        if record.get("standard_value") is None:
            return False
        if not record.get("standard_units"):
            return False
        if not record.get("target_chembl_id"):
            return False

        standard_type = record.get("standard_type")
        preferred_types = {"IC50", "Ki", "EC50", "Kd", "AC50", "GI50"}

        if standard_type not in preferred_types:
            return False

        return not record.get("data_validity_comment")

    def extract_watermark(self, record: dict[str, Any]) -> Watermark:
        """Extract watermark from record."""
        activity_id = record.get("activity_id")
        if activity_id:
            return Watermark(str(activity_id))

        from datetime import datetime, UTC
        return Watermark(datetime.now(UTC))
