"""ChEMBL-specific record mapper implementation."""

from __future__ import annotations

from bioetl.application.mappers.chembl.model_registry import (
    ENTITY_MODEL_REGISTRY,
    get_model_for_entity,
)
from bioetl.application.mappers.contracts import RecordMapperABC
from bioetl.domain.ports.parsing import RawRecordList
from bioetl.domain.record_source import RawRecord

# Supported entities derived from centralized registry
_SUPPORTED_ENTITIES: frozenset[str] = frozenset(ENTITY_MODEL_REGISTRY.keys())


class ChemblRecordMapper(RecordMapperABC):
    """Maps raw ChEMBL records to typed domain models.

    This mapper converts untyped dictionaries from the infrastructure
    layer to validated domain RawRecord instances using Pydantic models.

    Example:
        >>> mapper = ChemblRecordMapper()
        >>> raw_records = [{"activity_id": 123, "standard_flag": True}]
        >>> domain_records = mapper.map_records(raw_records, "activity")
        >>> assert isinstance(domain_records[0], ActivityRawModel)
    """

    def map_records(
        self,
        raw_records: RawRecordList,
        entity: str,
    ) -> list[RawRecord]:
        """Convert raw dicts to typed ChEMBL domain models.

        Args:
            raw_records: Untyped records from infrastructure parser.
            entity: Entity type (activity, assay, target, molecule, document).

        Returns:
            List of validated domain RawRecord instances.

        Raises:
            ValueError: If entity type is unknown.
            ValidationError: If record validation fails (from Pydantic).
        """
        model_class = self._get_model_class(entity)
        return [model_class.model_validate(record) for record in raw_records]

    def get_supported_entities(self) -> frozenset[str]:
        """Return set of entity names this mapper supports.

        Returns:
            Frozen set containing: activity, assay, target, molecule, document.
        """
        return _SUPPORTED_ENTITIES

    def _get_model_class(self, entity: str) -> type[RawRecord]:
        """Get model class for entity type.

        Args:
            entity: Entity type name.

        Returns:
            Pydantic model class for the entity.

        Raises:
            ValueError: If entity type is unknown.
        """
        # Use centralized registry from model_registry module
        return get_model_for_entity(entity)  # type: ignore[return-value]


__all__ = ["ChemblRecordMapper"]
