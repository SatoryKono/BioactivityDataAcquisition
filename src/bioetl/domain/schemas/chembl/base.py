"""Shared mixins and helpers for ChEMBL Pandera schemas.

Terminology:
    acquisition_timestamp: Timestamp when the data was acquired from the source.
        Deprecated alias: extracted_at (will be removed in v3.0).
"""

from typing import Any

import pandera.pandas as pa
from pandera.typing import Series

HEX_64_PATTERN = r"^[a-f0-9]{64}$"

# Canonical column names for generated columns
GENERATED_COLUMN_ORDER: list[str] = [
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "acquisition_timestamp",
]

# Deprecated column name mapping (for backward compatibility)
# TODO: Remove in v3.0
DEPRECATED_COLUMN_ALIASES: dict[str, str] = {
    "extracted_at": "acquisition_timestamp",
}


def build_output_column_order(business_columns: list[str]) -> list[str]:
    """Append generated columns to business column order."""

    return [*business_columns, *GENERATED_COLUMN_ORDER]


_FieldDefinition = tuple[Any, Any]
_FieldMapping = dict[str, _FieldDefinition]


class BaseGeneratedColumnsModel(pa.DataFrameModel):
    """Базовая схема с едиными служебными колонками и Config.

    Column naming:
        acquisition_timestamp: Canonical name for the data acquisition timestamp.
            Deprecated alias: extracted_at (will be removed in v3.0).
    """

    hash_row: Series[str] = pa.Field(
        str_matches=HEX_64_PATTERN,
        description="Хэш всей строки (64 hex символа)",
    )
    hash_business_key: Series[str] = pa.Field(
        nullable=True,
        str_matches=HEX_64_PATTERN,
        description="Хэш бизнес-ключа",
    )
    index: Series[int] = pa.Field(ge=0, description="Порядковый номер строки")
    database_version: Series[str] = pa.Field(
        nullable=True, description="Версия базы данных"
    )
    acquisition_timestamp: Series[str] = pa.Field(
        nullable=True,
        description="Дата и время получения данных из источника",
        alias="extracted_at",  # Backward compatibility alias
    )

    class Config:
        """Строгая конфигурация Pandera для всех схем."""

        strict = True
        coerce = True
        ordered = True

    @classmethod
    def _collect_fields(cls) -> _FieldMapping:
        """Упорядочивает служебные колонки в конце списка."""

        fields = super()._collect_fields()
        if cls is BaseGeneratedColumnsModel or not fields:
            return fields

        return cls._append_generated_columns(fields)

    @staticmethod
    def _append_generated_columns(fields: _FieldMapping) -> _FieldMapping:
        """Возвращает копию мапы полей с hash/index-колонками в конце."""

        generated = {
            name: fields[name] for name in GENERATED_COLUMN_ORDER if name in fields
        }
        ordered_fields: _FieldMapping = {}

        for name, value in fields.items():
            if name in generated:
                continue
            ordered_fields[name] = value

        for name in GENERATED_COLUMN_ORDER:
            definition = generated.get(name)
            if definition is None:
                continue
            ordered_fields[name] = definition

        return ordered_fields


# Backward compatibility alias for existing imports.
BaseGeneratedColumnsSchema = BaseGeneratedColumnsModel
