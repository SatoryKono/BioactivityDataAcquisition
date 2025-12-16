"""ChEMBL Activity Pipeline.

Fetches bioactivity data from ChEMBL database and processes it through
Bronze → Silver → Gold layers.

Entity: Bioactivity measurements (IC50, Ki, EC50, etc.)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)
"""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any

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
)


class ChEMBLActivityPipeline(BasePipeline):
    """Pipeline for ChEMBL bioactivity data.

    Transforms raw ChEMBL activity records into normalized format:
    - Bronze: Raw JSON from ChEMBL API
    - Silver: Normalized with entity_id, content_hash, metadata
    - Gold: Filtered high-quality activities (optional)

    Example (new API - recommended):
        >>> from bioetl.application.core import PipelineRuntimeConfig, PipelineServices
        >>> from bioetl.domain.types import RunType
        >>> runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
        >>> services = PipelineServices(...)
        >>> pipeline = ChEMBLActivityPipeline.from_config(
        ...     config=CHEMBL_ACTIVITY_CONFIG,
        ...     runtime=runtime,
        ...     services=services,
        ... )
        >>> await pipeline.run()

    Example (legacy API - deprecated):
        >>> pipeline = ChEMBLActivityPipeline(
        ...     run_type=RunType.INCREMENTAL,
        ...     data_source=chembl_adapter,
        ...     storage=storage_adapter,
        ...     lock=redis_lock,
        ...     checkpoint=s3_checkpoint,
        ...     quarantine=quarantine,
        ... )
    """

    @classmethod
    def create(
        cls,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
        config: PipelineConfig | None = None,
    ) -> "ChEMBLActivityPipeline":
        """Create ChEMBL Activity pipeline with decomposed config (new API).

        Args:
            runtime: Runtime execution parameters.
            services: Injected I/O port dependencies.
            config: Pipeline configuration (uses default if None).

        Returns:
            Configured pipeline instance.
        """
        effective_config = config or CHEMBL_ACTIVITY_CONFIG
        return cls(effective_config, runtime, services)

    def __init__(
        self,
        config: PipelineConfig,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
    ) -> None:
        """Initialize ChEMBL Activity pipeline.

        Args:
            config: Static pipeline configuration (uses CHEMBL_ACTIVITY_CONFIG defaults).
            runtime: Runtime execution parameters.
            services: Injected I/O port dependencies.
        """
        super().__init__(config, runtime, services)

    async def transform_bronze_to_silver(
        self,
        _context: PipelineContext,
        record: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Transform raw ChEMBL activity to normalized format.

        Args:
            context: The pipeline context.
            record: Raw activity record from ChEMBL

        Returns:
            Normalized record or None if should skip

        Transformation logic:
        1. Generate stable entity_id from activity_id
        2. Extract key fields (molecule, target, assay)
        3. Normalize units and values
        4. Generate content_hash for deduplication
        5. Add metadata fields
        """
        # Skip if missing critical fields
        if not record.get("activity_id"):
            return None

        # Extract core fields
        activity_id = str(record["activity_id"])
        molecule_chembl_id = record.get("molecule_chembl_id")
        target_chembl_id = record.get("target_chembl_id")
        assay_chembl_id = record.get("assay_chembl_id")

        # Generate entity_id (stable identifier)
        entity_id = generate_entity_id(
            record={"activity_id": activity_id},
            provider=self.provider,
            id_field="activity_id",
        )

        # Extract measurement data
        standard_type = record.get("standard_type")  # IC50, Ki, EC50, etc.
        standard_value = record.get("standard_value")
        standard_units = record.get("standard_units")
        standard_relation = record.get("standard_relation")  # =, <, >, ~

        # Convert value to float if present
        if standard_value is not None:
            try:
                standard_value = float(standard_value)
            except (ValueError, TypeError):
                standard_value = None

        # Extract assay information
        assay_type = record.get("assay_type")
        assay_description = record.get("assay_description")

        # Extract publication info
        document_chembl_id = record.get("document_chembl_id")
        document_year = record.get("document_year")

        # Build normalized record
        normalized = {
            "entity_id": entity_id,
            "activity_id": activity_id,
            "molecule_chembl_id": molecule_chembl_id,
            "target_chembl_id": target_chembl_id,
            "assay_chembl_id": assay_chembl_id,
            "standard_type": standard_type,
            "standard_value": standard_value,
            "standard_units": standard_units,
            "standard_relation": standard_relation,
            "assay_type": assay_type,
            "assay_description": assay_description,
            "document_chembl_id": document_chembl_id,
            "document_year": document_year,
            # Additional fields
            "pchembl_value": record.get(
                "pchembl_value"
            ),  # -log10(molar IC50, XC50, etc)
            "activity_comment": record.get("activity_comment"),
            "data_validity_comment": record.get("data_validity_comment"),
        }

        # Generate content_hash for versioning
        content_hash = generate_content_hash(normalized, self.provider)
        normalized["content_hash"] = content_hash

        return normalized

    def should_write_gold(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> bool:
        """Filter records for Gold layer.

        Gold layer criteria:
        - Must have standard_value (not null)
        - Must have standard_units
        - Must have target_chembl_id
        - Preferred standard_types: IC50, Ki, EC50, Kd
        - No data validity issues

        Args:
            context: The pipeline context.
            record: Silver record

        Returns:
            True if passes quality filters
        """
        # Must have measurement value
        if record.get("standard_value") is None:
            return False

        # Must have units
        if not record.get("standard_units"):
            return False

        # Must have target
        if not record.get("target_chembl_id"):
            return False

        # Prefer certain measurement types
        standard_type = record.get("standard_type")
        preferred_types = {"IC50", "Ki", "EC50", "Kd", "AC50", "GI50"}

        if standard_type not in preferred_types:
            return False

        # Exclude if data validity issues
        return not record.get("data_validity_comment")

    def extract_watermark(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> Watermark:
        """Extract watermark from record.

        Uses activity_id as watermark for incremental loading.

        Args:
            context: The pipeline context.
            record: Activity record

        Returns:
            Watermark (activity_id)
        """
        activity_id = record.get("activity_id")
        if activity_id:
            return Watermark(str(activity_id))

        # Fallback to timestamp
        from datetime import datetime

        return Watermark(datetime.now(UTC))
