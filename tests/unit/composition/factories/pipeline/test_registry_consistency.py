"""Registry consistency tests for pipeline factory registration."""

from __future__ import annotations

import inspect
import re

import pytest

from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.factories.pipeline.contract_validator import (
    _resolve_transformer_class_ref,
)
from bioetl.composition.factories.pipeline.registry import (
    PIPELINE_CONFIGS,
    list_available_pipelines,
    register_all_pipelines,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def test_registry() -> PipelineRegistry:
    """Create an isolated registry for testing."""
    registry = create_registry()
    register_all_pipelines(registry=registry)
    return registry


class TestChemblPipelinesRegistered:
    """Test that all ChEMBL pipeline classes are registered."""

    def test_all_chembl_pipelines_registered(
        self, test_registry: PipelineRegistry
    ) -> None:
        """Verify all ChEMBL pipeline classes have corresponding registry entries."""
        from bioetl.application.pipelines import chembl as chembl_module

        chembl_exports = getattr(chembl_module, "__all__", [])
        pipeline_class_names = [
            name for name in chembl_exports if name.endswith("Pipeline")
        ]

        unique_classes: dict[type, str] = {}
        for name in pipeline_class_names:
            cls = getattr(chembl_module, name)
            if cls not in unique_classes:
                unique_classes[cls] = name
            else:
                existing_name = unique_classes[cls]
                if "Document" in existing_name and "Publication" in name:
                    unique_classes[cls] = name

        pipeline_classes = list(unique_classes.values())
        registered_names = [
            name for name in test_registry.list_pipelines() if name.startswith("chembl")
        ]

        def class_to_registry_name(class_name: str) -> str:
            name = class_name.replace("Pipeline", "")
            if name.startswith("ChEMBL"):
                name = name[6:]
            name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
            return f"chembl_{name}"

        expected_registry_names = {
            class_to_registry_name(cls) for cls in pipeline_classes
        }

        assert len(pipeline_classes) == len(registered_names), (
            f"Mismatch between ChEMBL pipeline classes ({len(pipeline_classes)}) "
            f"and registered pipelines ({len(registered_names)}).\n"
            f"Pipeline classes: {sorted(pipeline_classes)}\n"
            f"Registered: {sorted(registered_names)}"
        )

        registered_set = set(registered_names)
        missing = expected_registry_names - registered_set
        assert not missing, (
            f"ChEMBL pipeline classes not registered: {missing}. "
            "Add them to PIPELINE_CONFIGS in registry_manifest.py"
        )

    def test_all_providers_have_pipelines_registered(
        self, test_registry: PipelineRegistry
    ) -> None:
        """Verify each provider has at least one registered pipeline."""
        registered = test_registry.list_pipelines()

        provider_to_pipelines: dict[str, list[str]] = {}
        for config in PIPELINE_CONFIGS:
            provider_to_pipelines.setdefault(config.provider, []).append(
                config.pipeline_name
            )

        missing_pipelines: list[str] = []
        for provider, pipelines in provider_to_pipelines.items():
            for pipeline in pipelines:
                if pipeline not in registered:
                    missing_pipelines.append(f"{provider}:{pipeline}")

        assert not missing_pipelines, (
            f"Pipelines not registered: {missing_pipelines}. "
            "Add them to the registry manifest and registry wiring."
        )


class TestRegistryNameUniqueness:
    """Test that all registry names are unique."""

    def test_pipeline_configs_have_unique_names(self) -> None:
        """Verify PIPELINE_CONFIGS has no duplicate pipeline names."""
        names = [config.pipeline_name for config in PIPELINE_CONFIGS]

        seen = set()
        duplicates = []
        for name in names:
            if name in seen:
                duplicates.append(name)
            seen.add(name)

        assert not duplicates, f"Duplicate pipeline names found: {duplicates}"

    def test_registry_has_unique_names(self, test_registry: PipelineRegistry) -> None:
        """Verify registered pipelines have unique names."""
        registered = test_registry.list_pipelines()
        assert len(registered) == len(set(registered)), (
            "Registry contains duplicate pipeline names"
        )

    def test_duplicate_registration_raises_error(self) -> None:
        """Verify that registering a duplicate pipeline raises ValueError."""
        registry = create_registry()
        register_all_pipelines(registry=registry)

        from bioetl.composition.factories.pipeline.registry import _factories

        factory = next(iter(_factories.values()))

        with pytest.raises(ValueError, match="Pipeline already registered"):
            registry.register_factory(factory)


class TestFactoryValidity:
    """Test that all registered factories are valid and callable."""

    def test_factories_mapping_is_read_only(self) -> None:
        """The module-level factory catalog should not be mutable."""
        from bioetl.composition.factories.pipeline.registry import _factories

        with pytest.raises(TypeError):
            _factories["test_pipeline"] = object()  # type: ignore[index]

    def test_all_factories_have_pipeline_name(self) -> None:
        """Verify each factory has a pipeline_name attribute."""
        from bioetl.composition.factories.pipeline.registry import _factories

        for name, factory in _factories.items():
            assert hasattr(factory, "pipeline_name"), (
                f"Factory {name} missing pipeline_name attribute"
            )
            assert factory.pipeline_name == name, (
                f"Factory pipeline_name mismatch: {factory.pipeline_name} != {name}"
            )

    def test_all_factories_have_silver_schema(self) -> None:
        """Verify each factory has a silver_schema attribute."""
        from bioetl.composition.factories.pipeline.registry import _factories

        for name, factory in _factories.items():
            assert hasattr(factory, "silver_schema"), (
                f"Factory {name} missing silver_schema attribute"
            )

    def test_all_factories_have_gold_schema(self) -> None:
        """Verify each factory has a non-None gold_schema attribute."""
        from bioetl.composition.factories.pipeline.registry import _factories

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
        from bioetl.composition.factories.pipeline.registry import _factories

        for name, factory in _factories.items():
            assert hasattr(factory, "create_with_services"), (
                f"Factory {name} missing create_with_services method"
            )
            assert callable(factory.create_with_services), (
                f"Factory {name}.create_with_services is not callable"
            )

    def test_all_factories_have_create_runner(self) -> None:
        """Verify each factory has create_runner method."""
        from bioetl.composition.factories.pipeline.registry import _factories

        for name, factory in _factories.items():
            assert hasattr(factory, "create_runner"), (
                f"Factory {name} missing create_runner method"
            )
            assert callable(factory.create_runner), (
                f"Factory {name}.create_runner is not callable"
            )

    def test_factory_count_matches_config_count(self) -> None:
        """Verify factory count matches PIPELINE_CONFIGS count."""
        from bioetl.composition.factories.pipeline.registry import _factories

        assert len(_factories) == len(PIPELINE_CONFIGS), (
            f"Factory count ({len(_factories)}) != "
            f"PIPELINE_CONFIGS count ({len(PIPELINE_CONFIGS)})"
        )


class TestRegistryConfigConsistency:
    """Test consistency between registry and config files."""

    def test_all_registered_pipelines_have_config_files(
        self, test_registry: PipelineRegistry
    ) -> None:
        """Verify each registered pipeline has a corresponding YAML config file."""
        from bioetl.infrastructure.config.pipeline_config_api import (
            load_pipeline_config,
        )

        registered = test_registry.list_pipelines()

        for pipeline_name in registered:
            try:
                config = load_pipeline_config(pipeline_name)
                assert config is not None, f"Config for {pipeline_name} returned None"
            except FileNotFoundError:
                pytest.fail(
                    f"Pipeline '{pipeline_name}' is registered but has no config file. "
                    f"Create configs/entities/<provider>/<entity>.yaml"
                )
            except ValueError as error:
                pytest.fail(f"Pipeline '{pipeline_name}' config is invalid: {error}")


class TestTransformerClassConsistency:
    """Test that transformer classes are properly configured."""

    def test_all_configs_have_valid_transformer_class(self) -> None:
        """Verify each PIPELINE_CONFIG has a valid transformer class."""
        for config in PIPELINE_CONFIGS:
            transformer_class = _resolve_transformer_class_ref(config.transformer_class)

            assert inspect.isclass(transformer_class), (
                f"Pipeline {config.pipeline_name}: "
                f"transformer_class is not a class: {transformer_class}"
            )
            assert hasattr(transformer_class, "transform"), (
                f"Pipeline {config.pipeline_name}: "
                f"transformer_class missing 'transform' method"
            )

    def test_all_configs_have_matching_provider(self) -> None:
        """Verify PIPELINE_CONFIG.provider matches pipeline_name prefix."""
        specialized_providers = {
            "uniprot_idmapping": "uniprot",
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
            "pubmed_publication",
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
