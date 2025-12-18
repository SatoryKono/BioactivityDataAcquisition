from __future__ import annotations

import os
from pathlib import Path
import pytest
from bioetl.application.registry import PipelineRegistry
# Import factories to ensure registration (via side effects of imports)
# In a real app, bootstrap/composition would do this.
# For this test, we might need to manually trigger the imports or import the module that imports them.
# `bioetl.composition.bootstrap` imports the factories, so importing it should suffice.
# However, bootstrap imports depend on global config sometimes.
# Let's import the factory modules directly to be safe and robust.
import bioetl.composition.factories.chembl_activity
import bioetl.composition.factories.pubchem_compound
import bioetl.composition.factories.uniprot_protein

def test_registry_completeness():
    """
    Verify that every pipeline configuration file in configs/pipelines
    has a corresponding entry in the PipelineRegistry.
    """
    config_dir = Path("configs/pipelines")
    if not config_dir.exists():
        pytest.skip("Config directory not found")

    # Walk through the config directory
    found_configs = []
    for root, _, files in os.walk(config_dir):
        for file in files:
            if file.endswith(".yaml") or file.endswith(".yml"):
                # Structure is configs/pipelines/{provider}/{entity}.yaml
                # The pipeline name is {provider}_{entity}
                path = Path(root) / file

                # Check if it's in a provider subdirectory
                relative_path = path.relative_to(config_dir)
                parts = relative_path.parts

                if len(parts) >= 2:
                    provider = parts[0]
                    entity = os.path.splitext(parts[1])[0]
                    pipeline_name = f"{provider}_{entity}"
                    found_configs.append(pipeline_name)

    # Get registered pipelines
    registered_pipelines = PipelineRegistry.list_pipelines()

    # Check for missing handlers
    missing_handlers = [
        name for name in found_configs
        if name not in registered_pipelines
    ]

    assert not missing_handlers, f"The following pipelines have configs but no registered factory: {missing_handlers}"

def test_registry_contains_expected_pipelines():
    """Sanity check that key pipelines are present."""
    expected = [
        "chembl_activity",
        "pubchem_compound",
        "uniprot_protein",
    ]
    registered = PipelineRegistry.list_pipelines()

    for pipe in expected:
        assert pipe in registered, f"Expected pipeline {pipe} not found in registry"
