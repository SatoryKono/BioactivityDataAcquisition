# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for storage-related exceptions.

Coverage target: >90%
"""

from __future__ import annotations

import pytest

from bioetl.domain.exceptions.infrastructure import (
    BronzeValidationError,
    BucketNotFoundError,
    DeltaOptimizeError,
    DeltaSchemaValidationError,
    DeltaTransactionError,
    DeltaWriteConflictError,
    SchemaEvolutionError,
    StorageError,
    StorageQuotaExceededError,
    TableNotFoundError,
    UploadError,
    _build_schema_error_message,
    _build_schema_validation_message,
    _format_column_diff,
    _format_type_mismatches,
)
from bioetl.domain.exceptions.base import CriticalError, RecoverableError
from bioetl.domain.types import ErrorType

pytestmark = pytest.mark.unit


class TestStorageError:
    """Tests for base StorageError."""

    def test_storage_error_inherits_from_recoverable_error(self) -> None:
        """Test StorageError inheritance."""
        error = StorageError("Test storage error")
        assert isinstance(error, RecoverableError)
        assert error.error_type == ErrorType.NETWORK_ERROR

    def test_storage_error_message(self) -> None:
        """Test StorageError message."""
        error = StorageError("Test message")
        assert str(error) == "Test message"


class TestBucketNotFoundError:
    """Tests for BucketNotFoundError."""

    def test_bucket_not_found_error_creation(self) -> None:
        """Test BucketNotFoundError initialization."""
        error = BucketNotFoundError("my-bucket")
        assert error.bucket == "my-bucket"
        assert "Bucket 'my-bucket' not found" in str(error)
        assert error.error_type == ErrorType.DB_UNAVAILABLE

    def test_bucket_not_found_error_inheritance(self) -> None:
        """Test BucketNotFoundError inherits from StorageError."""
        error = BucketNotFoundError("test-bucket")
        assert isinstance(error, StorageError)


class TestUploadError:
    """Tests for UploadError."""

    def test_upload_error_creation(self) -> None:
        """Test UploadError initialization."""
        error = UploadError("s3://bucket/key.json", "Network timeout")
        assert error.key == "s3://bucket/key.json"
        assert error.reason == "Network timeout"
        assert "Failed to upload 's3://bucket/key.json': Network timeout" in str(error)

    def test_upload_error_type(self) -> None:
        """Test UploadError error type."""
        error = UploadError("key", "reason")
        assert error.error_type == ErrorType.NETWORK_ERROR


class TestTableNotFoundError:
    """Tests for TableNotFoundError."""

    def test_table_not_found_error_creation(self) -> None:
        """Test TableNotFoundError initialization."""
        error = TableNotFoundError("/data/delta/silver/chembl_activity")
        assert error.table_path == "/data/delta/silver/chembl_activity"
        assert "Table not found: '/data/delta/silver/chembl_activity'" in str(error)

    def test_table_not_found_error_type(self) -> None:
        """Test TableNotFoundError error type."""
        error = TableNotFoundError("/path")
        assert error.error_type == ErrorType.DB_UNAVAILABLE


class TestSchemaEvolutionError:
    """Tests for SchemaEvolutionError."""

    def test_schema_evolution_error_with_new_fields(self) -> None:
        """Test SchemaEvolutionError with new fields."""
        error = SchemaEvolutionError(
            table="chembl_activity",
            new_fields={"new_col1", "new_col2"},
        )
        assert error.table == "chembl_activity"
        assert error.new_fields == {"new_col1", "new_col2"}
        assert error.removed_fields == set()
        assert "Schema drift detected for 'chembl_activity'" in str(error)
        assert "new_col1" in str(error) or "new_col2" in str(error)

    def test_schema_evolution_error_with_removed_fields(self) -> None:
        """Test SchemaEvolutionError with removed fields."""
        error = SchemaEvolutionError(
            table="test_table",
            removed_fields={"old_col"},
        )
        assert error.removed_fields == {"old_col"}
        assert "removed fields" in str(error)

    def test_schema_evolution_error_with_both_changes(self) -> None:
        """Test SchemaEvolutionError with both new and removed fields."""
        error = SchemaEvolutionError(
            table="test_table",
            new_fields={"new1"},
            removed_fields={"old1"},
        )
        assert "new fields" in str(error)
        assert "removed fields" in str(error)

    def test_schema_evolution_error_with_none_fields(self) -> None:
        """Test SchemaEvolutionError with None fields (defaults to empty set)."""
        error = SchemaEvolutionError(table="test_table")
        assert error.new_fields == set()
        assert error.removed_fields == set()
        assert "Schema drift detected for 'test_table'" in str(error)

    def test_schema_evolution_error_type(self) -> None:
        """Test SchemaEvolutionError error type."""
        error = SchemaEvolutionError(table="test")
        assert error.error_type == ErrorType.SCHEMA_EVOLUTION


class TestBuildSchemaErrorMessage:
    """Tests for _build_schema_error_message helper."""

    def test_build_schema_error_message_with_new_fields(self) -> None:
        """Test message with only new fields."""
        msg = _build_schema_error_message(
            table="test",
            new_fields={"col_a", "col_b"},
            removed_fields=set(),
        )
        assert "Schema drift detected for 'test'" in msg
        assert "new fields" in msg

    def test_build_schema_error_message_with_removed_fields(self) -> None:
        """Test message with only removed fields."""
        msg = _build_schema_error_message(
            table="test",
            new_fields=set(),
            removed_fields={"old_col"},
        )
        assert "removed fields" in msg

    def test_build_schema_error_message_with_empty_sets(self) -> None:
        """Test message with empty field sets."""
        msg = _build_schema_error_message(
            table="test",
            new_fields=set(),
            removed_fields=set(),
        )
        assert msg == "Schema drift detected for 'test'"


class TestBronzeValidationError:
    """Tests for BronzeValidationError."""

    def test_bronze_validation_error_basic(self) -> None:
        """Test BronzeValidationError with basic message."""
        error = BronzeValidationError("Invalid JSON bytes")
        assert "Invalid JSON bytes" in str(error)
        assert error.record_index is None
        assert error.original_error is None

    def test_bronze_validation_error_with_record_index(self) -> None:
        """Test BronzeValidationError with record index."""
        error = BronzeValidationError(
            message="Invalid record",
            record_index=5,
        )
        assert error.record_index == 5
        assert "record_index=5" in str(error)

    def test_bronze_validation_error_with_original_error(self) -> None:
        """Test BronzeValidationError with original error."""
        error = BronzeValidationError(
            message="Parse failed",
            original_error="Unexpected token at position 42",
        )
        assert error.original_error == "Unexpected token at position 42"
        assert "error=Unexpected token" in str(error)

    def test_bronze_validation_error_with_all_params(self) -> None:
        """Test BronzeValidationError with all parameters."""
        error = BronzeValidationError(
            message="Validation failed",
            record_index=10,
            original_error="JSON decode error",
        )
        msg = str(error)
        assert "Validation failed" in msg
        assert "record_index=10" in msg
        assert "error=JSON decode error" in msg

    def test_bronze_validation_error_type(self) -> None:
        """Test BronzeValidationError error type."""
        error = BronzeValidationError("test")
        assert error.error_type == ErrorType.INVALID_DATA


class TestDeltaWriteConflictError:
    """Tests for DeltaWriteConflictError."""

    def test_delta_write_conflict_error_basic(self) -> None:
        """Test DeltaWriteConflictError with basic params."""
        error = DeltaWriteConflictError(table_path="/data/silver/table")
        assert error.table_path == "/data/silver/table"
        assert error.operation == "write"
        assert error.conflicting_version is None
        assert "Delta write conflict on '/data/silver/table'" in str(error)

    def test_delta_write_conflict_error_with_operation(self) -> None:
        """Test DeltaWriteConflictError with custom operation."""
        error = DeltaWriteConflictError(
            table_path="/data/table",
            operation="merge",
        )
        assert error.operation == "merge"
        assert "during merge" in str(error)

    def test_delta_write_conflict_error_with_version(self) -> None:
        """Test DeltaWriteConflictError with conflicting version."""
        error = DeltaWriteConflictError(
            table_path="/data/table",
            operation="delete",
            conflicting_version=42,
        )
        assert error.conflicting_version == 42
        assert "(conflicting version: 42)" in str(error)

    def test_delta_write_conflict_error_inheritance(self) -> None:
        """Test DeltaWriteConflictError inherits from StorageError."""
        error = DeltaWriteConflictError(table_path="/path")
        assert isinstance(error, StorageError)
        assert isinstance(error, RecoverableError)


class TestDeltaTransactionError:
    """Tests for DeltaTransactionError."""

    def test_delta_transaction_error_basic(self) -> None:
        """Test DeltaTransactionError with basic params."""
        error = DeltaTransactionError(
            table_path="/data/table",
            reason="Transaction log corrupted",
        )
        assert error.table_path == "/data/table"
        assert error.reason == "Transaction log corrupted"
        assert error.version is None
        assert "Delta transaction failed on '/data/table'" in str(error)

    def test_delta_transaction_error_with_version(self) -> None:
        """Test DeltaTransactionError with version."""
        error = DeltaTransactionError(
            table_path="/data/table",
            reason="Commit failed",
            version=15,
        )
        assert error.version == 15
        assert "(version: 15)" in str(error)

    def test_delta_transaction_error_is_critical(self) -> None:
        """Test DeltaTransactionError is a CriticalError."""
        error = DeltaTransactionError(table_path="/path", reason="test")
        assert isinstance(error, CriticalError)
        assert error.error_type == ErrorType.DB_UNAVAILABLE


class TestFormatColumnDiff:
    """Tests for _format_column_diff helper."""

    def test_format_column_diff_with_missing(self) -> None:
        """Test formatting missing columns."""
        parts = _format_column_diff(
            expected_columns=["a", "b", "c"],
            actual_columns=["a"],
        )
        assert len(parts) == 1
        assert "missing columns" in parts[0]

    def test_format_column_diff_with_extra(self) -> None:
        """Test formatting extra columns."""
        parts = _format_column_diff(
            expected_columns=["a"],
            actual_columns=["a", "b", "c"],
        )
        assert len(parts) == 1
        assert "unexpected columns" in parts[0]

    def test_format_column_diff_with_both(self) -> None:
        """Test formatting both missing and extra columns."""
        parts = _format_column_diff(
            expected_columns=["a", "b"],
            actual_columns=["a", "c"],
        )
        assert len(parts) == 2

    def test_format_column_diff_no_diff(self) -> None:
        """Test formatting when no differences."""
        parts = _format_column_diff(
            expected_columns=["a", "b"],
            actual_columns=["a", "b"],
        )
        assert len(parts) == 0


class TestFormatTypeMismatches:
    """Tests for _format_type_mismatches helper."""

    def test_format_type_mismatches(self) -> None:
        """Test formatting type mismatches."""
        msg = _format_type_mismatches(
            {
                "col_a": ("int64", "string"),
                "col_b": ("float64", "int32"),
            }
        )
        assert "type mismatches" in msg
        assert "col_a: expected int64, got string" in msg
        assert "col_b: expected float64, got int32" in msg

    def test_format_type_mismatches_single(self) -> None:
        """Test formatting single type mismatch."""
        msg = _format_type_mismatches({"col": ("expected", "actual")})
        assert "col: expected expected, got actual" in msg


class TestBuildSchemaValidationMessage:
    """Tests for _build_schema_validation_message helper."""

    def test_build_schema_validation_message_with_columns(self) -> None:
        """Test message with column diff."""
        msg = _build_schema_validation_message(
            table_path="/path/table",
            expected_columns=["a", "b"],
            actual_columns=["a", "c"],
            type_mismatches={},
        )
        assert "Schema validation failed for '/path/table'" in msg

    def test_build_schema_validation_message_with_types(self) -> None:
        """Test message with type mismatches."""
        msg = _build_schema_validation_message(
            table_path="/path/table",
            expected_columns=[],
            actual_columns=[],
            type_mismatches={"col": ("int", "str")},
        )
        assert "type mismatches" in msg

    def test_build_schema_validation_message_empty(self) -> None:
        """Test message with empty params."""
        msg = _build_schema_validation_message(
            table_path="/path/table",
            expected_columns=[],
            actual_columns=[],
            type_mismatches={},
        )
        assert "Schema validation failed for '/path/table'" in msg


class TestDeltaSchemaValidationError:
    """Tests for DeltaSchemaValidationError."""

    def test_delta_schema_validation_error_basic(self) -> None:
        """Test DeltaSchemaValidationError with basic params."""
        error = DeltaSchemaValidationError(table_path="/data/gold/table")
        assert error.table_path == "/data/gold/table"
        assert error.expected_columns == []
        assert error.actual_columns == []
        assert error.type_mismatches == {}

    def test_delta_schema_validation_error_with_columns(self) -> None:
        """Test DeltaSchemaValidationError with column mismatch."""
        error = DeltaSchemaValidationError(
            table_path="/data/table",
            expected_columns=["a", "b", "c"],
            actual_columns=["a", "d"],
        )
        assert error.expected_columns == ["a", "b", "c"]
        assert error.actual_columns == ["a", "d"]
        msg = str(error)
        assert "missing columns" in msg or "unexpected columns" in msg

    def test_delta_schema_validation_error_with_type_mismatches(self) -> None:
        """Test DeltaSchemaValidationError with type mismatches."""
        error = DeltaSchemaValidationError(
            table_path="/data/table",
            type_mismatches={"id": ("int64", "string")},
        )
        assert "id" in error.type_mismatches
        assert "type mismatches" in str(error)

    def test_delta_schema_validation_error_is_critical(self) -> None:
        """Test DeltaSchemaValidationError is a CriticalError."""
        error = DeltaSchemaValidationError(table_path="/path")
        assert isinstance(error, CriticalError)
        assert error.error_type == ErrorType.SCHEMA_MISMATCH_GOLD


class TestDeltaOptimizeError:
    """Tests for DeltaOptimizeError."""

    def test_delta_optimize_error_vacuum(self) -> None:
        """Test DeltaOptimizeError for vacuum operation."""
        error = DeltaOptimizeError(
            table_path="/data/table",
            operation="vacuum",
            reason="Files in use",
        )
        assert error.table_path == "/data/table"
        assert error.operation == "vacuum"
        assert error.reason == "Files in use"
        assert "Delta vacuum failed on '/data/table': Files in use" in str(error)

    def test_delta_optimize_error_optimize(self) -> None:
        """Test DeltaOptimizeError for optimize operation."""
        error = DeltaOptimizeError(
            table_path="/data/table",
            operation="optimize",
            reason="Insufficient memory",
        )
        assert "Delta optimize failed" in str(error)

    def test_delta_optimize_error_is_recoverable(self) -> None:
        """Test DeltaOptimizeError is recoverable."""
        error = DeltaOptimizeError(
            table_path="/path", operation="vacuum", reason="test"
        )
        assert isinstance(error, StorageError)
        assert isinstance(error, RecoverableError)


class TestStorageQuotaExceededError:
    """Tests for StorageQuotaExceededError."""

    def test_storage_quota_exceeded_error_basic(self) -> None:
        """Test StorageQuotaExceededError with basic params."""
        error = StorageQuotaExceededError(path="/data/storage")
        assert error.path == "/data/storage"
        assert error.quota_bytes is None
        assert error.used_bytes is None
        assert "Storage quota exceeded for '/data/storage'" in str(error)

    def test_storage_quota_exceeded_error_with_details(self) -> None:
        """Test StorageQuotaExceededError with quota details."""
        error = StorageQuotaExceededError(
            path="/data/storage",
            quota_bytes=1_000_000_000,  # 1GB
            used_bytes=1_200_000_000,  # 1.2GB
        )
        assert error.quota_bytes == 1_000_000_000
        assert error.used_bytes == 1_200_000_000
        msg = str(error)
        assert "used:" in msg
        assert "quota:" in msg
        assert "bytes" in msg

    def test_storage_quota_exceeded_error_is_critical(self) -> None:
        """Test StorageQuotaExceededError is a CriticalError."""
        error = StorageQuotaExceededError(path="/path")
        assert isinstance(error, CriticalError)
        assert error.error_type == ErrorType.DB_UNAVAILABLE


class TestErrorTypeConsistency:
    """Tests for error type consistency across exceptions."""

    @pytest.mark.parametrize(
        "error_cls,args,expected_type",
        [
            (StorageError, ("msg",), ErrorType.NETWORK_ERROR),
            (BucketNotFoundError, ("bucket",), ErrorType.DB_UNAVAILABLE),
            (UploadError, ("key", "reason"), ErrorType.NETWORK_ERROR),
            (TableNotFoundError, ("path",), ErrorType.DB_UNAVAILABLE),
            (SchemaEvolutionError, ("table",), ErrorType.SCHEMA_EVOLUTION),
            (BronzeValidationError, ("msg",), ErrorType.INVALID_DATA),
            (DeltaWriteConflictError, ("/path",), ErrorType.NETWORK_ERROR),
            (DeltaTransactionError, ("/path", "reason"), ErrorType.DB_UNAVAILABLE),
            (DeltaSchemaValidationError, ("/path",), ErrorType.SCHEMA_MISMATCH_GOLD),
            (
                DeltaOptimizeError,
                ("/path", "vacuum", "reason"),
                ErrorType.NETWORK_ERROR,
            ),
            (StorageQuotaExceededError, ("/path",), ErrorType.DB_UNAVAILABLE),
        ],
    )
    def test_error_types_match_expected(
        self, error_cls: type, args: tuple, expected_type: ErrorType
    ) -> None:
        """Test each exception has the correct error_type."""
        error = error_cls(*args)
        assert error.error_type == expected_type
