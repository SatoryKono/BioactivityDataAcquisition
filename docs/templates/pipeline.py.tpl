"""
Template for a new Pipeline class.
Location: src/bioetl/application/pipelines/<provider>_<entity>.py
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from bioetl.application.core.base import BasePipeline
from bioetl.domain.config import PipelineConfig, PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.transformations import generate_content_hash, generate_entity_id
from bioetl.domain.types import Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext

# Default Configuration
{{PROVIDER}}_{{ENTITY}}_CONFIG = PipelineConfig(
    pipeline_name="{{provider}}_{{entity}}",
    provider="{{provider}}",
    entity_type="{{entity}}",
    primary_keys=["{{primary_key}}"],
    silver_table="{{provider}}.{{entity}}",
)

class {{Provider}}{{Entity}}Pipeline(BasePipeline):
    """Pipeline for {{Provider}} {{Entity}}."""

    @classmethod
    def create(
        cls,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
        config: PipelineConfig | None = None,
    ) -> "{{Provider}}{{Entity}}Pipeline":
        return cls(config or {{PROVIDER}}_{{ENTITY}}_CONFIG, runtime, services)

    async def transform_bronze_to_silver(
        self,
        context: PipelineContext,
        record: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Transform raw record to Silver format."""

        # 1. Validation / Skipping
        pk_value = record.get("{{source_primary_key}}")
        if not pk_value:
            return None

        # 2. ID Generation
        entity_id = generate_entity_id(
            record=record,
            provider=self.provider,
            id_field="{{source_primary_key}}",
        )

        # 3. Normalization
        normalized = {
            "entity_id": entity_id,
            "{{primary_key}}": str(pk_value),
            # Map other fields here
            "field_name": record.get("source_field"),
        }

        # 4. Content Hash
        normalized["content_hash"] = generate_content_hash(normalized, self.provider)

        return normalized

    def should_write_gold(self, context: PipelineContext, record: dict[str, Any]) -> bool:
        """Filter logic for Gold layer (optional)."""
        return True
