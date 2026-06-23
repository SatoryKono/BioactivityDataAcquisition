"""Tests for ErrorClassifier."""

from __future__ import annotations

import pytest

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.types import ErrorType


pytestmark = pytest.mark.unit


class TestErrorClassifier:
    """Tests for the ErrorClassifier class."""

    @pytest.fixture
    def classifier(self) -> ErrorClassifier:
        """Create an ErrorClassifier instance."""
        return ErrorClassifier()

    def test_classify_schema_violation(self, classifier: ErrorClassifier) -> None:
        """Exceptions with 'Schema' in name should be SCHEMA_VIOLATION."""

        class SchemaError(Exception):
            pass

        class MySchemaValidationError(Exception):
            pass

        assert classifier.classify(SchemaError()) == ErrorType.SCHEMA_VIOLATION
        assert (
            classifier.classify(MySchemaValidationError()) == ErrorType.SCHEMA_VIOLATION
        )

    def test_classify_validation_error(self, classifier: ErrorClassifier) -> None:
        """Exceptions with 'Validation' in name should be SCHEMA_VIOLATION."""

        class ValidationError(Exception):
            pass

        class DataValidationFailed(Exception):
            pass

        assert classifier.classify(ValidationError()) == ErrorType.SCHEMA_VIOLATION
        assert classifier.classify(DataValidationFailed()) == ErrorType.SCHEMA_VIOLATION

    def test_classify_missing_field(self, classifier: ErrorClassifier) -> None:
        """Exceptions with 'Missing' in name should be MISSING_REQUIRED_FIELD."""

        class MissingFieldError(Exception):
            pass

        class MissingKeyError(Exception):
            pass

        assert (
            classifier.classify(MissingFieldError()) == ErrorType.MISSING_REQUIRED_FIELD
        )
        assert (
            classifier.classify(MissingKeyError()) == ErrorType.MISSING_REQUIRED_FIELD
        )

    def test_classify_required_error(self, classifier: ErrorClassifier) -> None:
        """Exceptions with 'Required' in name should be MISSING_REQUIRED_FIELD."""

        class RequiredFieldMissing(Exception):
            pass

        class RequiredValueError(Exception):
            pass

        assert (
            classifier.classify(RequiredFieldMissing())
            == ErrorType.MISSING_REQUIRED_FIELD
        )
        assert (
            classifier.classify(RequiredValueError())
            == ErrorType.MISSING_REQUIRED_FIELD
        )

    def test_classify_generic_error(self, classifier: ErrorClassifier) -> None:
        """Generic exceptions should be classified as INVALID_DATA."""
        assert classifier.classify(ValueError("bad value")) == ErrorType.INVALID_DATA
        assert classifier.classify(TypeError("wrong type")) == ErrorType.INVALID_DATA
        assert (
            classifier.classify(RuntimeError("runtime issue")) == ErrorType.INVALID_DATA
        )
        assert classifier.classify(UnicodeError("generic")) == ErrorType.INVALID_DATA

    def test_classify_builtin_exceptions(self, classifier: ErrorClassifier) -> None:
        """Built-in exceptions should be classified as INVALID_DATA."""
        assert classifier.classify(KeyError("key")) == ErrorType.INVALID_DATA
        assert classifier.classify(IndexError("index")) == ErrorType.INVALID_DATA
        assert classifier.classify(AttributeError("attr")) == ErrorType.INVALID_DATA

    def test_classifier_priority_schema_over_generic(
        self, classifier: ErrorClassifier
    ) -> None:
        """Schema-related keywords should take precedence."""

        class SchemaValidationError(Exception):
            """Has both Schema and Validation - should be SCHEMA_VIOLATION."""

            pass

        assert (
            classifier.classify(SchemaValidationError()) == ErrorType.SCHEMA_VIOLATION
        )
