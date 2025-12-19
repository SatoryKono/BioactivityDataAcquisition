"""ChEMBL Activity Pipeline.

Fetches bioactivity data from ChEMBL database and processes it through
Bronze → Silver → Gold layers.

Entity: Bioactivity measurements (IC50, Ki, EC50, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base import BasePipeline
from bioetl.domain.entities import Activity
from bioetl.domain.transformations import (
    generate_content_hash,
    generate_entity_id,
    safe_float,
)
from bioetl.domain.types import BronzeRecord, SilverRecord, Watermark

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class ChEMBLActivityPipeline(BasePipeline):
    """Pipeline for ChEMBL bioactivity data."""

    def __init__(
        self,
        config: PipelineConfig,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
    ) -> None:
        """Initialize pipeline and pre-compute filter sets."""
        super().__init__(config, runtime, services)
        # Pre-compute set for O(1) lookups in hot path
        self._preferred_types = set(self.config.gold_filter_types) or {
            "IC50",
            "Ki",
        }

    async def transform_bronze_to_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL activity to normalized format using Domain Entity."""
        activity_id = record.get("activity_id")
        if not activity_id:
            return None

        # 1. Prepare data for Entity inflation
        # Clean numeric fields
        pchembl = safe_float(record.get("pchembl_value"))
        std_val = safe_float(record.get("standard_value"))

        # 2. Instantiate Domain Entity (Validation happens here)
        try:
            # We construct the ID / Hash first as they are required by BaseEntity
            entity_id = generate_entity_id(
                record={"activity_id": str(activity_id)},
                provider=self.provider,
                id_field="activity_id",
            )

            # Map raw fields to Entity fields
            business_data = {
                "activity_id": str(activity_id),
                "molecule_id": str(record.get("molecule_chembl_id", "")),
                "target_id": str(record.get("target_chembl_id", "")),
                "assay_id": str(record.get("assay_chembl_id", "")),
                "standard_type": record.get("standard_type"),
                "standard_value": std_val,
                "standard_units": record.get("standard_units"),
                "standard_relation": record.get("standard_relation"),
                "pchembl_value": pchembl,
                "activity_comment": record.get("activity_comment"),
                "data_validity_comment": record.get("data_validity_comment"),
                # Extended fields (Gap Analysis Fix)
                "assay_type": record.get("assay_type"),
                "assay_description": record.get("assay_description"),
                "document_chembl_id": record.get("document_chembl_id"),
                "document_year": record.get("document_year"),
            }

            # Generate content hash based on business data
            content_hash = generate_content_hash(business_data, self.provider)

            entity = Activity(
                entity_id=entity_id,
                content_hash=content_hash,
                run_id=context.run_id,
                run_type=context.run_type,
                source_batch_id="UNKNOWN",  # TODO: pass batch_id from context if available
                **business_data,
            )

        except ValueError as e:
            # Validation failed (e.g. pchembl < 0)
            # Log warning and skip record (return None)
            self.logger.warning(
                "entity_validation_failed", error=str(e), activity_id=activity_id
            )
            return None

        # 3. Convert back to SilverRecord (DTO) for storage
        # Strictly populate from Entity attributes to ensure Domain is the source of truth
        silver_record: dict[str, Any] = {
            "entity_id": entity.entity_id,
            "content_hash": entity.content_hash,
            "activity_id": entity.activity_id,
            "molecule_chembl_id": entity.molecule_id,
            "target_chembl_id": entity.target_id,
            "assay_chembl_id": entity.assay_id,
            "standard_type": entity.standard_type,
            "standard_value": entity.standard_value,
            "standard_units": entity.standard_units,
            "standard_relation": entity.standard_relation,
            "pchembl_value": entity.pchembl_value,
            "activity_comment": entity.activity_comment,
            "data_validity_comment": entity.data_validity_comment,
            "assay_type": entity.assay_type,
            "assay_description": entity.assay_description,
            "document_chembl_id": entity.document_chembl_id,
            "document_year": entity.document_year,
            # System fields required by Silver Schema
            "_run_id": str(entity.run_id),
            "_run_type": str(entity.run_type.value),
            "_ingestion_ts": entity.ingestion_ts.isoformat(),
        }

        return cast(SilverRecord, silver_record)

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
        # Use pre-computed set for fast lookup
        if standard_type not in self._preferred_types:
            return False

        return not record.get("data_validity_comment")

    def extract_watermark(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract watermark and return Watermark wrapper.

        Behavior:
        - if activity_id present: Watermark.from_id(str(activity_id));
        - else use config field (e.g. updated_on) and return
          Watermark.from_timestamp(datetime in UTC) if valid ISO8601;
        - if value not date-like — Watermark.from_id(str(value));
        - if nothing — Watermark.from_id("").
        """
        activity_id = record.get("activity_id")
        if activity_id is not None:
            return Watermark.from_id(str(activity_id))

        fallback_field = self.config.watermark_field
        fallback_value = record.get(fallback_field) if fallback_field else None

        if fallback_value is None:
            return Watermark.from_id("")

        if isinstance(fallback_value, datetime):
            return Watermark.from_timestamp(
                fallback_value.replace(tzinfo=fallback_value.tzinfo or UTC)
            )

        if isinstance(fallback_value, str):
            try:
                parsed = datetime.fromisoformat(fallback_value)
            except ValueError:
                return Watermark.from_id(fallback_value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return Watermark.from_timestamp(parsed)

        return Watermark.from_id(str(fallback_value))
