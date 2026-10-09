"""Canonical grouping for transform primitives and field-spec helpers."""

from __future__ import annotations
# ruff: noqa: I001

from types import ModuleType

from bioetl.application.core import dict_transformers as _dict_transformers
from bioetl.application.core.entity_id import (
    ENTITY_ID_SCHEME_VERSION as ENTITY_ID_SCHEME_VERSION,
    compute_publication_term_entity_id as compute_publication_term_entity_id,
    compute_subcellular_fraction_entity_id as compute_subcellular_fraction_entity_id,
)
from bioetl.application.core import field_specs as _field_specs

__all__ = [
    "ENTITY_ID_SCHEME_VERSION",
    "compute_publication_term_entity_id",
    "compute_subcellular_fraction_entity_id",
    *_dict_transformers.__all__,
    *_field_specs.__all__,
]


def __getattr__(name: str) -> object:
    """Resolve field-spec exports from their canonical owner module."""
    source_module: ModuleType
    if name in _dict_transformers.__all__:
        source_module = _dict_transformers
    elif name in _field_specs.__all__:
        source_module = _field_specs
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(source_module, name)
    globals()[name] = value
    return value
