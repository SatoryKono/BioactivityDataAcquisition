"""ChEMBL Activity Pipeline.

Fetches bioactivity data from ChEMBL database and processes it through
Bronze → Silver → Gold layers.

Entity: Bioactivity measurements (IC50, Ki, EC50, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any
import yaml
from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import (
    PipelineConfig,
    PipelineRuntimeConfig,
)
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.transformations import generate_content_hash, generate_entity_id
from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext

# Load fields from YAML configuration
with open("configs/pipelines/chembl/activity.yaml", "r", encoding="utf-8") as f:
    config_data = yaml.safe_load(f)
    # Extract just the names of the fields
    SOURCE_FIELDS = [field['name'] for field in config_data.get("source", {}).get("fields", [])]

# Default configuration for ChEMBL Activity pipeline
CHEMBL_ACTIVITY_CONFIG = PipelineConfig(
    pipeline_name="chembl_activity",
    provider="chembl",
    entity_type="activity",
    primary_keys=["activity_id"],
    silver_table="chembl.activity",
    gold_table="chembl.activity_gold",
    batch_size=100,
    checkpoint_interval=1000,
    fields=SOURCE_FIELDS,
)


class ChEMBLActivityPipeline(BasePipeline):
    """Pipeline for ChEMBL bioactivity data."""

    @classmethod
    def create(
        cls,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
        config: PipelineConfig | None = None,
    ) -> "ChEMBLActivityPipeline":
        """Create ChEMBL Activity pipeline with decomposed config (new API)."""
        effective_config = config or CHEMBL_ACTIVITY_CONFIG
        return cls(effective_config, runtime, services)

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
        if "standard_value" in normalized and normalized["standard_value"] is not None:
            try:
                normalized["standard_value"] = float(normalized["standard_value"])
            except (ValueError, TypeError):
                normalized["standard_value"] = None

        if "pchembl_value" in normalized and normalized["pchembl_value"] is not None:
            try:
                normalized["pchembl_value"] = float(normalized["pchembl_value"])
            except (ValueError, TypeError):
                normalized["pchembl_value"] = None

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
        preferred_types = {"IC50", "Ki", "EC50", "Kd", "AC50", "GI50"}
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
        from datetime import datetime
        return datetime.now(UTC)
