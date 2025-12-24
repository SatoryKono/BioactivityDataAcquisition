from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.domain.error_classifier import _ERROR_KEYWORDS, ErrorClassifier
from bioetl.domain.exceptions import (
    ApiError,
    BioETLError,
    BucketNotFoundError,
    CheckpointConflictError,
    ChemblApiError,
    CircuitBreakerOpenError,
    CriticalError,
    DataQualityError,
    DataQualityThresholdError,
    InvalidDataFormatError,
    LockAcquisitionError,
    LockLostError,
    MergeConflictError,
    MissingRequiredFieldError,
    NetworkError,
    RateLimitError,
    RecoverableError,
    RetryExhaustedError,
    SchemaViolationError,
    StorageError,
    TableNotFoundError,
    UploadError,
)
from bioetl.domain.types import ErrorType


class TestExceptions:
    def test_base_exceptions_inheritance(self) -> None:
        """Test inheritance hierarchy."""
        assert issubclass(CriticalError, BioETLError)
        assert issubclass(RecoverableError, BioETLError)
        assert issubclass(DataQualityError, BioETLError)

    def test_lock_lost_error_without_run_id(self) -> None:
        """Test LockLostError without run_id."""
        e = LockLostError("my_key")
        assert e.key == "my_key"
        assert e.run_id is None
        assert "Lock lost: my_key" in str(e)
        assert "run_id" not in str(e)

    def test_lock_acquisition_error_without_owner(self) -> None:
        """Test LockAcquisitionError without owner."""
        e = LockAcquisitionError("my_key")
        assert e.key == "my_key"
        assert e.current_owner is None
        assert "Failed to acquire lock: my_key" in str(e)
        assert "owned by" not in str(e)

    def test_api_error_without_status_code(self) -> None:
        """Test ApiError without status code."""
        e = ApiError("Something went wrong")
        assert e.message == "Something went wrong"
        assert e.status_code is None
        assert str(e) == "Something went wrong"

    def test_retry_exhausted_error_without_last_error(self) -> None:
        """Test RetryExhaustedError without last_error."""
        e = RetryExhaustedError("http://example.com/api", 5)
        assert e.url == "http://example.com/api"
        assert e.attempts == 5
        assert e.last_error is None
        assert "Exhausted 5 retry attempts" in str(e)

    def test_missing_required_field_without_record_id(self) -> None:
        """Test MissingRequiredFieldError without record_id."""
        e = MissingRequiredFieldError("activity_id")
        assert e.field == "activity_id"
        assert e.record_id is None
        assert "Missing required field: activity_id" in str(e)
        assert "record_id" not in str(e)

    def test_chembl_api_error_inheritance(self) -> None:
        """Test ChemblApiError inherits from ApiError."""
        e = ChemblApiError("ChEMBL service unavailable", 503)
        assert isinstance(e, ApiError)
        assert isinstance(e, RecoverableError)
        assert e.status_code == 503
        assert "[503]" in str(e)

    def test_storage_error_inheritance(self) -> None:
        """Test StorageError inheritance."""
        e = StorageError("Storage operation failed")
        assert isinstance(e, RecoverableError)
        assert isinstance(e, BioETLError)

    def test_data_quality_threshold_error(self) -> None:
        """Test DataQualityThresholdError."""
        e = DataQualityThresholdError(error_rate=0.25, threshold=0.20)
        assert e.error_rate == 0.25
        assert e.threshold == 0.20
        assert "25.00% errors" in str(e)
        assert "20.00%" in str(e)
        assert isinstance(e, BioETLError)

    def test_critical_errors(self) -> None:
        """Test initialization of critical errors."""
        e1 = LockLostError("key1", "run1")
        assert "Lock lost: key1 (run_id=run1)" in str(e1)

        e2 = LockAcquisitionError("key1", "owner1")
        assert "Failed to acquire lock: key1 (owned by owner1)" in str(e2)

        e3 = CheckpointConflictError("pipe1", "msg")
        assert "Checkpoint conflict in 'pipe1': msg" in str(e3)

        e4 = MergeConflictError("table1", 5)
        assert "Merge conflict in 'table1': 5 conflicts" in str(e4)

    def test_recoverable_errors(self) -> None:
        """Test initialization of recoverable errors."""
        e1 = RateLimitError("prov1", 30.0)
        assert "Retry after 30.0s" in str(e1)

        e2 = RetryExhaustedError("url1", 3, ValueError("foo"))
        assert "Exhausted 3 retry attempts for url1: foo" in str(e2)

        e3 = CircuitBreakerOpenError("prov1", 60.0)
        assert "Circuit breaker open for prov1" in str(e3)

        e4 = ApiError("fail", 500)
        assert "[500] fail" in str(e4)

    def test_storage_errors(self) -> None:
        """Test initialization of storage errors."""
        e1 = BucketNotFoundError("bucket1")
        assert "Bucket 'bucket1' not found" in str(e1)

        e2 = UploadError("key1", "reason1")
        assert "Failed to upload 'key1': reason1" in str(e2)

        e3 = TableNotFoundError("path1")
        assert "Table not found: 'path1'" in str(e3)

    def test_data_quality_errors(self) -> None:
        """Test initialization of data quality errors."""
        e1 = SchemaViolationError("t1", ["e1", "e2"])
        assert "Schema validation failed for 't1': ['e1', 'e2']" in str(e1)

        e2 = MissingRequiredFieldError("f1", "r1")
        assert "Missing required field: f1 (record_id=r1)" in str(e2)

        e3 = InvalidDataFormatError("f1", "val", "fmt")
        assert "Invalid format for 'f1': got 'val', expected fmt" in str(e3)


class TestErrorClassifier:
    @pytest.fixture
    def classifier(self) -> ErrorClassifier:
        return ErrorClassifier()

    @pytest.mark.parametrize(
        "error,expected_type",
        [
            # Critical / Infrastructure
            (LockLostError("k"), ErrorType.LOCK_LOST),
            (LockAcquisitionError("k"), ErrorType.LOCK_LOST),
            (CheckpointConflictError("p", "m"), ErrorType.DB_UNAVAILABLE),
            (MergeConflictError("t", 1), ErrorType.DB_UNAVAILABLE),
            # Recoverable / Network
            (RateLimitError("p", 1.0), ErrorType.RATE_LIMIT),
            (CircuitBreakerOpenError("p", 1.0), ErrorType.TIMEOUT),
            (RetryExhaustedError("u", 1), ErrorType.NETWORK_ERROR),
            (
                ApiError("fail"),
                ErrorType.NETWORK_ERROR,
            ),  # Fallback hierarchy -> RecoverableError -> NETWORK_ERROR
            # Data Quality
            (SchemaViolationError("t", []), ErrorType.SCHEMA_VIOLATION),
            (MissingRequiredFieldError("f"), ErrorType.MISSING_REQUIRED_FIELD),
            (InvalidDataFormatError("f", "v", "e"), ErrorType.INVALID_DATA),
        ],
    )
    def test_classify_domain_errors(
        self, classifier: ErrorClassifier, error: Exception, expected_type: ErrorType
    ) -> None:
        """Test classification of known domain exceptions."""
        assert classifier.classify(error) == expected_type

    @pytest.mark.parametrize(
        "error_name,expected_type",
        [
            ("LockLostException", ErrorType.LOCK_LOST),
            ("BucketNotFoundException", ErrorType.DB_UNAVAILABLE),
            ("AuthFailureError", ErrorType.AUTH_FAILURE),
            ("TooManyRequestsError", ErrorType.RATE_LIMIT),
            ("TimeoutError", ErrorType.TIMEOUT),
            ("NetworkError", ErrorType.NETWORK_ERROR),
            ("SchemaValidationError", ErrorType.SCHEMA_VIOLATION),
            ("MissingRequiredField", ErrorType.MISSING_REQUIRED_FIELD),
            ("UnknownError", ErrorType.INVALID_DATA),
        ],
    )
    def test_classify_legacy_errors(
        self, classifier: ErrorClassifier, error_name: str, expected_type: ErrorType
    ) -> None:
        """Test keyword-based classification for legacy/external exceptions."""
        # Dynamically create exception class
        error_cls = type(error_name, (Exception,), {})
        assert classifier.classify(error_cls("msg")) == expected_type

    def test_classify_hierarchy_fallback(self, classifier: ErrorClassifier) -> None:
        """Test fallback to hierarchy when keywords don't match."""

        class CustomCritical(CriticalError):
            pass

        class CustomRecoverable(RecoverableError):
            pass

        class CustomDQ(DataQualityError):
            pass

        assert classifier.classify(CustomCritical("msg")) == ErrorType.DB_UNAVAILABLE
        assert classifier.classify(CustomRecoverable("msg")) == ErrorType.NETWORK_ERROR
        assert classifier.classify(CustomDQ("msg")) == ErrorType.INVALID_DATA

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.text())
    def test_classify_unknown_exception(
        self, classifier: ErrorClassifier, msg: str
    ) -> None:
        """Property-based test: Any unknown exception maps to INVALID_DATA unless keyword matched."""
        e = ValueError(msg)
        # Check against exposed internal keyword list
        if not any(k in "ValueError" for ks, _ in _ERROR_KEYWORDS for k in ks):
            assert classifier.classify(e) == ErrorType.INVALID_DATA


class TestErrorContext:
    """Tests for unified error context API (BioETLError.context)."""

    def test_context_collects_public_attributes(self) -> None:
        """The context property should collect all public instance attributes."""
        err = RateLimitError(provider="chembl", retry_after=60.0)
        ctx = err.context

        assert ctx["provider"] == "chembl"
        assert ctx["retry_after"] == 60.0
        assert len(ctx) == 2

    def test_context_excludes_private_attributes(self) -> None:
        """The context property should exclude private attributes."""
        err = ApiError("test", status_code=500)
        # Manually add a private attribute
        err._internal = "should not appear"  # type: ignore[attr-defined]

        ctx = err.context
        assert "_internal" not in ctx
        assert "message" in ctx
        assert "status_code" in ctx

    def test_context_with_none_values(self) -> None:
        """The context should include None values if they are set."""
        err = LockAcquisitionError("my_key", current_owner=None)
        ctx = err.context

        assert ctx["key"] == "my_key"
        assert ctx["current_owner"] is None

    def test_context_on_base_error(self) -> None:
        """Base BioETLError should have empty context if no attrs set."""
        # Create a simple subclass without custom __init__
        class SimpleError(BioETLError):
            pass

        err = SimpleError("test message")
        assert err.context == {}

    def test_with_context_adds_attributes(self) -> None:
        """with_context should add extra attributes to the exception."""
        err = ApiError("Connection failed", status_code=500)
        err = err.with_context(endpoint="/api/v1/data", attempt=3)

        ctx = err.context
        assert ctx["endpoint"] == "/api/v1/data"
        assert ctx["attempt"] == 3
        assert ctx["status_code"] == 500

    def test_with_context_returns_self(self) -> None:
        """with_context should return the same exception instance."""
        err = StorageError("test")
        result = err.with_context(key="value")

        assert result is err

    def test_with_context_chainable(self) -> None:
        """with_context should be chainable."""
        err = (
            NetworkError("Connection refused")
            .with_context(host="localhost", port=8080)
            .with_context(retry_count=3)
        )

        ctx = err.context
        assert ctx["host"] == "localhost"
        assert ctx["port"] == 8080
        assert ctx["retry_count"] == 3

    def test_context_inheritance(self) -> None:
        """Subclass context should include parent class attributes."""
        err = ChemblApiError("Service unavailable", status_code=503)
        ctx = err.context

        # ChemblApiError inherits from ApiError which sets message and status_code
        assert ctx["message"] == "Service unavailable"
        assert ctx["status_code"] == 503

    @pytest.mark.parametrize(
        "error_cls,args,expected_keys",
        [
            (LockLostError, ("key1", "run1"), {"key", "run_id"}),
            (RateLimitError, ("provider1", 30.0), {"provider", "retry_after"}),
            (SchemaViolationError, ("table1", ["e1"]), {"table", "errors"}),
            (BucketNotFoundError, ("bucket1",), {"bucket"}),
            (RetryExhaustedError, ("url1", 3, None), {"url", "attempts", "last_error"}),
        ],
    )
    def test_context_for_various_errors(
        self, error_cls: type, args: tuple, expected_keys: set[str]
    ) -> None:
        """Verify context extraction for various error types."""
        err = error_cls(*args)
        ctx = err.context

        assert set(ctx.keys()) == expected_keys
