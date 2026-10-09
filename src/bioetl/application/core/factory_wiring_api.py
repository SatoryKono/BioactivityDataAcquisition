"""Legacy flat facade for composition-owned pipeline factory wiring."""

from __future__ import annotations

from bioetl.application.core.wiring import factory as _factory

__all__ = [*_factory.__all__]


def __getattr__(name: str) -> object:
    """Resolve legacy factory exports through the canonical lazy facade."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(_factory, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
