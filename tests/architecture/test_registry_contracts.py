# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for Registry pattern contracts.

Verifies that all registries follow the unified BaseRegistry protocol.
Implements CLAUDE.md §6.3.3 requirements.

Updated for instance-level PipelineRegistry (2025-12).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bioetl.composition.registry_api import (
    PipelineRegistry,
    create_registry,
    get_default_registry,
)
from bioetl.domain.ports import PipelineFactoryPort


pytestmark = pytest.mark.architecture


class TestRegistryProtocol:
    """All registries must implement BaseRegistry protocol."""

    def test_pipeline_registry_has_required_methods(self) -> None:
        """PipelineRegistry must have get, register_factory, list_pipelines methods."""
        # Check class-level methods exist
        registry = PipelineRegistry()
        assert hasattr(registry, "get"), "PipelineRegistry MUST have get() method"
        assert hasattr(registry, "register_factory"), (
            "PipelineRegistry MUST have register_factory() method"
        )
        assert hasattr(registry, "list_pipelines"), (
            "PipelineRegistry MUST have list_pipelines() method"
        )

    def test_datasource_creator_helper_exists(self) -> None:
        """Datasource factory module must expose the canonical creator helper."""
        from bioetl.composition.factories.datasource.data_source_factory import (
            get_data_source_creator,
        )

        assert callable(get_data_source_creator), (
            "Datasource factory module MUST expose get_data_source_creator()"
        )

    def test_provider_registry_has_required_methods(self) -> None:
        """ProviderRegistry must have get, register, list_providers methods."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        assert hasattr(ProviderRegistry, "get"), (
            "ProviderRegistry MUST have get() method"
        )
        assert hasattr(ProviderRegistry, "register"), (
            "ProviderRegistry MUST have register() method"
        )
        assert hasattr(ProviderRegistry, "list_providers"), (
            "ProviderRegistry MUST have list_providers() method"
        )

    def test_provider_registry_has_create_adapter(self) -> None:
        """ProviderRegistry must have create_adapter for adapter instantiation."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        assert hasattr(ProviderRegistry, "create_adapter"), (
            "ProviderRegistry MUST have create_adapter() method for DI"
        )

    def test_provider_registry_uses_typed_adapter_creator_contract(
        self,
        src_dir: Path,
    ) -> None:
        """Provider registration must not reintroduce the legacy creator seam."""
        providers_path = src_dir / "bioetl" / "composition" / "providers"
        forbidden_patterns = (
            "custom_creator",
            "AdapterCreator = Callable",
            "AdapterCreator,",
        )
        violations: list[str] = []

        for py_file in providers_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                if pattern in content:
                    violations.append(f"{py_file.relative_to(src_dir)}: {pattern}")

        assert not violations, (
            "Provider registration must use AdapterCreatorProtocol and "
            "ProviderConfig.adapter_creator instead of the legacy custom_creator "
            "seam.\n" + "\n".join(f"  - {item}" for item in violations)
        )

    def test_datasource_factory_path_avoids_class_level_provider_registry_access(
        self,
        src_dir: Path,
    ) -> None:
        """Datasource composition path should prefer explicit registry instances.

        RF-07C: after introducing an explicit registry path in datasource
        factories, new class-level ``ProviderRegistry`` method calls in this
        subtree should not grow back unnoticed.
        """
        datasource_path = (
            src_dir / "bioetl" / "composition" / "factories" / "datasource"
        )
        forbidden_patterns = [
            "ProviderRegistry.ensure_loaded(",
            "ProviderRegistry.is_registered(",
            "ProviderRegistry.list_providers(",
            "ProviderRegistry.get_http_config(",
            "ProviderRegistry.create_adapter(",
            "ProviderRegistry.build_data_source_creator(",
        ]
        violations: list[str] = []

        for py_file in datasource_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                if pattern in content:
                    violations.append(f"{py_file.relative_to(src_dir)}: {pattern}")

        assert not violations, (
            "Datasource composition should use explicit ProviderRegistry instances "
            "instead of new class-level registry access.\n"
            + "\n".join(f"  - {item}" for item in violations)
        )

    def test_runtime_paths_avoid_raw_class_level_provider_registry_bootstrap(
        self,
        src_dir: Path,
    ) -> None:
        """Deferred runtime files should use the named provider bootstrap seam.

        RF-07D3: runtime/bootstrap migration moved these files away from raw
        ``ProviderRegistry.ensure_loaded()`` access. This guard keeps that seam
        from silently regressing.
        """
        runtime_files = [
            src_dir / "bioetl" / "composition" / "_pipeline_execution.py",
            src_dir
            / "bioetl"
            / "composition"
            / "bootstrap"
            / "runtime"
            / "pipeline.py",
            src_dir / "bioetl" / "composition" / "factories" / "pipeline" / "runner.py",
            src_dir
            / "bioetl"
            / "composition"
            / "runtime_builders"
            / "runner_builder.py",
        ]
        forbidden_pattern = "ProviderRegistry.ensure_loaded("
        violations: list[str] = []

        for py_file in runtime_files:
            content = py_file.read_text(encoding="utf-8")
            if forbidden_pattern in content:
                violations.append(
                    f"{py_file.relative_to(src_dir)}: {forbidden_pattern}"
                )

        assert not violations, (
            "Deferred runtime paths should use the named runtime bootstrap seam "
            "instead of raw class-level ProviderRegistry.ensure_loaded().\n"
            + "\n".join(f"  - {item}" for item in violations)
        )

    def test_cli_bootstrap_paths_avoid_pipeline_default_registry_access(
        self,
        src_dir: Path,
    ) -> None:
        """CLI bootstrap should assemble explicit registries in the Composition Root."""
        bootstrap_path = src_dir / "bioetl" / "composition" / "bootstrap" / "cli"
        violations: list[str] = []

        for py_file in bootstrap_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "get_default_registry" in content:
                violations.append(f"{py_file.relative_to(src_dir)}")

        assert not violations, (
            "CLI bootstrap must use explicit pipeline registries instead of the "
            "compatibility default registry seam.\n"
            + "\n".join(f"  - {item}" for item in violations)
        )

    def test_cli_main_entrypoint_uses_explicit_registry_builder(
        self,
        src_dir: Path,
    ) -> None:
        """Canonical CLI startup should keep registry bootstrap lazy."""
        main_path = src_dir / "bioetl" / "interfaces" / "cli" / "main.py"
        content = main_path.read_text(encoding="utf-8")

        assert "def _build_main_registry()" in content
        assert "cli(obj=None)" in content

    def test_src_paths_avoid_raw_class_level_provider_registry_calls(
        self,
        src_dir: Path,
    ) -> None:
        """Production src should use named/provider-instance seams, not raw class calls."""
        src_root = src_dir / "bioetl"
        violations: list[str] = []

        for py_file in src_root.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if not isinstance(func.value, ast.Name):
                    continue
                if func.value.id != "ProviderRegistry":
                    continue
                violations.append(
                    f"{py_file.relative_to(src_dir)}:{node.lineno}: "
                    f"ProviderRegistry.{func.attr}(...)"
                )

        assert not violations, (
            "Production src should use explicit registry instances or named default "
            "registry seams instead of raw class-level ProviderRegistry calls.\n"
            + "\n".join(f"  - {item}" for item in violations)
        )


class TestRegistryRaiseOnMissingKey:
    """Registries must raise clear error for unknown keys."""

    def test_pipeline_registry_raises_on_missing(self, isolated_registry) -> None:
        """PipelineRegistry raises RuntimeError or ValueError for unknown pipeline."""
        # Empty registry raises RuntimeError
        with pytest.raises((RuntimeError, ValueError, KeyError)):
            isolated_registry.get("nonexistent_pipeline_12345")

    def test_datasource_creator_helper_raises_on_missing(self) -> None:
        """Canonical datasource helper raises KeyError for unknown provider."""
        from bioetl.composition.factories.datasource.data_source_factory import (
            get_data_source_creator,
        )

        with pytest.raises(KeyError):
            get_data_source_creator("nonexistent_provider_12345")

    def test_provider_registry_raises_on_missing(self) -> None:
        """ProviderRegistry raises KeyError for unknown provider."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        with pytest.raises(KeyError):
            ProviderRegistry.get("nonexistent_provider_12345")


class TestRegistryInstanceVariables:
    """PipelineRegistry uses instance variables for test isolation."""

    def test_pipeline_registry_has_instance_registry(self) -> None:
        """PipelineRegistry._registry must be an instance variable."""
        registry = PipelineRegistry()

        # Instance should have _registry attribute
        assert hasattr(registry, "_registry"), (
            "PipelineRegistry MUST have _registry attribute"
        )

        # It should be a dict
        assert isinstance(registry._registry, dict), (
            "PipelineRegistry._registry MUST be a dict"
        )

    def test_pipeline_registry_has_instance_lock(self) -> None:
        """PipelineRegistry._lock must be an instance variable."""
        import threading

        registry = PipelineRegistry()

        # Instance should have _lock attribute
        assert hasattr(registry, "_lock"), "PipelineRegistry MUST have _lock attribute"

        # It should be an RLock
        assert isinstance(registry._lock, type(threading.RLock())), (
            "PipelineRegistry._lock MUST be an RLock"
        )

    def test_pipeline_registry_instances_are_independent(self) -> None:
        """Two PipelineRegistry instances must have separate storage."""
        registry1 = PipelineRegistry()
        registry2 = PipelineRegistry()

        # Should be different dict instances
        assert registry1._registry is not registry2._registry, (
            "PipelineRegistry instances MUST have independent _registry"
        )

        # Should be different lock instances
        assert registry1._lock is not registry2._lock, (
            "PipelineRegistry instances MUST have independent _lock"
        )

    def test_provider_registry_uses_instance_scoped_providers(self) -> None:
        """ProviderRegistry must use instance-scoped _providers with lazy singleton."""
        from bioetl.composition.providers.provider_registry import (
            ProviderRegistry,
            get_default_provider_registry,
        )

        # Instance-scoped: each new instance gets its own dict
        reg = ProviderRegistry()
        assert isinstance(reg._providers, dict)
        assert len(reg._providers) == 0

        # Class-level access delegates to default singleton (backward compat)
        default_providers = ProviderRegistry._providers
        assert default_providers is get_default_provider_registry()._providers

    def test_provider_registry_instance_api_uses_instance_store(self) -> None:
        """ProviderRegistry instance methods must not write through the default singleton."""
        from bioetl.composition.providers.provider_registry import (
            ProviderRegistry,
            get_default_provider_registry,
        )
        from bioetl.composition.providers._models import ProviderConfig

        class DummyAdapter:
            def __init__(self, http_client=None, logger=None) -> None:
                self.http_client = http_client
                self.logger = logger

        default_registry = get_default_provider_registry()
        original_default = dict(default_registry._providers)
        default_registry._providers.clear()

        try:
            reg = ProviderRegistry()
            config = ProviderConfig(
                adapter_class=DummyAdapter,
                requires_http_client=False,
                requires_logger=False,
            )

            reg.register("isolated_provider", config)

            assert reg.get("isolated_provider") is config
            assert "isolated_provider" in reg._providers
            assert "isolated_provider" not in default_registry._providers
        finally:
            default_registry._providers.clear()
            default_registry._providers.update(original_default)


class TestRegistryReturnTypes:
    """Registries must return proper types."""

    def test_pipeline_registry_list_returns_list(
        self, populated_isolated_registry
    ) -> None:
        """PipelineRegistry.list_pipelines must return list[str]."""
        result = populated_isolated_registry.list_pipelines()
        assert isinstance(result, list), "list_pipelines() MUST return a list"
        # All items should be strings
        for item in result:
            assert isinstance(item, str), "list_pipelines() MUST return list of strings"

    def test_provider_registry_list_includes_loaded_provider_names(self) -> None:
        """ProviderRegistry.list_providers must return loaded provider names."""
        from bioetl.composition.providers import ensure_providers_loaded
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        ensure_providers_loaded()
        result = ProviderRegistry.list_providers()
        assert isinstance(result, list), "list_providers() MUST return a list"
        assert {"chembl", "pubchem", "uniprot"} <= set(result)

    def test_provider_registry_list_returns_sorted_list(self) -> None:
        """ProviderRegistry.list_providers must return sorted list[str]."""
        from bioetl.composition.providers.provider_registry import ProviderRegistry

        result = ProviderRegistry.list_providers()
        assert isinstance(result, list), "list_providers() MUST return a list"
        # Check it's sorted
        assert result == sorted(result), "list_providers() MUST return sorted list"


class TestRegistryConsistency:
    """Test consistency between provider registry and creator helper."""

    def test_datasource_creator_helper_binds_provider_registry_providers(self) -> None:
        """get_data_source_creator should work for registered provider names."""
        from bioetl.composition.factories.datasource.data_source_factory import (
            get_data_source_creator,
        )
        from bioetl.composition.providers import ensure_providers_loaded

        ensure_providers_loaded()
        for provider in {"chembl", "pubchem", "uniprot"}:
            assert callable(get_data_source_creator(provider))


class TestRegistryFactoryProtocol:
    """Test that PipelineRegistry has proper factory protocol."""

    def test_pipeline_factory_protocol_is_runtime_checkable(self) -> None:
        """PipelineFactoryPort must be @runtime_checkable."""

        # Test by attempting isinstance() - non-runtime_checkable raises TypeError
        class DummyImpl:
            """Dummy class for testing isinstance()."""

            pass

        try:
            isinstance(DummyImpl(), PipelineFactoryPort)
            is_runtime_checkable = True
        except TypeError:
            is_runtime_checkable = False

        assert is_runtime_checkable, "PipelineFactoryPort MUST be @runtime_checkable"

    def test_pipeline_factory_protocol_has_required_attributes(self) -> None:
        """PipelineFactoryPort must define pipeline_name and silver_schema."""
        # Use __annotations__ instead of get_type_hints() to avoid
        # resolving forward references (pa.Schema) at runtime.
        annotations = PipelineFactoryPort.__annotations__

        assert "pipeline_name" in annotations, (
            "PipelineFactoryPort MUST have pipeline_name"
        )
        assert "silver_schema" in annotations, (
            "PipelineFactoryPort MUST have silver_schema"
        )

    def test_pipeline_factory_protocol_has_create_methods(self) -> None:
        """PipelineFactoryPort must have create_with_services and create_runner."""
        assert hasattr(PipelineFactoryPort, "create_with_services"), (
            "PipelineFactoryPort MUST have create_with_services()"
        )
        assert hasattr(PipelineFactoryPort, "create_runner"), (
            "PipelineFactoryPort MUST have create_runner()"
        )

    def test_pipeline_factory_protocol_uses_domain_runtime_contracts(self) -> None:
        """PipelineFactoryPort should stay expressed in domain-facing contracts."""
        create_with_services_annotations = (
            PipelineFactoryPort.create_with_services.__annotations__
        )
        create_runner_annotations = PipelineFactoryPort.create_runner.__annotations__

        assert create_with_services_annotations["request"] == (
            "PipelineCreateWithServicesRequest"
        )
        assert create_runner_annotations["request"] == "PipelineCreateRunnerRequest"
        assert create_runner_annotations["return"] == "ExecutionMetricsRunnerPort"


class TestDefaultRegistryHelper:
    """Test get_default_registry() helper function."""

    def test_get_default_registry_returns_instance(self) -> None:
        """get_default_registry() must return a PipelineRegistry instance."""
        registry = get_default_registry()
        assert isinstance(registry, PipelineRegistry), (
            "get_default_registry() MUST return PipelineRegistry instance"
        )

    def test_get_default_registry_returns_same_instance(self) -> None:
        """get_default_registry() must return the same instance on multiple calls."""
        registry1 = get_default_registry()
        registry2 = get_default_registry()
        assert registry1 is registry2, (
            "get_default_registry() MUST return the same instance"
        )

    def test_create_registry_returns_new_instance(self) -> None:
        """create_registry() must return a new instance each time."""
        registry1 = create_registry()
        registry2 = create_registry()
        assert registry1 is not registry2, (
            "create_registry() MUST return a new instance"
        )
