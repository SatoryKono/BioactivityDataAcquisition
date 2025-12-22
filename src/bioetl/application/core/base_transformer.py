"""Base Transformer class for Bronze → Silver transformations.

Provides common functionality for all entity transformers:
- Content hash generation (RULES.md §2.8.1)
- JSON serialization of complex fields
- Entity to SilverRecord conversion with lineage field renaming

Implements DRY principle by extracting shared logic from entity transformers.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.transformations import generate_content_hash
from bioetl.domain.types import ContentHash

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class BaseTransformer(ABC):
    """Abstract base class for Bronze → Silver transformers.

    Provides:
    - `compute_content_hash()`: Canonical content hash generation (RULES.md §2.8.1)
    - `serialize_json()`: JSON serialization for complex fields (dict/list)
    - `entity_to_silver_record()`: Entity → SilverRecord conversion with lineage fields

    Subclasses MUST implement:
    - `transform()`: Entity-specific transformation logic
    """

    def __init__(self, provider: str) -> None:
        """Initialize transformer with provider name.

        Args:
            provider: Data provider identifier (e.g., 'chembl', 'pubchem').
        """
        self.provider = provider

    def compute_content_hash(
        self,
        business_data: dict[str, Any],
        *,
        exclude_none: bool = True,
    ) -> ContentHash:
        """Generate canonical content hash for record versioning.

        Implements RULES.md §2.8.1:
        - sha256(provider + canonical_json(record))
        - Normalizes NaN/Inf → null, floats → round(val, 10), dates → ISO

        Args:
            business_data: Business data dictionary (excluding meta fields).
            exclude_none: Whether to exclude None values from hash calculation.

        Returns:
            ContentHash: SHA256 hash of normalized record.
        """
        return generate_content_hash(
            business_data,
            self.provider,
            exclude_none=exclude_none,
        )

    @staticmethod
    def serialize_json(value: Any) -> str | None:
        """Serialize complex values (dict/list) to JSON string.

        Used for storing nested structures in Silver layer as JSON strings.

        Args:
            value: Value to serialize.

        Returns:
            JSON string for dict/list, str(value) for other types, None for None.
        """
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @staticmethod
    def entity_to_silver_record(entity: Any) -> dict[str, Any]:
        """Convert Domain Entity to SilverRecord format.

        Handles lineage fields renaming and formatting:
        - run_id → _run_id (str)
        - run_type → _run_type (str value)
        - source_batch_id → _source_batch_id (str)
        - ingestion_ts → _ingestion_ts (ISO string)

        Args:
            entity: Domain entity with __dict__ attribute.

        Returns:
            SilverRecord dictionary with renamed lineage fields.
        """
        silver_record = entity.__dict__.copy()

        # Handle lineage fields renaming and formatting
        silver_record["_run_id"] = str(silver_record.pop("run_id"))
        silver_record["_run_type"] = str(silver_record.pop("run_type").value)
        silver_record["_source_batch_id"] = str(silver_record.pop("source_batch_id"))
        silver_record["_ingestion_ts"] = silver_record.pop("ingestion_ts").isoformat()

        return silver_record

    @abstractmethod
    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform Bronze record to Silver format.

        Subclasses MUST implement entity-specific transformation logic:
        1. Extract and validate required fields
        2. Build business_data dictionary
        3. Generate entity_id and content_hash
        4. Create Domain Entity
        5. Convert to SilverRecord using entity_to_silver_record()

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from data source.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.
        """
        ...
