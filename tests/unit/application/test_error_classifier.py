"""Unit tests for the ErrorClassifier class."""

from __future__ import annotations

import pytest

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.types import ErrorType


@pytest.fixture
def classifier():
    """Fixture for an ErrorClassifier."""
    return ErrorClassifier()


def test_classify_schema_violation(classifier):
    """Test that SchemaError is classified correctly."""

    class SchemaError(Exception):
        pass

    error = SchemaError()
    assert classifier.classify(error) == ErrorType.SCHEMA_VIOLATION


def test_classify_validation_error(classifier):
    """Test that ValidationError is classified correctly."""

    class ValidationError(Exception):
        pass

    error = ValidationError()
    assert classifier.classify(error) == ErrorType.SCHEMA_VIOLATION


def test_classify_missing_field(classifier):
    """Test that MissingField error is classified correctly."""

    class MissingFieldError(Exception):
        pass

    error = MissingFieldError()
    assert classifier.classify(error) == ErrorType.MISSING_REQUIRED_FIELD


def test_classify_required_field(classifier):
    """Test that RequiredFieldError is classified correctly."""

    class RequiredFieldError(Exception):
        pass

    error = RequiredFieldError()
    assert classifier.classify(error) == ErrorType.MISSING_REQUIRED_FIELD


def test_classify_invalid_data(classifier):
    """Test that a generic error is classified as invalid data."""
    error = ValueError()
    assert classifier.classify(error) == ErrorType.INVALID_DATA
