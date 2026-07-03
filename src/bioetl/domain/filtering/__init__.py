"""Filter configuration for pipeline filtering.

This facade preserves historical ``from bioetl.domain.filtering import X``
imports without eagerly importing all filtering submodules.
"""

from __future__ import annotations

from importlib import import_module

_EXPORT_GROUPS: dict[str, tuple[str, ...]] = {
    "bioetl.domain.filtering._base_filter_config": (
        "BaseFilterConfig",
        "FilterDecision",
    ),
    "bioetl.domain.filtering.column_filter": (
        "FilterOperator",
        "GoldColumnFilter",
    ),
    "bioetl.domain.filtering.gold_config": ("GoldFilterConfig",),
    "bioetl.domain.filtering.input_config": (
        "FilterColumn",
        "InputFilterConfig",
    ),
    "bioetl.domain.filtering.list_filters": (
        "GoldListContainsFilter",
        "GoldListLengthFilter",
    ),
    "bioetl.domain.filtering.load_result": ("FilterLoadResult",),
    "bioetl.domain.filtering.range_filter": ("GoldRangeFilter",),
    "bioetl.domain.filtering.silver_config": ("SilverFilterConfig",),
}

_EXPORT_MODULES = {
    export_name: module_name
    for module_name, export_names in _EXPORT_GROUPS.items()
    for export_name in export_names
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> object:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
