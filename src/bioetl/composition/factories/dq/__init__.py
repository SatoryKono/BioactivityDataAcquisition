"""DQ (Data Quality) factory subpackage with lazy exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.factories.dq.composite_validation import (
        create_composite_validation_service,
    )
    from bioetl.composition.factories.dq.factory import DQServicesFactory

_PUBLIC_EXPORTS = {
    "DQServicesFactory": (
        "bioetl.composition.factories.dq.factory",
        "DQServicesFactory",
    ),
    "create_composite_validation_service": (
        "bioetl.composition.factories.dq.composite_validation",
        "create_composite_validation_service",
    ),
}

__all__ = [*_PUBLIC_EXPORTS]


def __getattr__(name: str) -> object:
    export = _PUBLIC_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = export
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
