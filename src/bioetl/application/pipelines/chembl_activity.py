"""ChEMBL Activity Pipeline.

Fetches bioactivity data from ChEMBL database and processes it through
Bronze → Silver → Gold layers.

Entity: Bioactivity measurements (IC50, Ki, EC50, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import (
    PipelineRuntimeConfig,
)
from bioetl.domain.pipeline_config import PipelineConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.transformations import (
    generate_content_hash,
    generate_entity_id,
    safe_float,
)
from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class ChEMBLActivityPipeline(BasePipeline):
    """Pipeline for ChEMBL bioactivity data."""

    @classmethod
    def create(
        cls,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
        config: PipelineConfig,
    ) -> "ChEMBLActivityPipeline":
        """Create ChEMBL Activity pipeline with decomposed config (new API)."""
        return cls(config, runtime, services)

    def __init__(
        self,
        config: PipelineConfig,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
    ) -> None:
        """Initialize ChEMBL Activity pipeline."""
        super().__init__(config, runtime, services)

    async def transform_bronze_to_silver(
        self,
        _context: PipelineContext,
        record: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Transform raw ChEMBL activity to normalized format."""
        if not record.get("activity_id"):
            return None

        # If a list of fields is specified in the config, use it to build the record
        if self.config.fields:
            normalized = {field: record.get(field) for field in self.config.fields}
        else:
            # Fallback to extracting all fields if none are specified
            normalized = record.copy()

        # Ensure critical fields are present and correctly typed
        activity_id = str(record["activity_id"])
        normalized["activity_id"] = activity_id

        entity_id = generate_entity_id(
            record={"activity_id": activity_id},
            provider=self.provider,
            id_field="activity_id",
        )
        normalized["entity_id"] = entity_id

        # Type conversions for numeric fields
        if "standard_value" in normalized:
            normalized["standard_value"] = safe_float(normalized["standard_value"])

        if "pchembl_value" in normalized:
            normalized["pchembl_value"] = safe_float(normalized["pchembl_value"])

        # Generate content_hash for versioning
        content_hash = generate_content_hash(normalized, self.provider)
        normalized["content_hash"] = content_hash

        return normalized

    def should_write_gold(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> bool:
        """Filter records for Gold layer."""
        if record.get("standard_value") is None:
            return False
        if not record.get("standard_units"):
            return False
        if not record.get("target_chembl_id"):
            return False

        standard_type = record.get("standard_type")
        # Use configured types or fallback to default
        preferred_types = set(self.config.gold_filter_types) or {
            "IC50",
            "Ki",
            "EC50",
            "Kd",
            "AC50",
            "GI50",
        }
        if standard_type not in preferred_types:
            return False

        return not record.get("data_validity_comment")

    def extract_watermark(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract watermark from record."""
        activity_id = record.get("activity_id")
        if activity_id:
            return str(activity_id)
        fallback_field = self.config.watermark_field
        fallback_value = record.get(fallback_field) if fallback_field else None
        if fallback_value is None:
            return ""

        if isinstance(fallback_value, datetime):
            return fallback_value.replace(tzinfo=fallback_value.tzinfo or UTC)

        if isinstance(fallback_value, str):
            try:
                parsed = datetime.fromisoformat(fallback_value)
            except ValueError:
                return fallback_value
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed

        return fallback_value
