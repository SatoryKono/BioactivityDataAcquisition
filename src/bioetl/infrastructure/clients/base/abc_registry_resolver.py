"""Resolver for ABC registry and implementation mappings."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
from typing import Any, Callable

import yaml


class ABCRegistryError(Exception):
    """Base error for ABC registry resolution."""


class RoleNotFoundError(ABCRegistryError):
    """Raised when a requested role is not present in the registry."""

    def __init__(self, role: str) -> None:
        super().__init__(f"ABC role not found: {role}")
        self.role = role


class DefaultFactoryNotFoundError(ABCRegistryError):
    """Raised when default factory is missing for a role."""

    def __init__(self, role: str) -> None:
        super().__init__(f"Default factory not found for role: {role}")
        self.role = role


class ImplementationNotFoundError(ABCRegistryError):
    """Raised when implementation is missing for a role."""

    def __init__(self, role: str, implementation: str) -> None:
        super().__init__(f"Implementation '{implementation}' not found for role: {role}")
        self.role = role
        self.implementation = implementation


def _import_from_path(dotted_path: str) -> Any:
    module_path, _, attribute = dotted_path.rpartition(".")
    if not module_path or not attribute:
        raise ABCRegistryError(f"Invalid dotted path: {dotted_path}")

    module = importlib.import_module(module_path)
    try:
        return getattr(module, attribute)
    except AttributeError as exc:
        raise ABCRegistryError(
            f"Attribute '{attribute}' not found in module '{module_path}'"
        ) from exc


@dataclass
class ABCRegistryResolver:
    """Resolves ABC registry definitions and factories/implementations."""

    registry_path: Path = Path(__file__).with_name("abc_registry.yaml")
    impls_path: Path = Path(__file__).with_name("abc_impls.yaml")

    def __post_init__(self) -> None:
        self._registry = self._load_yaml(self.registry_path)
        self._impls = self._load_yaml(self.impls_path)

    def resolve_default_factory(self, role: str) -> Callable[..., Any]:
        """Return default factory callable for the given role."""
        data = self._impls.get(role)
        if data is None:
            raise RoleNotFoundError(role)
        factory_path = data.get("default_factory")
        if not factory_path:
            raise DefaultFactoryNotFoundError(role)
        factory = _import_from_path(factory_path)
        if not callable(factory):
            raise DefaultFactoryNotFoundError(role)
        return factory

    def resolve_implementation(self, role: str, implementation: str) -> type[Any]:
        """Return implementation class for the given role and name."""
        data = self._impls.get(role)
        if data is None:
            raise RoleNotFoundError(role)
        implementations: dict[str, str] | None = data.get("implementations")
        if not implementations or implementation not in implementations:
            raise ImplementationNotFoundError(role, implementation)
        return _import_from_path(implementations[implementation])

    def resolve_role(self, role: str) -> type[Any]:
        """Return ABC class for given role from registry mapping."""
        role_path = self._registry.get(role)
        if role_path is None:
            raise RoleNotFoundError(role)
        return _import_from_path(role_path)

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}


__all__ = [
    "ABCRegistryError",
    "RoleNotFoundError",
    "DefaultFactoryNotFoundError",
    "ImplementationNotFoundError",
    "ABCRegistryResolver",
]

