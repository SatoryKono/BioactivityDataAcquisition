"""Backward-compatible re-export for `bioetl.domain.value_objects.publication_field_group_types`."""

from __future__ import annotations

from bioetl.domain.value_objects import publication_field_group_types as _public

for _name in _public.__all__:
    globals()[_name] = getattr(_public, _name)

__all__ = list(_public.__all__)
