"""Common transformation utilities for all pipelines.

Реализует общие паттерны трансформации для уменьшения дублирования
в ChEMBL и других трансформерах.

Функции:
- flatten_nested_dict: Разворачивание вложенных словарей с префиксом
- extract_list_field: Извлечение поля из списка словарей
- aggregate_nested_lists: Агрегация вложенных списков
- normalize_string: Нормализация строковых полей
- parse_date_field: Парсинг даты с обработкой ошибок
- validate_smiles: Валидация SMILES строки
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from typing import Any, TypeVar

from bioetl.domain.transformations import safe_float, safe_int

T = TypeVar("T")


def flatten_nested_dict(
    data: dict[str, Any] | None,
    prefix: str,
    field_mapping: dict[str, Callable[[Any], Any] | None],
) -> dict[str, Any]:
    """Разворачивает вложенный словарь в плоскую структуру с префиксом.

    Используется для извлечения полей из вложенных структур API
    (molecule_properties, molecule_hierarchy, ligand_efficiency и т.д.).

    Args:
        data: Вложенный словарь для разворачивания. Если None, возвращает
              словарь с None значениями для всех ключей.
        prefix: Префикс для результирующих ключей (e.g., "property_", "hierarchy_").
        field_mapping: Словарь {исходный_ключ: конвертер}.
                       Конвертер может быть safe_float, safe_int или None (без конвертации).

    Returns:
        Плоский словарь с префиксами и сконвертированными значениями.

    Example:
        >>> data = {"alogp": "3.5", "hba": 2}
        >>> mapping = {"alogp": safe_float, "hba": safe_int}
        >>> flatten_nested_dict(data, "property_", mapping)
        {'property_alogp': 3.5, 'property_hba': 2}

        >>> flatten_nested_dict(None, "property_", mapping)
        {'property_alogp': None, 'property_hba': None}

    """
    if not data or not isinstance(data, dict):
        return {f"{prefix}{key}": None for key in field_mapping}

    result: dict[str, Any] = {}
    for source_key, converter in field_mapping.items():
        value = data.get(source_key)
        if converter is not None and value is not None:
            result[f"{prefix}{source_key}"] = converter(value)
        else:
            result[f"{prefix}{source_key}"] = value

    return result


def extract_list_field(
    items: list[dict[str, Any]] | None,
    field: str,
    converter: Callable[[Any], T] | None = None,
) -> list[T] | None:
    """Извлекает значения поля из списка словарей.

    Используется для агрегации полей из компонентов, классификаций и т.д.

    Args:
        items: Список словарей для обработки.
        field: Имя поля для извлечения.
        converter: Опциональный конвертер (safe_int, safe_float и т.д.).
                   Если None, значения возвращаются как есть.

    Returns:
        Список значений или None, если результат пустой.

    Example:
        >>> items = [{"id": "1"}, {"id": "2"}, {"id": None}]
        >>> extract_list_field(items, "id")
        ['1', '2']

        >>> extract_list_field(items, "id", safe_int)
        [1, 2]

    """
    if not items or not isinstance(items, list):
        return None

    values: list[T] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_value = item.get(field)
        if raw_value is None:
            continue

        if converter is not None:
            converted = converter(raw_value)
            if converted is not None:
                values.append(converted)
        else:
            values.append(raw_value)

    return values if values else None


def _extract_nested_values(items: list[dict[str, Any]], field: str) -> list[Any]:
    """Extract all nested list values from a field across items."""
    values: list[Any] = []
    for item in items:
        if isinstance(item, dict):
            nested = item.get(field)
            if isinstance(nested, list):
                values.extend(nested)
    return values


def aggregate_nested_lists(
    items: list[dict[str, Any]] | None,
    field: str,
    deduplicate: bool = True,
) -> list[Any] | None:
    """Агрегирует вложенные списки из списка словарей.

    Используется для сбора synonyms, xrefs и других вложенных списков
    из множества компонентов в один плоский список.

    Args:
        items: Список словарей, каждый из которых может содержать вложенный список.
        field: Имя поля со вложенным списком.
        deduplicate: Если True, удаляет дубликаты из результирующего списка (по умолчанию True).

    Returns:
        Объединённый список или None, если результат пустой.

    Example:
        >>> items = [
        ...     {"synonyms": ["a", "b"]},
        ...     {"synonyms": ["c", "a"]},
        ...     {"other": "data"}
        ... ]
        >>> aggregate_nested_lists(items, "synonyms")
        ['a', 'b', 'c']

    """
    if not isinstance(items, list) or not items:
        return None

    values = _extract_nested_values(items, field)
    if not values:
        return None

    if deduplicate:
        seen: set[str] = set()
        unique: list[Any] = []
        for val in values:
            key = str(val)
            if key not in seen:
                seen.add(key)
                unique.append(val)
        return unique if unique else None

    return values


def normalize_string(value: str | None) -> str | None:
    """Нормализует строковое поле.

    Удаляет пробельные символы по краям и возвращает None для пустых строк.

    Args:
        value: Строка для нормализации.

    Returns:
        Нормализованная строка или None.

    Example:
        >>> normalize_string("  hello world  ")
        'hello world'
        >>> normalize_string("   ")
        None
        >>> normalize_string(None)
        None

    """
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def parse_date_field(
    value: str | None,
    fmt: str = "%Y-%m-%d",
) -> date | None:
    """Парсит строку даты в объект date.

    Безопасный парсинг с обработкой ошибок и невалидных форматов.

    Args:
        value: Строка с датой или None.
        fmt: Формат даты (по умолчанию ISO: YYYY-MM-DD).

    Returns:
        Объект date или None при ошибке парсинга.

    Example:
        >>> parse_date_field("2024-01-15")
        datetime.date(2024, 1, 15)
        >>> parse_date_field("invalid")
        None
        >>> parse_date_field("15/01/2024", "%d/%m/%Y")
        datetime.date(2024, 1, 15)

    """
    if value is None:
        return None

    from datetime import datetime

    try:
        return datetime.strptime(value.strip(), fmt).date()
    except (ValueError, AttributeError):
        return None


# SMILES validation regex (базовая проверка синтаксиса)
# Допускает: буквы, цифры, скобки, точки, знаки, решётки, проценты, @, +, -, =, #
_SMILES_PATTERN = re.compile(r"^[A-Za-z0-9@+\-=#$()\[\]\\/%.*]+$")


def validate_smiles(smiles: str | None) -> bool:
    """Проверяет валидность SMILES строки.

    Выполняет базовую синтаксическую проверку без полного парсинга молекулы.
    Для полной валидации используйте RDKit или другую химическую библиотеку.

    Args:
        smiles: SMILES строка для проверки.

    Returns:
        True если строка соответствует базовому синтаксису SMILES.

    Example:
        >>> validate_smiles("CCO")  # Ethanol
        True
        >>> validate_smiles("C1=CC=CC=C1")  # Benzene
        True
        >>> validate_smiles("")
        False
        >>> validate_smiles(None)
        False
        >>> validate_smiles("invalid smiles with spaces")
        False

    """
    if not smiles or not isinstance(smiles, str):
        return False

    stripped = smiles.strip()
    if not stripped:
        return False

    return bool(_SMILES_PATTERN.match(stripped))


def safe_extract(
    record: dict[str, Any],
    key: str,
    default: T | None = None,
) -> T | Any | None:
    """Безопасно извлекает значение из словаря с логированием.

    Обёртка над dict.get() для унифицированного извлечения полей.
    Для использования с логированием используйте в связке с контекстом.

    Args:
        record: Словарь для извлечения.
        key: Ключ для поиска.
        default: Значение по умолчанию (None).

    Returns:
        Значение по ключу или default.

    Example:
        >>> record = {"name": "test", "value": 42}
        >>> safe_extract(record, "name")
        'test'
        >>> safe_extract(record, "missing", "default")
        'default'

    """
    return record.get(key, default)


# Re-export safe_float and safe_int for convenience
__all__ = [
    "aggregate_nested_lists",
    "extract_list_field",
    "flatten_nested_dict",
    "normalize_string",
    "parse_date_field",
    "safe_extract",
    "safe_float",
    "safe_int",
    "validate_smiles",
]
