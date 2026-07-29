# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for composition/types.py module exports.

These tests verify that the types module correctly re-exports
all required composition layer types.
"""

from __future__ import annotations


import pytest

pytestmark = pytest.mark.unit


class TestTypesModuleExports:
    """Tests for composition/types.py exports."""

    def test_observability_bundle_importable(self) -> None:
        """ObservabilityBundle is importable from types."""
        from bioetl.composition.types import ObservabilityBundle

        assert ObservabilityBundle is not None

    def test_pipeline_definition_importable(self) -> None:
        """PipelineDefinition is importable from types."""
        from bioetl.composition.types import PipelineDefinition

        assert PipelineDefinition is not None

    def test_types_module_exports__registry_importable__36385d83(self) -> None:
        """PipelineRegistry is importable from types."""
        from bioetl.composition.types import PipelineRegistry

        assert PipelineRegistry is not None

    def test_storage_adapter_importable(self) -> None:
        """StorageBundle is importable from types."""
        from bioetl.composition.types import StorageBundle

        assert StorageBundle is not None

    def test_create_registry_importable(self) -> None:
        """create_registry is importable from types."""
        from bioetl.composition.types import create_registry

        assert callable(create_registry)

    def test_get_default_registry_importable(self) -> None:
        """get_default_registry is importable from types."""
        from bioetl.composition.types import get_default_registry

        assert callable(get_default_registry)

    def test_all_exports_defined(self) -> None:
        """All items in __all__ are defined."""
        from bioetl.composition import types

        expected_exports = [
            # Core composition types
            "ObservabilityBundle",
            "PipelineDefinition",
            "PipelineRegistry",
            "StorageBundle",
            "create_registry",
            "get_default_registry",
            # Typed bootstrap contexts
            "CircuitBreakerConfig",
            "DQConfigsContext",
            "DQOutputPathsContext",
            "PipelineCallbacksContext",
            "RateLimitContext",
        ]
        for name in expected_exports:
            assert name in types.__all__, f"{name} not in __all__"
            assert hasattr(types, name), f"{name} not in module"

    def test_exports_match_all(self) -> None:
        """__all__ contains exactly the expected exports."""
        from bioetl.composition import types

        expected = {
            # Core composition types
            "ObservabilityBundle",
            "PipelineDefinition",
            "PipelineRegistry",
            "StorageBundle",
            "create_registry",
            "get_default_registry",
            # Typed bootstrap contexts
            "CircuitBreakerConfig",
            "DQConfigsContext",
            "DQOutputPathsContext",
            "PipelineCallbacksContext",
            "RateLimitContext",
        }
        assert set(types.__all__) == expected


class TestTypesReExports:
    """Tests verifying re-exports match source modules."""

    def test_observability_bundle_is_same(self) -> None:
        """ObservabilityBundle from types is same as from observability."""
        from bioetl.composition.observability import ObservabilityBundle as DirectBundle
        from bioetl.composition.types import ObservabilityBundle as ReExportedBundle

        assert DirectBundle is ReExportedBundle

    def test_pipeline_registry_is_same(self) -> None:
        """PipelineRegistry from types is same as from registry."""
        from bioetl.composition.registry_api import PipelineRegistry as DirectRegistry
        from bioetl.composition.types import PipelineRegistry as ReExportedRegistry

        assert DirectRegistry is ReExportedRegistry

    def test_storage_adapter_is_same(self) -> None:
        """StorageBundle from types is same as from storage factory."""
        from bioetl.composition.factories.storage import StorageBundle as DirectAdapter
        from bioetl.composition.types import StorageBundle as ReExportedAdapter

        assert DirectAdapter is ReExportedAdapter

    def test_create_registry_is_same(self) -> None:
        """create_registry from types is same as from registry."""
        from bioetl.composition.registry_api import create_registry as direct_fn
        from bioetl.composition.types import create_registry as reexported_fn

        assert direct_fn is reexported_fn

    def test_get_default_registry_is_same(self) -> None:
        """get_default_registry from types returns the same shared instance."""
        from bioetl.composition.registry_api import get_default_registry as direct_fn
        from bioetl.composition.types import get_default_registry as reexported_fn

        assert direct_fn() is reexported_fn()


class TestTypesUsability:
    """Tests verifying types can be used for annotations."""

    def test_types_usable_in_annotation(self) -> None:
        """Types can be used in function annotations."""
        from bioetl.composition.types import (
            ObservabilityBundle,
            PipelineRegistry,
            StorageBundle,
        )

        # Just verify they can be used as type annotations
        # (this is a compile-time check, but we verify at runtime)
        def example_function(
            registry: PipelineRegistry,
            storage: StorageBundle,
            observability: ObservabilityBundle,
        ) -> None:
            pass

        # Function was created successfully
        assert example_function is not None

    def test_create_registry_returns_pipeline_registry(self) -> None:
        """create_registry returns a PipelineRegistry instance."""
        from bioetl.composition.types import PipelineRegistry, create_registry

        registry = create_registry()
        assert isinstance(registry, PipelineRegistry)
