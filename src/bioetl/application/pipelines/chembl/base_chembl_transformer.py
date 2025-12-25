"""Base ChEMBL Transformer.

Provides common transformation logic for all ChEMBL entity transformers.
Implements Template Method pattern to eliminate duplication across:
- ActivityTransformer
- AssayTransformer
- DocumentTransformer
- MoleculeTransformer
- TargetTransformer
- TargetComponentTransformer
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.types import BronzeRecord, SilverRecord


class BaseChemblTransformer(BaseTransformer):
    """Base class for all ChEMBL transformers.

    Provides common field extraction and mapping logic.
    Implements Template Method pattern for unified transformation flow.

    Subclasses MUST define:
    - `entity_class`: The domain entity class to create
    - `primary_id_field`: Field name of the primary identifier

    Subclasses MUST implement:
    - `_extract_business_data()`: Entity-specific field extraction

    Example:
        >>> class ActivityTransformer(BaseChemblTransformer):
        ...     entity_class = Activity
        ...     primary_id_field = "activity_id"
        ...
        ...     def _extract_business_data(self, record, primary_id):
        ...         return {"activity_id": str(primary_id), ...}

    """

    # Class variables that subclasses must override
    entity_class: ClassVar[type[BaseEntity]]
    primary_id_field: ClassVar[str]

    def __init__(self, provider: str = "chembl") -> None:
        """Initialize ChEMBL transformer.

        Args:
            provider: Data provider identifier. Defaults to 'chembl'.

        """
        super().__init__(provider)

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Template method implementing common ChEMBL transformation flow.

        Steps:
        1. Validate and extract primary ID
        2. Generate entity_id using standard format
        3. Extract business data (delegated to subclass)
        4. Compute content hash
        5. Create domain entity
        6. Convert to SilverRecord

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from ChEMBL API.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        """
        # 1. Validate primary ID
        primary_id = self._get_required_field(record, self.primary_id_field)

        # 2. Generate entity ID
        entity_id = generate_entity_id(
            record={self.primary_id_field: str(primary_id)},
            provider=self.provider,
            id_field=self.primary_id_field,
        )

        # 3. Extract business data (delegated to subclass)
        business_data = self._extract_business_data(record, primary_id)

        # 4. Compute content hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # 5. Create domain entity
        entity = self._create_entity(
            self.entity_class,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            **business_data,
        )

        # 6. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    @abstractmethod
    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract business data from the bronze record.

        Subclasses MUST implement this method to extract entity-specific fields.
        The primary_id is already validated and passed for convenience.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated primary identifier value.

        Returns:
            Dictionary of business data fields for entity creation.

        Example:
            >>> def _extract_business_data(self, record, primary_id):
            ...     return {
            ...         "activity_id": str(primary_id),
            ...         "molecule_chembl_id": record.get("molecule_chembl_id"),
            ...         ...
            ...     }

        """
        ...
