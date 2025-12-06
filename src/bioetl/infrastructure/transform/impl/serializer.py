"""
Serialization utilities for domain entities.
"""

from typing import Any, Callable, Optional, Sequence

import pandas as pd


def serialize_dict(
    value: dict[str, Any], value_normalizer: Optional[Callable[[Any], Any]] = None
) -> Any:
    """
    Преобразует словарь в строку key:value|key:value.
    Пропускает вложенные списки и словари (глубина 1).
    """
    if not value:
        return pd.NA

    parts = []
    norm_func = value_normalizer if value_normalizer else (lambda x: x)

    # Sort keys for determinism
    for k in sorted(value.keys()):
        v = value[k]
        if v is None:
            continue
        if isinstance(v, (list, dict)):
            continue

        # Normalize value
        val_norm = norm_func(v)
        if val_norm is not pd.NA and val_norm is not None:
            parts.append(f"{k}:{val_norm}")

    if not parts:
        return pd.NA

    return "|".join(parts)


def serialize_list(
    value: Sequence[Any], value_normalizer: Optional[Callable[[Any], Any]] = None
) -> Any:
    """
    Преобразует список в строку, соединяя элементы через |.
    Для списка словарей объединяет их сериализованные представления.
    """
    if not value:
        return pd.NA
    norm_func = value_normalizer if value_normalizer else (lambda x: x)

    if value and isinstance(value[0], dict):
        parts = _serialize_dict_items(value, norm_func)
    else:
        parts = _serialize_flat_items(value, norm_func)

    return pd.NA if not parts else "|".join(parts)


def _serialize_dict_items(
    value: Sequence[Any], norm_func: Callable[[Any], Any]
) -> list[str]:
    parts: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        serialized = serialize_dict(item, value_normalizer=norm_func)
        if serialized is not pd.NA and serialized is not None:
            parts.append(serialized)
    return parts


def _serialize_flat_items(
    value: Sequence[Any], norm_func: Callable[[Any], Any]
) -> list[str]:
    parts: list[str] = []
    for item in value:
        if isinstance(item, (list, dict)):
            continue
        val_norm = norm_func(item)
        if val_norm is not pd.NA and val_norm is not None:
            parts.append(str(val_norm))
    return parts


__all__ = ["serialize_dict", "serialize_list"]
