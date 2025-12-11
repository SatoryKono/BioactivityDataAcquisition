"""ChEMBL-specific record mapper implementation."""

from __future__ import annotations

from typing import cast

from bioetl.application.mappers.contracts import RecordMapperABC
from bioetl.domain.ports.entity_models import EntityModelRegistryABC
from bioetl.domain.ports.parsing import RecordBatch
from bioetl.domain.record_source import SourceRecordModel


class ChemblRecordMapper(RecordMapperABC):
    """Maps raw ChEMBL records to typed domain models.

    This mapper converts untyped dictionaries from the infrastructure
    layer to validated domain SourceRecordModel instances using Pydantic models.

    Args:
        registry: Entity model registry for resolving entity types to models.
            If not provided, uses the default ChEMBL registry.

    Example:
        >>> mapper = ChemblRecordMapper()
        >>> raw_records = [{"activity_id": 123, "standard_flag": True}]
        >>> domain_records = mapper.map_records(raw_records, "activity")
        >>> assert isinstance(domain_records[0], ActivityRawModel)
    """

    def __init__(
        self,
        registry: EntityModelRegistryABC,
    ) -> None:
        """Initialize mapper with entity model registry.

        Args:
            registry: Entity model registry for resolving entity types.
        """
        self._registry = registry

    def map_records(
        self,
        raw_records: RecordBatch,
        entity: str,
    ) -> list[SourceRecordModel]:
        """Convert raw dicts to typed ChEMBL domain models.

        Args:
            raw_records: Untyped records from infrastructure parser.
            entity: Entity type (activity, assay, target, molecule, document,
                publication).

        Returns:
            List of validated domain SourceRecordModel instances.

        Raises:
            ValueError: If entity type is unknown.
            ValidationError: If record validation fails (from Pydantic).
        """
        model_class = self._registry.get_model(entity)
        return [
            cast(SourceRecordModel, model_class.model_validate(record))
            for record in raw_records
        ]

    def get_supported_entities(self) -> frozenset[str]:
        """Return set of entity names this mapper supports.

        Returns:
            Frozen set containing: activity, assay, target, molecule,
            document, publication.
        """
        return self._registry.supported_entities()


__all__ = ["ChemblRecordMapper"]
