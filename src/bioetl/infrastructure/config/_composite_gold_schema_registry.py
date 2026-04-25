"""Lazy registry for composite Gold contract schemas."""

from __future__ import annotations

from collections.abc import Mapping

__all__ = [
    "DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY",
]


def _build_default_gold_schema_registry() -> dict[str, type]:
    from bioetl.domain.contracts import (
        CompositeActivityGoldSchema,
        CompositeAssayGoldSchema,
        CompositeMoleculeGoldSchema,
        CompositePublicationGoldSchema,
        CompositeTargetGoldSchema,
    )

    return {
        "activity": CompositeActivityGoldSchema,
        "assay": CompositeAssayGoldSchema,
        "molecule": CompositeMoleculeGoldSchema,
        "publication": CompositePublicationGoldSchema,
        "target": CompositeTargetGoldSchema,
    }


class _LazyCompositeGoldSchemaRegistry(Mapping[str, type]):
    def __init__(self) -> None:
        self._registry: dict[str, type] | None = None

    def _materialize(self) -> dict[str, type]:
        if self._registry is None:
            self._registry = _build_default_gold_schema_registry()
        return self._registry

    def __getitem__(self, key: str) -> type:
        return self._materialize()[key]

    def __iter__(self):
        return iter(self._materialize())

    def __len__(self) -> int:
        return len(self._materialize())


DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY: Mapping[str, type] = (
    _LazyCompositeGoldSchemaRegistry()
)
