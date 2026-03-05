"""Contract tests for pipeline/service factory decoupling."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

from bioetl.composition.factories import pipeline_factory


@pytest.mark.unit
def test_service_bundle_factory_has_no_pipeline_factory_proxy_imports() -> None:
    """service_bundle_factory must not depend on pipeline_factory module."""
    source = Path(
        "src/bioetl/composition/factories/service_bundle_factory.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_imports = {
        "bioetl.composition.factories.pipeline_factory",
        "pipeline_factory",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_imports
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            assert node.module not in forbidden_imports


@pytest.mark.unit
@patch("bioetl.composition.factories.pipeline_factory._build_pipeline_services")
def test_pipeline_factory_build_services_injects_compat_dependencies(
    mock_build_pipeline_services,
) -> None:
    """Facade build_pipeline_services should pass explicit compatibility deps."""
    mock_build_pipeline_services.return_value = "services"

    with pytest.warns(DeprecationWarning):
        result = pipeline_factory.build_pipeline_services(
            "chembl_activity",
            object(),
            object(),
            object(),
        )

    assert result == "services"
    deps = mock_build_pipeline_services.call_args.kwargs["_deps"]
    assert deps.base_services_factory is pipeline_factory.BaseServicesFactory
    assert deps.load_pipeline_config is pipeline_factory.load_pipeline_config
    assert deps.yaml_config_to_domain is pipeline_factory.yaml_config_to_domain
    assert deps.compute_config_hash is pipeline_factory.compute_config_hash


@pytest.mark.unit
@patch("bioetl.composition.factories.pipeline_factory._create_pipeline_with_services")
def test_pipeline_factory_create_with_services_injects_compat_dependencies(
    mock_create_pipeline_with_services,
) -> None:
    """Facade create_pipeline_with_services should pass explicit compatibility deps."""
    mock_create_pipeline_with_services.return_value = "pipeline"

    with pytest.warns(DeprecationWarning):
        result = pipeline_factory.create_pipeline_with_services(
            "chembl_activity",
            object(),  # pipeline_class
            "chembl",  # provider
            object(),  # create_data_source_fn
            None,  # transformer_class
            "run-test",  # run_id
            object(),  # runtime
            object(),  # settings
            object(),  # logger
        )

    assert result == "pipeline"
    deps = mock_create_pipeline_with_services.call_args.kwargs["_deps"]
    assert deps.base_services_factory is pipeline_factory.BaseServicesFactory
    assert deps.load_pipeline_config is pipeline_factory.load_pipeline_config
    assert deps.yaml_config_to_domain is pipeline_factory.yaml_config_to_domain
    assert deps.compute_config_hash is pipeline_factory.compute_config_hash
