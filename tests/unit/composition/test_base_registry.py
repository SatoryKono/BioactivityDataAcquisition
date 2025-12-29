"""Tests for composition/base_registry.py Registry Protocol.

These tests verify that the RegistryProtocol is correctly defined
and can be used for structural subtyping.
"""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from bioetl.composition.base_registry import RegistryProtocol


class TestRegistryProtocol:
    """Tests for RegistryProtocol definition."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """RegistryProtocol is @runtime_checkable."""

        # Create a class that implements the protocol
        class TestRegistry:
            _registry: ClassVar[dict[str, str]] = {}

            @classmethod
            def register(cls, key: str, value: str) -> None:
                cls._registry[key] = value

            @classmethod
            def get(cls, key: str) -> str:
                return cls._registry[key]

            @classmethod
            def list_keys(cls) -> list[str]:
                return list(cls._registry.keys())

            @classmethod
            def contains(cls, key: str) -> bool:
                return key in cls._registry

            @classmethod
            def clear(cls) -> None:
                cls._registry.clear()

        # isinstance check should work with @runtime_checkable protocols
        assert isinstance(TestRegistry(), RegistryProtocol)

    def test_protocol_structural_subtyping(self) -> None:
        """Classes implementing the protocol interface are valid."""

        class StringRegistry:
            _registry: ClassVar[dict[str, Any]] = {}

            @classmethod
            def register(cls, key: str, value: Any) -> None:
                cls._registry[key] = value

            @classmethod
            def get(cls, key: str) -> Any:
                return cls._registry[key]

            @classmethod
            def list_keys(cls) -> list[str]:
                return list(cls._registry.keys())

            @classmethod
            def contains(cls, key: str) -> bool:
                return key in cls._registry

            @classmethod
            def clear(cls) -> None:
                cls._registry.clear()

        # Test the implementation works
        StringRegistry.register("test_key", "test_value")
        assert StringRegistry.get("test_key") == "test_value"
        assert StringRegistry.contains("test_key")
        assert "test_key" in StringRegistry.list_keys()
        StringRegistry.clear()
        assert not StringRegistry.contains("test_key")

    def test_incomplete_implementation_fails_check(self) -> None:
        """Classes missing methods don't pass isinstance check."""

        class IncompleteRegistry:
            _registry: ClassVar[dict[str, str]] = {}

            @classmethod
            def register(cls, key: str, value: str) -> None:
                cls._registry[key] = value

            # Missing: get, list_keys, contains, clear

        # Without all methods, isinstance should fail
        assert not isinstance(IncompleteRegistry(), RegistryProtocol)

    def test_protocol_with_different_key_types(self) -> None:
        """Protocol works with various key types."""

        class IntKeyRegistry:
            _registry: ClassVar[dict[int, str]] = {}

            @classmethod
            def register(cls, key: int, value: str) -> None:
                cls._registry[key] = value

            @classmethod
            def get(cls, key: int) -> str:
                return cls._registry[key]

            @classmethod
            def list_keys(cls) -> list[int]:
                return list(cls._registry.keys())

            @classmethod
            def contains(cls, key: int) -> bool:
                return key in cls._registry

            @classmethod
            def clear(cls) -> None:
                cls._registry.clear()

        IntKeyRegistry.register(1, "one")
        IntKeyRegistry.register(2, "two")
        assert IntKeyRegistry.get(1) == "one"
        assert IntKeyRegistry.list_keys() == [1, 2]
        IntKeyRegistry.clear()

    def test_protocol_with_tuple_key(self) -> None:
        """Protocol works with tuple keys."""

        class TupleKeyRegistry:
            _registry: ClassVar[dict[tuple[str, str], Any]] = {}

            @classmethod
            def register(cls, key: tuple[str, str], value: Any) -> None:
                cls._registry[key] = value

            @classmethod
            def get(cls, key: tuple[str, str]) -> Any:
                return cls._registry[key]

            @classmethod
            def list_keys(cls) -> list[tuple[str, str]]:
                return list(cls._registry.keys())

            @classmethod
            def contains(cls, key: tuple[str, str]) -> bool:
                return key in cls._registry

            @classmethod
            def clear(cls) -> None:
                cls._registry.clear()

        key = ("chembl", "activity")
        TupleKeyRegistry.register(key, {"transformer": "ActivityTransformer"})
        assert TupleKeyRegistry.contains(key)
        assert TupleKeyRegistry.get(key) == {"transformer": "ActivityTransformer"}
        TupleKeyRegistry.clear()

    def test_protocol_register_idempotent(self) -> None:
        """Registering the same key twice overwrites the value."""

        class OverwriteRegistry:
            _registry: ClassVar[dict[str, str]] = {}

            @classmethod
            def register(cls, key: str, value: str) -> None:
                cls._registry[key] = value

            @classmethod
            def get(cls, key: str) -> str:
                return cls._registry[key]

            @classmethod
            def list_keys(cls) -> list[str]:
                return list(cls._registry.keys())

            @classmethod
            def contains(cls, key: str) -> bool:
                return key in cls._registry

            @classmethod
            def clear(cls) -> None:
                cls._registry.clear()

        OverwriteRegistry.clear()
        OverwriteRegistry.register("key", "value1")
        OverwriteRegistry.register("key", "value2")
        assert OverwriteRegistry.get("key") == "value2"
        assert len(OverwriteRegistry.list_keys()) == 1
        OverwriteRegistry.clear()

    def test_protocol_get_raises_keyerror_for_missing(self) -> None:
        """Get raises KeyError for unregistered keys."""

        class StrictRegistry:
            _registry: ClassVar[dict[str, str]] = {}

            @classmethod
            def register(cls, key: str, value: str) -> None:
                cls._registry[key] = value

            @classmethod
            def get(cls, key: str) -> str:
                return cls._registry[key]  # Raises KeyError

            @classmethod
            def list_keys(cls) -> list[str]:
                return list(cls._registry.keys())

            @classmethod
            def contains(cls, key: str) -> bool:
                return key in cls._registry

            @classmethod
            def clear(cls) -> None:
                cls._registry.clear()

        StrictRegistry.clear()
        with pytest.raises(KeyError):
            StrictRegistry.get("nonexistent")

    def test_protocol_list_keys_empty(self) -> None:
        """list_keys returns empty list for empty registry."""

        class EmptyRegistry:
            _registry: ClassVar[dict[str, str]] = {}

            @classmethod
            def register(cls, key: str, value: str) -> None:
                cls._registry[key] = value

            @classmethod
            def get(cls, key: str) -> str:
                return cls._registry[key]

            @classmethod
            def list_keys(cls) -> list[str]:
                return list(cls._registry.keys())

            @classmethod
            def contains(cls, key: str) -> bool:
                return key in cls._registry

            @classmethod
            def clear(cls) -> None:
                cls._registry.clear()

        EmptyRegistry.clear()
        assert EmptyRegistry.list_keys() == []

    def test_protocol_clear_is_idempotent(self) -> None:
        """clear() can be called multiple times safely."""

        class SafeRegistry:
            _registry: ClassVar[dict[str, str]] = {}

            @classmethod
            def register(cls, key: str, value: str) -> None:
                cls._registry[key] = value

            @classmethod
            def get(cls, key: str) -> str:
                return cls._registry[key]

            @classmethod
            def list_keys(cls) -> list[str]:
                return list(cls._registry.keys())

            @classmethod
            def contains(cls, key: str) -> bool:
                return key in cls._registry

            @classmethod
            def clear(cls) -> None:
                cls._registry.clear()

        SafeRegistry.clear()
        SafeRegistry.clear()
        SafeRegistry.clear()
        assert SafeRegistry.list_keys() == []


class TestRegistryProtocolTypeVars:
    """Tests for K and V type variables in protocol."""

    def test_type_vars_allow_any_types(self) -> None:
        """K and V can be any types."""

        class CallableRegistry:
            _registry: ClassVar[dict[str, type]] = {}

            @classmethod
            def register(cls, key: str, value: type) -> None:
                cls._registry[key] = value

            @classmethod
            def get(cls, key: str) -> type:
                return cls._registry[key]

            @classmethod
            def list_keys(cls) -> list[str]:
                return list(cls._registry.keys())

            @classmethod
            def contains(cls, key: str) -> bool:
                return key in cls._registry

            @classmethod
            def clear(cls) -> None:
                cls._registry.clear()

        CallableRegistry.clear()
        CallableRegistry.register("str", str)
        CallableRegistry.register("int", int)
        assert CallableRegistry.get("str") is str
        assert CallableRegistry.get("int") is int
        CallableRegistry.clear()
