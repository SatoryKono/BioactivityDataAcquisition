"""Storage-related exceptions."""

from bioetl.domain.exceptions import InfrastructureError


class StorageError(InfrastructureError):
    """Base class for storage exceptions."""


class StorageWriteError(StorageError):
    """Raised when writing to storage fails."""


class StorageReadError(StorageError):
    """Raised when reading from storage fails."""


class TableNotFoundError(StorageError):
    """Raised when a table is not found."""


class SchemaViolationError(StorageError):
    """Raised when schema validation fails."""
