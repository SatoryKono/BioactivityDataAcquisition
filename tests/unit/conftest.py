"""Unit-test fixtures for explicit local seams."""

from __future__ import annotations

import pytest

from tests.helpers.publication_type_classification import (
    initialize_test_publication_type_classification,
)


@pytest.fixture(scope="module")
def publication_type_classification_data() -> None:
    """Initialize classification lookups explicitly for unit publication suites."""
    initialize_test_publication_type_classification()
