"""Tests for the baseline project-memory scaffold validator."""

from __future__ import annotations

from memory.resources import (
    REQUIRED_CATALOG_FILES,
    REQUIRED_POLICY_FILES,
    REQUIRED_SCHEMA_FILES,
    iter_catalog_paths,
    iter_policy_paths,
    iter_schema_paths,
)
from memory.validation import validate_memory_scaffold


def test_required_memory_resource_files_exist() -> None:
    assert [path.name for path in iter_policy_paths()] == list(REQUIRED_POLICY_FILES)
    assert [path.name for path in iter_catalog_paths()] == list(REQUIRED_CATALOG_FILES)
    assert [path.name for path in iter_schema_paths()] == list(REQUIRED_SCHEMA_FILES)

    for path in (*iter_policy_paths(), *iter_catalog_paths(), *iter_schema_paths()):
        assert path.exists(), path


def test_memory_scaffold_validation_passes() -> None:
    assert validate_memory_scaffold() == []
