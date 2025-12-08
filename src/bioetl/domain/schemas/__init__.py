"""Утилиты регистрации Pandera-схем домена."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from bioetl.domain.schemas.chembl import (
    ActivityTableSchema,
    AssayTableSchema,
    MoleculeTableSchema,
    PublicationTableSchema,
    TargetTableSchema,
)
from bioetl.domain.schemas.chembl.activity import (
    OUTPUT_COLUMN_ORDER as ACTIVITY_COLUMNS,
)
from bioetl.domain.schemas.chembl.assay import (
    OUTPUT_COLUMN_ORDER as ASSAY_COLUMNS,
)
from bioetl.domain.schemas.chembl.base import GENERATED_COLUMN_ORDER
from bioetl.domain.schemas.registry import default_schema_provider
from bioetl.domain.validation import SchemaProviderABC


SchemaType = type[Any]


@dataclass(frozen=True)
class _EntitySchemaSpec:
    """Описание схемы и её алиасов."""

    entity: str
    schema: SchemaType
    column_order: Sequence[str] | None = None


_ENTITY_SCHEMAS: tuple[_EntitySchemaSpec, ...] = (
    _EntitySchemaSpec("activity", ActivityTableSchema, ACTIVITY_COLUMNS),
    _EntitySchemaSpec("assay", AssayTableSchema, ASSAY_COLUMNS),
    _EntitySchemaSpec("molecule", MoleculeTableSchema, None),
    _EntitySchemaSpec("publication", PublicationTableSchema, None),
    _EntitySchemaSpec("document", PublicationTableSchema, None),
    _EntitySchemaSpec("target", TargetTableSchema, None),
)


def _resolve_column_order(
    schema_cls: SchemaType, column_order: Sequence[str] | None
) -> list[str]:
    if column_order is not None:
        return list(column_order)

    schema = schema_cls.to_schema()
    columns = getattr(schema, "columns", None)
    if columns is None:
        raise TypeError(f"Schema {schema_cls.__name__} does not expose columns.")

    column_names = list(columns.keys())
    metadata = [col for col in GENERATED_COLUMN_ORDER if col in column_names]
    business = [col for col in column_names if col not in metadata]
    return [*business, *metadata]


def _iter_schema_aliases(entity: str) -> tuple[str, str, str]:
    return entity, f"{entity}_input", f"{entity}_output"


def register_schemas(
    schema_provider: SchemaProviderABC | None = None,
) -> SchemaProviderABC:
    """
    Регистрирует все доступные Pandera-схемы в переданном провайдере.

    Возвращает провайдер, в котором зарегистрированы базовые и стадиальные алиасы
    (entity, entity_input, entity_output) для каждого пайплайна.
    """

    provider = schema_provider or default_schema_provider()

    for spec in _ENTITY_SCHEMAS:
        column_order = _resolve_column_order(spec.schema, spec.column_order)
        for alias in _iter_schema_aliases(spec.entity):
            provider.register(alias, spec.schema, column_order=column_order)

    return provider


__all__ = ["register_schemas"]
