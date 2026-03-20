"""Contract tests for pipeline/service factory decoupling."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bioetl.composition.factories.pipeline import build_pipeline_services
from bioetl.composition.factories.pipeline.creation_api import (
    _PipelineCreationInputs as CanonicalPipelineCreationInputs,
    _create_pipeline_with_services_impl as canonical_create_pipeline,
)
from bioetl.composition.factories.services import (
    _PipelineCreationInputs,
    _create_pipeline_with_services_impl,
)


@pytest.mark.unit
def test_service_bundle_factory_has_no_pipeline_factory_proxy_imports() -> None:
    """service_bundle_factory must not depend on pipeline_factory module."""
    source = Path("src/bioetl/composition/factories/services/bundle.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    forbidden_imports = {
        "bioetl.composition.factories.pipeline.facade",
        "pipeline_factory",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_imports
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            assert node.module not in forbidden_imports


@pytest.mark.unit
def test_pipeline_package_root_reexports_canonical_service_bundle_entrypoint() -> None:
    """Package root should expose the canonical service bundle function directly."""
    assert build_pipeline_services.__module__ == (
        "bioetl.composition.factories.services.bundle"
    )


@pytest.mark.unit
def test_services_package_root_reexports_canonical_pipeline_creation_symbols() -> None:
    """Services package root should expose pipeline-owned creation contracts."""
    assert _PipelineCreationInputs is CanonicalPipelineCreationInputs
    assert _create_pipeline_with_services_impl is canonical_create_pipeline
