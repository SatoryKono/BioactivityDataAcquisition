"""Domain-level transform contracts and DTOs.

Terminology:
    compute_row_fingerprint: Computes a hash of the entire row.
        Deprecated alias: hash_row (will be removed in v3.0).
    compute_entity_key: Computes a hash of the business key columns.
        Deprecated alias: hash_business_key (will be removed in v3.0).

Tabular Data Abstractions:
    This module uses domain-level abstractions (Record, TabularData) instead of
    pandas types. Infrastructure layer provides PandasAdapter implementations.

    See bioetl.domain.data for protocol definitions.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol
import warnings

# Import the canonical NormalizationConfig from configs.normalization
from bioetl.domain.configs.normalization import NormalizationConfig
from bioetl.domain.data import MutableTabularData, Record, TabularData

if TYPE_CHECKING:
    from collections.abc import Sequence


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
    """Row hashing abstraction.

    Uses domain-level Record and TabularData instead of pandas types.
    Infrastructure implementations can work with pandas internally.
    """

    def get_algorithm(self) -> str:
        """Return hashing algorithm name (default: blake2b_256)."""
        return "blake2b_256"

    @abstractmethod
    def compute_hash_row(self, row: Record) -> str:
        """Compute hash of a single record.

        Args:
            row: Record to hash (dict-like interface).

        Returns:
            Hex string hash of the record.
        """

    @abstractmethod
    def compute_hash_columns(
        self, data: TabularData, columns: list[str]
    ) -> "Sequence[str]":
        """Compute hash of specified columns for each row.

        Args:
            data: Tabular data to process.
            columns: Column names to include in hash.

        Returns:
            Sequence of hash strings, one per row.
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
    """Stateless hash computation service.

    Responsible for computing and adding hash columns to tabular data.
    Does not contain stateful logic (indices, timestamps).

    Terminology:
        compute_row_fingerprint: Canonical name for row hashing.
        compute_entity_key: Canonical name for business key hashing.
        hash_row: Deprecated alias for compute_row_fingerprint.
        hash_business_key: Deprecated alias for compute_entity_key.
    """

    @abstractmethod
    def compute_row_fingerprint(self, row: dict[str, Any]) -> str:
        """Compute hash fingerprint of a row as complete object.

        Args:
            row: Row data as dictionary.

        Returns:
            Hex string hash of the row.

        Note:
            This is the canonical method name for row hashing.
        """

    @abstractmethod
    def compute_entity_key(self, row: dict[str, Any], key_columns: list[str]) -> str:
        """Compute hash of business key columns.

        Args:
            row: Row data as dictionary.
            key_columns: List of columns forming the business key.

        Returns:
            Hex string hash of the business key.

        Note:
            This is the canonical method name for business key hashing.
        """

    @abstractmethod
    def add_hash_columns(
        self, data: TabularData, business_key_cols: list[str] | None = None
    ) -> MutableTabularData:
        """Add hash_row and hash_business_key columns to data.

        Args:
            data: Input tabular data.
            business_key_cols: Optional list of business key column names.

        Returns:
            Data with added hash columns.
        """

    # =========================================================================
    # Deprecated aliases (will be removed in v3.0)
    # =========================================================================

    def hash_row(self, row: dict) -> str:
        """Deprecated: Use compute_row_fingerprint() instead.

        Will be removed in v3.0.
        """
        warnings.warn(
            "hash_row() is deprecated, use compute_row_fingerprint() instead. "
            "Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.compute_row_fingerprint(row)

    def hash_business_key(self, row: dict, key_columns: list[str]) -> str:
        """Deprecated: Use compute_entity_key() instead.

        Will be removed in v3.0.
        """
        warnings.warn(
            "hash_business_key() is deprecated, use compute_entity_key() instead. "
            "Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.compute_entity_key(row, key_columns)


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
    "NormalizationConfig",
    "NormalizationConfigProviderProtocol",
    "HasherABC",
    "NormalizationServiceABC",
    "HashServiceABC",
    "TimestampProviderABC",
    "IndexGeneratorABC",
]
