"""Contracts for record mapping between layers."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from bioetl.domain.ports.parsing import RecordBatch
from bioetl.domain.record_source import SourceRecordModel


class RecordMapperABC(ABC):
    """Maps raw records from infrastructure to domain models.

    This abstract base class defines the contract for mapping untyped
    record dictionaries from the infrastructure layer to typed domain
    SourceRecordModel instances. Implementations handle source-specific
    mapping logic and validation.

    Example:
        >>> class MyMapper(RecordMapperABC):
        ...     def map_records(self, raw_records, entity):
        ...         model_cls = get_model_for_entity(entity)
        ...         return [model_cls.model_validate(r) for r in raw_records]
        ...
        ...     def get_supported_entities(self):
        ...         return frozenset({"activity", "molecule"})
    """

    @abstractmethod
    def map_records(
        self,
        raw_records: RecordBatch,
        entity: str,
    ) -> list[SourceRecordModel]:
        """Convert raw dicts to typed domain SourceRecordModel instances.

        Args:
            raw_records: Untyped records from infrastructure parser.
            entity: Entity type (activity, assay, target, molecule, document).

        Returns:
            List of validated domain SourceRecordModel instances.

        Raises:
            ValueError: If entity type is unknown.
            ValidationError: If record validation fails.
        """

    @abstractmethod
    def get_supported_entities(self) -> frozenset[str]:
        """Return set of entity names this mapper supports.

        Returns:
            Frozen set of entity type names (e.g., "activity", "molecule").
        """


__all__ = ["RecordMapperABC"]
