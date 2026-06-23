"""Tests for the composition.services package-root surface."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_services_package_root_retains_only_versioning_namespace() -> None:
    """Package root should not re-export versioning helpers directly."""
    module = importlib.import_module("bioetl.composition.services")

    assert module.__all__ == ["versioning"]
    assert hasattr(module, "versioning")
    for removed_name in (
        "compute_config_hash",
        "get_code_revision_provenance",
        "get_dependency_lock_hash",
        "get_git_commit",
        "get_pipeline_version",
    ):
        assert removed_name not in dir(module)
        with pytest.raises(AttributeError):
            getattr(module, removed_name)
