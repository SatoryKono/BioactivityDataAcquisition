"""Contract tests for pipeline/service factory decoupling."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bioetl.composition.factories.pipeline import build_pipeline_services
from bioetl.composition.factories.pipeline._creation_wiring import (
    _PipelineCreationInputs as CanonicalPipelineCreationInputs,
    _create_pipeline_with_services_impl as canonical_create_pipeline,
)
from bioetl.composition.factories.services import (
    _PipelineCreationInputs,
    _create_pipeline_with_services_impl,
)

pytestmark = pytest.mark.repo_backed


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


@pytest.mark.unit
def test_pipeline_builder_stays_guarded_service_facade() -> None:
    """pipeline_builder.py should remain a thin facade over split builder seams."""
    path = Path("src/bioetl/composition/factories/services/pipeline_builder.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    top_level_functions = [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    ]
    assert set(top_level_functions) == {
        "create_batch_processing_components",
        "create_checkpoint_manager",
        "create_record_processor_from_pipeline",
        "create_batch_executor_from_pipeline",
    }, (
        "pipeline_builder.py should expose only the expected service-facade "
        f"functions. Found: {top_level_functions}"
    )

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    required_builder_modules = {
        "bioetl.composition.factories.services.pipeline_batch_executor_builder",
        "bioetl.composition.factories.services.pipeline_processing_components_builder",
        "bioetl.composition.factories.services.pipeline_record_processor_builder",
    }
    assert required_builder_modules <= imported_modules, (
        "pipeline_builder.py must stay wired through the extracted helper "
        "builder modules."
    )

    forbidden_runtime_modules = {
        "bioetl.application.core.batch_extraction_loop",
        "bioetl.application.core.batch_writer",
    }
    unexpected_runtime_imports = forbidden_runtime_modules & imported_modules
    assert not unexpected_runtime_imports, (
        "pipeline_builder.py must not absorb low-level orchestration imports again:\n"
        + "\n".join(sorted(unexpected_runtime_imports))
    )

    line_count = len(source.splitlines())
    assert line_count <= 180, (
        "pipeline_builder.py must remain a thin service facade "
        f"(current lines: {line_count}, max: 180)."
    )


@pytest.mark.unit
def test_creation_wiring_uses_canonical_domain_config_resolver_not_loader_class_directly() -> (
    None
):
    """Pipeline creation wiring should use the canonical domain-config resolver."""
    path = Path("src/bioetl/composition/factories/pipeline/_creation_wiring.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "bioetl.infrastructure.config.domain_config_resolver" in imported_modules, (
        "Pipeline creation wiring must use the canonical domain_config_resolver."
    )
    assert (
        "bioetl.infrastructure.config.pipeline_config_loader" not in imported_modules
    ), "Pipeline creation wiring must not import PipelineConfigLoader directly."


@pytest.mark.unit
def test_service_bundle_uses_config_resolution_seam_for_pipeline_config_access() -> (
    None
):
    """Service bundle should use canonical infrastructure config owners directly."""
    path = Path("src/bioetl/composition/factories/services/bundle.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert (
        "bioetl.composition.factories.pipeline.config_resolution"
        not in imported_modules
    ), "Service bundle must not keep routing through the config_resolution shim."
    assert "bioetl.infrastructure.config.pipeline_config_api" in imported_modules, (
        "Service bundle must import load_pipeline_config from the canonical infrastructure API."
    )
    assert "bioetl.infrastructure.config.converters" in imported_modules, (
        "Service bundle must import yaml_config_to_domain from the canonical converter module."
    )


@pytest.mark.unit
def test_factory_method_helpers_use_config_resolution_seam() -> None:
    """Factory helpers should load pipeline config from the canonical infrastructure API."""
    path = Path("src/bioetl/composition/factories/pipeline/factory_method_helpers.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert (
        "bioetl.composition.factories.pipeline.config_resolution"
        not in imported_modules
    ), (
        "Factory method helpers must not keep routing through the config_resolution shim."
    )
    assert "bioetl.infrastructure.config.pipeline_config_api" in imported_modules, (
        "Factory method helpers must import pipeline_config_api directly."
    )


@pytest.mark.unit
def test_service_bundle_uses_public_creation_support_module() -> None:
    """Service bundle should import creation contracts from the public support seam."""
    path = Path("src/bioetl/composition/factories/services/bundle.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "bioetl.composition.factories.pipeline.creation_support" in imported_modules
    assert "bioetl.composition.factories.pipeline.creation_api" not in imported_modules


@pytest.mark.unit
def test_services_package_root_uses_public_creation_support_module() -> None:
    """Services package root should use the public creation support seam."""
    path = Path("src/bioetl/composition/factories/services/__init__.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "bioetl.composition.factories.pipeline.creation_support" in imported_modules
    assert "bioetl.composition.factories.pipeline.creation_api" not in imported_modules
