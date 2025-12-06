from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import yaml

REGISTRY_PATH = Path("src/bioetl/infrastructure/clients/base/abc_registry.yaml")
IMPLS_PATH = Path("src/bioetl/infrastructure/clients/base/abc_impls.yaml")


def _load_symbol(path: str):
    module_name, attr = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def test_registry_entries_resolve_to_classes():
    registry = _load_yaml(REGISTRY_PATH)
    assert registry, "abc_registry.yaml must not be empty"

    for role, dotted_path in sorted(registry.items()):
        symbol = _load_symbol(dotted_path)
        assert inspect.isclass(
            symbol
        ), f"{role} at {dotted_path} must resolve to class/Protocol"


def test_impl_entries_resolve_and_match_registry():
    registry = _load_yaml(REGISTRY_PATH)
    impls = _load_yaml(IMPLS_PATH)
    assert impls, "abc_impls.yaml must not be empty"

    for role, cfg in sorted(impls.items()):
        _validate_impl_entry(role, cfg, registry)


def _validate_impl_entry(role: str, cfg: dict, registry: dict) -> None:
    assert role in registry, f"{role} missing in abc_registry.yaml"
    abc_class = _load_symbol(registry[role])

    default_factory = _resolve_default_factory(role, cfg)
    assert callable(default_factory), f"{role} default_factory must be callable"

    implementations = _resolve_implementations(role, cfg)
    for impl_name, impl_path in sorted(implementations.items()):
        _validate_impl_class(role, impl_name, impl_path, abc_class)


def _resolve_default_factory(role: str, cfg: dict):
    default_factory_path = cfg.get("default_factory")
    assert default_factory_path, f"{role} must declare default_factory"
    return _load_symbol(default_factory_path)


def _resolve_implementations(role: str, cfg: dict) -> dict:
    implementations = cfg.get("implementations") or {}
    assert implementations, f"{role} must declare at least one implementation"
    return implementations


def _validate_impl_class(role: str, impl_name: str, impl_path: str, abc_class) -> None:
    impl_class = _load_symbol(impl_path)
    assert inspect.isclass(impl_class), f"{role}:{impl_name} must resolve to class"
    try:
        assert issubclass(
            impl_class, abc_class
        ), f"{impl_class.__name__} must implement {abc_class.__name__}"
    except TypeError:
        # Some Protocols are not runtime-checkable; skip subclass assertion.
        pass
