# tests/unit/cli/test_registry_consistency.py
"""Registry consistency tests.

Ensures all pipelines are correctly registered and accessible via CLI.
These tests detect missing registrations for new pipelines.

Run with: pytest tests/unit/cli/test_registry_consistency.py -v
Update snapshots: pytest tests/unit/cli/test_registry_consistency.py --snapshot-update
"""

from __future__ import annotations

import inspect
import re
from typing import Any

import pytest
from click.testing import CliRunner

from bioetl.composition.factories.pipeline_factories import (
    PIPELINE_CONFIGS,
    list_available_pipelines,
    register_all_pipelines,
)
from bioetl.composition.registry import PipelineRegistry, create_registry

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def test_registry() -> PipelineRegistry:
    """Create an isolated registry for testing."""
    registry = create_registry()
    register_all_pipelines(registry=registry)
    return registry


# =============================================================================
# Test: All ChEMBL Pipeline Classes Are Registered
# =============================================================================


class TestChemblPipelinesRegistered:
    """Test that all ChEMBL pipeline classes are registered."""

    def test_all_chembl_pipelines_registered(
        self, test_registry: PipelineRegistry
    ) -> None:
        """Verify all ChEMBL Pipeline classes have corresponding registry entries.

        This test ensures that when a new *Pipeline class is added to
        bioetl.application.pipelines.chembl, it is also registered in
        PIPELINE_CONFIGS.

        If this test fails, add the new pipeline to PIPELINE_CONFIGS in
        src/bioetl/composition/factories/pipeline_factories.py.
        """
        # Import the chembl module to introspect exports
        from bioetl.application.pipelines import chembl as chembl_module

        # Get all exported names that end with 'Pipeline'
        chembl_exports = getattr(chembl_module, "__all__", [])
        pipeline_classes = [
            name for name in chembl_exports if name.endswith("Pipeline")
        ]

        # Get registered ChEMBL pipelines
        registered_names = [
            name for name in test_registry.list_pipelines() if name.startswith("chembl")
        ]

        # Each pipeline class should have a corresponding registration
        # ChEMBLActivityPipeline -> chembl_activity
        # ChEMBLAssayPipeline -> chembl_assay, etc.
        def class_to_registry_name(class_name: str) -> str:
            """Convert ChEMBLActivityPipeline -> chembl_activity."""
            # Remove 'Pipeline' suffix
            name = class_name.replace("Pipeline", "")
            # ChEMBL -> chembl, Activity -> activity
            # Handle 'ChEMBL' prefix specially
            if name.startswith("ChEMBL"):
                name = name[6:]  # Remove 'ChEMBL'
            # Convert CamelCase to snake_case
            name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
            return f"chembl_{name}"

        # Map pipeline classes to expected registry names
        expected_registry_names = {
            class_to_registry_name(cls) for cls in pipeline_classes
        }

        # Verify counts match
        assert len(pipeline_classes) == len(registered_names), (
            f"Mismatch between ChEMBL pipeline classes ({len(pipeline_classes)}) "
            f"and registered pipelines ({len(registered_names)}).\n"
            f"Pipeline classes: {sorted(pipeline_classes)}\n"
            f"Registered: {sorted(registered_names)}"
        )

        # Verify each expected name is registered
        registered_set = set(registered_names)
        missing = expected_registry_names - registered_set
        assert not missing, (
            f"ChEMBL pipeline classes not registered: {missing}. "
            f"Add them to PIPELINE_CONFIGS in pipeline_factories.py"
        )

    def test_all_providers_have_pipelines_registered(
        self, test_registry: PipelineRegistry
    ) -> None:
        """Verify each provider has at least one registered pipeline."""
        registered = test_registry.list_pipelines()

        # Map from provider to list of pipelines for that provider
        provider_to_pipelines: dict[str, list[str]] = {}
        for config in PIPELINE_CONFIGS:
            provider_to_pipelines.setdefault(config.provider, []).append(
                config.pipeline_name
            )

        # Check each provider's pipelines are registered
        missing_pipelines: list[str] = []
        for provider, pipelines in provider_to_pipelines.items():
            for pipeline in pipelines:
                if pipeline not in registered:
                    missing_pipelines.append(f"{provider}:{pipeline}")

        assert not missing_pipelines, (
            f"Pipelines not registered: {missing_pipelines}. "
            f"Add them to the registry in pipeline_factories.py"
        )


# =============================================================================
# Test: Snapshot Test for List Command Output
# =============================================================================


class TestListPipelinesCommandSnapshot:
    """Snapshot tests for list-pipelines command output."""

    def test_list_pipelines_command_output(
        self,
        cli_runner: CliRunner,
        snapshot: Any,
    ) -> None:
        """Test list-pipelines command output matches snapshot.

        This test captures the expected CLI output for regression detection.
        If the pipeline list changes intentionally, update the snapshot with:
            pytest tests/unit/cli/test_registry_consistency.py --snapshot-update
        """
        # Skip if syrupy is not installed
        pytest.importorskip("syrupy", reason="syrupy required for snapshot tests")

        from bioetl.interfaces.cli.main import cli

        result = cli_runner.invoke(cli, ["config", "list-pipelines"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert result.output == snapshot

    def test_list_pipelines_output_format(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test list-pipelines output format (non-snapshot, always runs)."""
        from bioetl.interfaces.cli.main import cli

        result = cli_runner.invoke(cli, ["config", "list-pipelines"])

        assert result.exit_code == 0
        assert "Available pipelines:" in result.output
        # Verify expected pipelines are in output
        expected = ["chembl_activity", "pubchem_compound", "uniprot_protein"]
        for pipeline in expected:
            assert pipeline in result.output, f"Missing pipeline: {pipeline}"


# =============================================================================
# Test: Registry Name Uniqueness
# =============================================================================


class TestRegistryNameUniqueness:
    """Test that all registry names are unique."""

    def test_pipeline_configs_have_unique_names(self) -> None:
        """Verify PIPELINE_CONFIGS has no duplicate pipeline names.

        Duplicate names would cause registration conflicts.
        """
        names = [config.pipeline_name for config in PIPELINE_CONFIGS]

        # Check for duplicates
        seen = set()
        duplicates = []
        for name in names:
            if name in seen:
                duplicates.append(name)
            seen.add(name)

        assert not duplicates, f"Duplicate pipeline names found: {duplicates}"

    def test_registry_has_unique_names(self, test_registry: PipelineRegistry) -> None:
        """Verify registered pipelines have unique names.

        This test validates the registry's enforcement of uniqueness.
        """
        registered = test_registry.list_pipelines()

        # list_pipelines returns a list, check for duplicates
        assert len(registered) == len(set(registered)), (
            "Registry contains duplicate pipeline names"
        )

    def test_duplicate_registration_raises_error(self) -> None:
        """Verify that registering a duplicate pipeline raises ValueError."""
        registry = create_registry()
        register_all_pipelines(registry=registry)

        # Attempt to register again should raise
        from bioetl.composition.factories.pipeline_factories import _factories

        factory = next(iter(_factories.values()))

        with pytest.raises(ValueError, match="Pipeline already registered"):
            registry.register_factory(factory)


# =============================================================================
# Test: Factory Validity
# =============================================================================


class TestFactoryValidity:
    """Test that all registered factories are valid and callable."""

    def test_all_factories_have_pipeline_name(self) -> None:
        """Verify each factory has a pipeline_name attribute."""
        from bioetl.composition.factories.pipeline_factories import _factories

        for name, factory in _factories.items():
            assert hasattr(factory, "pipeline_name"), (
                f"Factory {name} missing pipeline_name attribute"
            )
            assert factory.pipeline_name == name, (
                f"Factory pipeline_name mismatch: {factory.pipeline_name} != {name}"
            )

    def test_all_factories_have_silver_schema(self) -> None:
        """Verify each factory has a silver_schema attribute (can be None)."""
        from bioetl.composition.factories.pipeline_factories import _factories

        for name, factory in _factories.items():
            assert hasattr(factory, "silver_schema"), (
                f"Factory {name} missing silver_schema attribute"
            )

    def test_all_factories_have_gold_schema(self) -> None:
        """Verify each factory has a non-None gold_schema attribute.

        Gold schemas are required for all pipelines (RULES.md §3.1).
        """
        from bioetl.composition.factories.pipeline_factories import _factories

        for name, factory in _factories.items():
            assert hasattr(factory, "gold_schema"), (
                f"Factory {name} missing gold_schema attribute"
            )
            assert factory.gold_schema is not None, (
                f"Factory {name} has None gold_schema. "
                "All pipelines require a Gold schema for validation."
            )

    def test_all_factories_have_create_with_services(self) -> None:
        """Verify each factory has create_with_services method."""
        from bioetl.composition.factories.pipeline_factories import _factories

        for name, factory in _factories.items():
            assert hasattr(factory, "create_with_services"), (
                f"Factory {name} missing create_with_services method"
            )
            assert callable(factory.create_with_services), (
                f"Factory {name}.create_with_services is not callable"
            )

    def test_all_factories_have_create_runner(self) -> None:
        """Verify each factory has create_runner method."""
        from bioetl.composition.factories.pipeline_factories import _factories

        for name, factory in _factories.items():
            assert hasattr(factory, "create_runner"), (
                f"Factory {name} missing create_runner method"
            )
            assert callable(factory.create_runner), (
                f"Factory {name}.create_runner is not callable"
            )

    def test_factory_count_matches_config_count(self) -> None:
        """Verify factory count matches PIPELINE_CONFIGS count."""
        from bioetl.composition.factories.pipeline_factories import _factories

        assert len(_factories) == len(PIPELINE_CONFIGS), (
            f"Factory count ({len(_factories)}) != "
            f"PIPELINE_CONFIGS count ({len(PIPELINE_CONFIGS)})"
        )


# =============================================================================
# Test: Registry-Config File Consistency
# =============================================================================


class TestRegistryConfigConsistency:
    """Test consistency between registry and config files."""

    def test_all_registered_pipelines_have_config_files(
        self, test_registry: PipelineRegistry
    ) -> None:
        """Verify each registered pipeline has a corresponding YAML config file.

        This ensures pipelines can actually be run.
        """

        from bioetl.infrastructure.config import load_pipeline_config

        registered = test_registry.list_pipelines()

        for pipeline_name in registered:
            try:
                config = load_pipeline_config(pipeline_name)
                assert config is not None, f"Config for {pipeline_name} returned None"
            except FileNotFoundError:
                pytest.fail(
                    f"Pipeline '{pipeline_name}' is registered but has no config file. "
                    f"Create configs/pipelines/<provider>/<entity>.yaml"
                )
            except ValueError as e:
                pytest.fail(f"Pipeline '{pipeline_name}' config is invalid: {e}")


# =============================================================================
# Test: Transformer Class Consistency
# =============================================================================


class TestTransformerClassConsistency:
    """Test that transformer classes are properly configured."""

    def test_all_configs_have_valid_transformer_class(self) -> None:
        """Verify each PIPELINE_CONFIG has a valid transformer class."""
        for config in PIPELINE_CONFIGS:
            transformer_class = config.transformer_class

            # Check it's a class
            assert inspect.isclass(transformer_class), (
                f"Pipeline {config.pipeline_name}: "
                f"transformer_class is not a class: {transformer_class}"
            )

            # Check it has transform method (async)
            assert hasattr(transformer_class, "transform"), (
                f"Pipeline {config.pipeline_name}: "
                f"transformer_class missing 'transform' method"
            )

    def test_all_configs_have_matching_provider(self) -> None:
        """Verify PIPELINE_CONFIG.provider matches pipeline_name prefix.

        Note: Some pipelines use specialized providers that don't follow
        the standard {provider}_{entity} naming convention, e.g.,
        'uniprot_idmapping' uses provider 'uniprot_idmapping' (not 'uniprot').
        """
        # Pipelines with specialized providers that don't follow naming convention
        specialized_providers = {
            "uniprot_idmapping": "uniprot_idmapping",
        }

        for config in PIPELINE_CONFIGS:
            if config.pipeline_name in specialized_providers:
                expected = specialized_providers[config.pipeline_name]
                assert config.provider == expected, (
                    f"Pipeline {config.pipeline_name}: "
                    f"provider '{config.provider}' doesn't match expected '{expected}'"
                )
            else:
                prefix = config.pipeline_name.split("_")[0]
                assert config.provider == prefix, (
                    f"Pipeline {config.pipeline_name}: "
                    f"provider '{config.provider}' doesn't match prefix '{prefix}'"
                )


# =============================================================================
# Test: list_available_pipelines() Function
# =============================================================================


class TestListAvailablePipelinesFunction:
    """Test the list_available_pipelines() helper function."""

    def test_returns_sorted_list(self) -> None:
        """Verify list_available_pipelines returns sorted list."""
        result = list_available_pipelines()

        assert isinstance(result, list)
        assert result == sorted(result), "Pipeline list should be sorted"

    def test_contains_expected_pipelines(self) -> None:
        """Verify list contains expected pipeline names."""
        result = list_available_pipelines()

        expected = [
            "chembl_activity",
            "chembl_assay",
            "chembl_molecule",
            "pubchem_compound",
            "pubmed_publications",
            "uniprot_protein",
        ]

        for pipeline in expected:
            assert pipeline in result, f"Missing expected pipeline: {pipeline}"

    def test_matches_registry_list(self, test_registry: PipelineRegistry) -> None:
        """Verify list_available_pipelines matches registry.list_pipelines."""
        function_result = list_available_pipelines()
        registry_result = test_registry.list_pipelines()

        assert function_result == registry_result, (
            "list_available_pipelines() should match registry.list_pipelines()"
        )
