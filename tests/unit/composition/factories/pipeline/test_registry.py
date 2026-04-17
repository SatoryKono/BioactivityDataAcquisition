from __future__ import annotations

import os
from pathlib import Path

import pytest

from bioetl.composition import create_registry, get_default_registry
from bioetl.composition.factories.pipeline.registry import (
    register_all_pipelines,
    reset_registration,
)


@pytest.fixture(autouse=True)
def ensure_registration():
    """Ensure pipeline factories are registered before tests."""
    register_all_pipelines()


def test_registry_completeness():
    """
    Verify that every unified entity pipeline configuration file in configs/entities
    has a corresponding entry in the PipelineRegistry.
    """
    config_dir = Path("configs/entities")
    if not config_dir.exists():
        pytest.skip("Config directory not found")

    registry = get_default_registry()

    # Pipelines that have configs but are not yet fully integrated
    # These are new providers in development that will be registered later
    pipelines_in_development: set[str] = set()  # All pipelines are now fully integrated

    # Walk through the config directory
    found_configs = []
    for root, _, files in os.walk(config_dir):
        for file in files:
            if file.endswith(".yaml") or file.endswith(".yml"):
                # Structure is configs/entities/{provider}/{entity}.yaml
                # The pipeline name is {provider}_{entity}
                path = Path(root) / file

                # Check if it's in a provider subdirectory
                relative_path = path.relative_to(config_dir)
                parts = relative_path.parts

                if len(parts) >= 2:
                    provider = parts[0]
                    # Skip internal directories (documentation, templates, etc.)
                    if provider.startswith("_"):
                        continue
                    entity = os.path.splitext(parts[1])[0]
                    pipeline_name = f"{provider}_{entity}"
                    found_configs.append(pipeline_name)

    # Get registered pipelines
    registered_pipelines = registry.list_pipelines()

    # Check for missing handlers (excluding pipelines in development)
    missing_handlers = list(
        name
        for name in found_configs
        if name not in registered_pipelines and name not in pipelines_in_development
    )

    assert not missing_handlers, (
        f"The following pipelines have configs but no registered factory: {missing_handlers}"
    )


def test_registry_contains_expected_pipelines():
    """Sanity check that key pipelines are present."""
    registry = get_default_registry()
    expected = [
        "chembl_activity",
        "pubchem_compound",
        "uniprot_protein",
        "pubmed_publication",
    ]
    registered = registry.list_pipelines()

    for pipe in expected:
        assert pipe in registered, f"Expected pipeline {pipe} not found in registry"


def test_register_all_pipelines_is_idempotent():
    """Test that calling register_all_pipelines multiple times is safe."""
    from bioetl.composition.factories.pipeline.registry import is_registered

    registry = get_default_registry()

    # First call already made in fixture
    assert is_registered()

    # Get current count
    initial_count = len(registry.list_pipelines())

    # Call again - should be no-op
    register_all_pipelines()

    # Count should remain the same
    assert len(registry.list_pipelines()) == initial_count


def test_registry_empty_raises_runtime_error(isolated_registry):
    """Test that accessing empty registry raises RuntimeError."""
    # Use the isolated_registry fixture which is empty
    with pytest.raises(RuntimeError, match="PipelineRegistry is empty"):
        isolated_registry.get("any_pipeline")


def test_isolated_registry_is_independent(isolated_registry):
    """Test that isolated registries are independent of each other."""
    registry1 = isolated_registry
    registry2 = create_registry()

    # Both should be empty initially
    assert len(registry1.list_pipelines()) == 0
    assert len(registry2.list_pipelines()) == 0

    # Register to one
    register_all_pipelines(registry=registry1)

    # First registry should be populated
    assert len(registry1.list_pipelines()) > 0

    # Second registry should still be empty
    assert len(registry2.list_pipelines()) == 0


def test_multiple_registries_in_same_process():
    """Test that we can create 2 registries in one process."""
    registry1 = create_registry()
    registry2 = create_registry()

    register_all_pipelines(registry=registry1)
    register_all_pipelines(registry=registry2)

    # Both should have the same pipelines
    assert registry1.list_pipelines() == registry2.list_pipelines()

    # But they should be different instances
    assert registry1 is not registry2
    assert registry1._registry is not registry2._registry


def test_reset_registration_clears_default_registry_state():
    """reset_registration should clear the default registry and registration flag."""
    from bioetl.composition.factories.pipeline.registry import is_registered

    try:
        register_all_pipelines()
        assert is_registered()
        assert len(get_default_registry().list_pipelines()) > 0

        reset_registration()

        assert not is_registered()
        assert get_default_registry().list_pipelines() == []
    finally:
        register_all_pipelines()
