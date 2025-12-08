"""Shared mixins and helpers for ChEMBL Pandera schemas."""

import pandera as pa
from pandera.typing import Series

HEX_64_PATTERN = r"^[a-f0-9]{64}$"
GENERATED_COLUMN_ORDER: list[str] = [
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "extracted_at",
]


def build_output_column_order(business_columns: list[str]) -> list[str]:
    """Append generated columns to business column order."""

    return [*business_columns, *GENERATED_COLUMN_ORDER]


class BaseGeneratedColumnsSchema(pa.DataFrameModel):
    """Базовая схема с едиными служебными колонками и Config."""

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
    extracted_at: Series[str] = pa.Field(
        nullable=True, description="Дата и время извлечения"
    )

    class Config:
        """Строгая конфигурация Pandera для всех схем."""

        strict = True
        coerce = True
        ordered = True
