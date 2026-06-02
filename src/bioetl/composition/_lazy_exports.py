"""Shared helpers for composition lazy public export facades."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from importlib import import_module
from typing import Callable


def resolve_lazy_export(
    *,
    module_globals: dict[str, object],
    public_exports: Mapping[str, str],
    module_name: str,
    name: str,
    cache: bool = False,
) -> object:
    """Resolve a lazy public export and optionally cache it in module globals."""
    target_module = public_exports.get(name)
    if target_module is None:
        raise AttributeError(f"module {module_name!r} has no attribute {name!r}")

    value = getattr(import_module(target_module), name)
    if cache:
        module_globals[name] = value
    return value


def lazy_export_dir(
    *,
    module_globals: Mapping[str, object],
    public_exports: Mapping[str, str],
    explicit_exports: Iterable[str],
) -> list[str]:
    """Return stable introspection results for lazy-export modules."""
    return sorted(set(module_globals) | set(public_exports) | set(explicit_exports))


def build_lazy_export_hooks(
    *,
    module_globals: dict[str, object],
    public_exports: Mapping[str, str],
    module_name: str,
    explicit_exports: Iterable[str],
    cache: bool = False,
) -> tuple[Callable[[str], object], Callable[[], list[str]]]:
    """Build module-level ``__getattr__`` and ``__dir__`` hooks for lazy exports."""

    def _module_getattr(name: str) -> object:
        return resolve_lazy_export(
            module_globals=module_globals,
            public_exports=public_exports,
            module_name=module_name,
            name=name,
            cache=cache,
        )

    def _module_dir() -> list[str]:
        return lazy_export_dir(
            module_globals=module_globals,
            public_exports=public_exports,
            explicit_exports=explicit_exports,
        )

    return _module_getattr, _module_dir


def install_lazy_exports(
    *,
    module_globals: dict[str, object],
    public_exports: Mapping[str, str],
    module_name: str,
    explicit_exports: Iterable[str],
    cache: bool = False,
) -> None:
    """Install module-level lazy export hooks directly into module globals."""
    module_getattr, module_dir = build_lazy_export_hooks(
        module_globals=module_globals,
        public_exports=public_exports,
        module_name=module_name,
        explicit_exports=explicit_exports,
        cache=cache,
    )
    module_globals["__getattr__"] = module_getattr
    module_globals["__dir__"] = module_dir
