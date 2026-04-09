"""BioETL: Bioactivity data acquisition and processing pipeline."""

from __future__ import annotations

import typing

__version__ = "6.1.0"

_PACKAGE_EXPORTS: dict[str, str] = {
    "application": "bioetl.application",
    "composition": "bioetl.composition",
    "domain": "bioetl.domain",
    "infrastructure": "bioetl.infrastructure",
    "interfaces": "bioetl.interfaces",
}

__all__ = ["__version__", *_PACKAGE_EXPORTS]


def __getattr__(
    name: str,
) -> typing.Any:  # Any: lazy package export returns heterogeneous submodules.
    """Lazily expose top-level package namespaces for patch/import stability."""
    try:
        module_name = _PACKAGE_EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    from importlib import import_module

    module = import_module(module_name)
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    """Return stable top-level exports for shell/help introspection."""
    return sorted(set(globals()) | set(__all__))
