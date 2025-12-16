"""Storage layer exceptions.

Implements structured error handling for storage operations.
"""


class StorageError(Exception):
    """Base exception for all storage errors."""

    pass


class BucketNotFoundError(StorageError):
    """Raised when S3 bucket does not exist."""

    def __init__(self, bucket: str):
        self.bucket = bucket
        super().__init__(f"Bucket '{bucket}' not found")


class UploadError(StorageError):
    """Raised when upload to S3 fails."""

    def __init__(self, key: str, reason: str):
        self.key = key
        self.reason = reason
        super().__init__(f"Failed to upload '{key}': {reason}")


class SchemaValidationError(StorageError):
    """Raised when data does not match expected schema."""

    def __init__(self, table: str, errors: list[str]):
        self.table = table
        self.errors = errors
        super().__init__(f"Schema validation failed for '{table}': {errors}")


class TableNotFoundError(StorageError):
    """Raised when Delta table does not exist."""

    def __init__(self, table_path: str):
        self.table_path = table_path
        super().__init__(f"Table not found: '{table_path}'")


class MergeConflictError(StorageError):
    """Raised when Delta merge has conflicts."""

    def __init__(self, table: str, conflicts: int):
        self.table = table
        self.conflicts = conflicts
        super().__init__(f"Merge conflict in '{table}': {conflicts} conflicts")
