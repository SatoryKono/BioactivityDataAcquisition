"""Unit-test fixtures for explicit local seams."""

from __future__ import annotations

import pytest

from tests.helpers.publication_type_classification import (
    initialize_test_publication_type_classification,
)


@pytest.fixture(autouse=True)
def target_classification_working_directory(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run target migration temporary workspaces inside the CWD trust boundary."""
    target_tests = {
        "test_target_migration_binding.py",
        "test_target_migration_rehearsal.py",
        "test_classification_evidence_boundaries.py",
        "test_target_fk_restoration.py",
        "test_target_candidate_builder.py",
        "test_target_classification_migration.py",
    }
    if request.path.name in target_tests and "tmp_path" in request.fixturenames:
        monkeypatch.chdir(request.getfixturevalue("tmp_path"))


@pytest.fixture(scope="module")
def publication_type_classification_data() -> None:
    """Initialize classification lookups explicitly for unit publication suites."""
    initialize_test_publication_type_classification()
