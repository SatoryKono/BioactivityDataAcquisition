"""Domain-level transform contracts and DTOs.

Terminology Mapping (contracts ↔ schemas):
    This module uses domain-specific terms for hash concepts. The schema layer
    uses column names that differ for data storage compatibility.

    | Contract term | Schema column      | Canonical term       |
    |---------------|--------------------|----------------------|
    | fingerprint   | hash_row           | record_hash          |
    | entity_key    | hash_business_key  | business_key_hash    |

    Definitions:
        record_hash (fingerprint): SHA-256 hash of entire record (all fields).
            Provides content-based deduplication and change detection.
        business_key_hash (entity_key): SHA-256 hash of business key fields only.
            Identifies logical entity regardless of non-key field changes.

Tabular Data Abstractions:
    This module uses domain-level abstractions (Record, TabularData, RecordBatch)
    instead of pandas types. Infrastructure layer provides adapter implementations.

    See bioetl.domain.data for protocol definitions.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

# Import the canonical NormalizationConfig from configs.normalization
from bioetl.domain.configs.normalization import NormalizationConfig
from bioetl.domain.data import MutableTabularData, RecordBatch, TabularData
from bioetl.domain.value_objects import HashDigest

if TYPE_CHECKING:
    pass


class NormalizationConfigProviderProtocol(Protocol):
    """Provides normalization configuration context for services."""

    def get_normalization(self) -> Any:
        """Return normalization section."""

    def get_fields(self) -> list[dict[str, Any]]:
        """Return field configuration for normalization."""

    @property
    def serialization_mode(self) -> str:
        """Return configured serialization mode for nested structures."""


class HasherABC(ABC):
    """Low-level hashing abstraction.

    Provides primitive hashing operations used by HashServiceABC.
    Uses domain-level Record and TabularData instead of pandas types.
    Infrastructure implementations can work with pandas internally.

    Note:
        This is an internal abstraction. Prefer HashServiceABC for domain code.
    """

    @property
    def algorithm(self) -> str:
        """Return hashing algorithm identifier (e.g., 'blake2b_256')."""
        return "blake2b_256"

    @abstractmethod
    def compute_hash(self, record: Mapping[str, Any]) -> HashDigest:
        """Compute hash of a single record.

        Args:
            record: Record to hash (dict-like interface).

        Returns:
            HashDigest value object.
        """

    @abstractmethod
    def compute_hash_for_fields(
        self,
        record: Mapping[str, Any],
        fields: Sequence[str],
    ) -> HashDigest:
        """Compute hash of specified fields from a record.

        Args:
            record: Record containing fields.
            fields: Field names to include in hash.

        Returns:
            HashDigest value object.
        """


class NormalizationServiceABC(ABC):
    """Data normalization service.

    Provides batch and record-level normalization operations.
    Uses domain-level TabularData abstraction.
    """

    @abstractmethod
    def normalize(self, data: TabularData) -> MutableTabularData:
        """Normalize tabular data batch and coerce numeric columns.

        Args:
            data: Input tabular data.

        Returns:
            Normalized tabular data (may be new instance).
        """

    @abstractmethod
    def normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize a single record.

        Args:
            record: Record dictionary to normalize.

        Returns:
            Normalized record dictionary.
        """

    @abstractmethod
    def ensure_numeric_columns(self, data: TabularData) -> MutableTabularData:
        """Coerce numeric columns to appropriate types.

        Args:
            data: Input tabular data.

        Returns:
            Data with numeric columns coerced.
        """


class HashServiceABC(ABC):
    """Stateless service for computing deterministic hashes.

    Responsible for computing and adding hash columns to data.
    Does not contain stateful logic (indices, timestamps).

    Terminology (see module docstring for full mapping):
        fingerprint: Computes record_hash - hash of entire record.
        entity_key: Computes business_key_hash - hash of business key fields.

    Output columns (schema layer):
        hash_row: Contains the record_hash (fingerprint result).
        hash_business_key: Contains the business_key_hash (entity_key result).

    Example:
        >>> service: HashServiceABC = get_hash_service()
        >>> digest = service.compute_fingerprint({"id": 1, "name": "test"})
        >>> print(digest.value)  # hex string
    """

    @property
    def algorithm(self) -> str:
        """Return algorithm identifier (e.g., 'blake2b_256')."""
        return "blake2b_256"

    @abstractmethod
    def compute_fingerprint(self, record: Mapping[str, Any]) -> HashDigest:
        """Compute record_hash (fingerprint) of entire record.

        This produces the canonical record_hash value, stored in schema
        column ``hash_row``.

        Args:
            record: Record data as mapping (dict-like).

        Returns:
            HashDigest value object containing the record_hash.
        """

    @abstractmethod
    def compute_entity_key(
        self,
        record: Mapping[str, Any],
        key_fields: Sequence[str],
    ) -> HashDigest:
        """Compute business_key_hash (entity_key) from key fields.

        This produces the canonical business_key_hash value, stored in
        schema column ``hash_business_key``.

        Args:
            record: Record data as mapping.
            key_fields: Sequence of field names forming the business key.

        Returns:
            HashDigest value object containing the business_key_hash.
        """

    @abstractmethod
    def add_hashes_to_batch(
        self,
        records: RecordBatch,
        key_fields: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Add hash columns (record_hash, business_key_hash) to each record.

        This is the pandas-free version for processing record batches.

        Args:
            records: Sequence of records (Mapping[str, Any]).
            key_fields: Optional sequence of business key field names.

        Returns:
            List of dictionaries with added hash columns:
            - hash_row: record_hash (fingerprint) of entire record
            - hash_business_key: business_key_hash (or None if key_fields not provided)
        """

    def add_hash_columns(
        self,
        data: TabularData,
        business_key_cols: Sequence[str] | None = None,
    ) -> MutableTabularData:
        """Add hash columns (record_hash, business_key_hash) to tabular data.

        Adds columns:
            - hash_row: Contains record_hash (fingerprint)
            - hash_business_key: Contains business_key_hash (entity_key)

        This method works with TabularData abstraction (pandas-compatible).
        For pandas-free processing, use add_hashes_to_batch().

        Args:
            data: Input tabular data.
            business_key_cols: Optional sequence of business key column names.

        Returns:
            MutableTabularData with added hash columns.

        Note:
            Default implementation converts to records and back.
            Infrastructure may override for better performance.
        """
        # Infrastructure layer should provide optimized implementation
        # This default raises to force infrastructure override
        # Note: Default implementation would convert to records and back
        raise NotImplementedError(
            "Infrastructure must override add_hash_columns for TabularData support"
        )


class TimestampProviderABC(ABC):
    """
    Провайдер временных меток для извлечения данных.

    Обеспечивает детерминированный timestamp в рамках сессии.
    """

    @abstractmethod
    def get_extraction_timestamp(self) -> datetime:
        """Возвращает timestamp извлечения данных."""


class IndexGeneratorABC(ABC):
    """
    Генератор последовательных индексов для строк данных.

    Stateful: сохраняет текущее значение счётчика между вызовами.
    """

    @abstractmethod
    def next_index(self) -> int:
        """Возвращает следующий индекс и увеличивает счётчик."""

    @abstractmethod
    def reset(self) -> None:
        """Сбрасывает счётчик в начальное состояние."""


__all__ = [
    "HashDigest",
    "HasherABC",
    "HashServiceABC",
    "IndexGeneratorABC",
    "NormalizationConfig",
    "NormalizationConfigProviderProtocol",
    "NormalizationServiceABC",
    "TimestampProviderABC",
]
