"""
Serialization utilities for domain entities.
"""
from typing import Any, Callable, Optional, Sequence

import pandas as pd


def serialize_dict(
    value: dict[str, Any], 
    value_normalizer: Optional[Callable[[Any], Any]] = None
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
    value: Sequence[Any],
    value_normalizer: Optional[Callable[[Any], Any]] = None
) -> Any:
    """
    Преобразует список в строку, соединяя элементы через |.
    Для списка словарей объединяет их сериализованные представления.
    """
    if not value:
        return pd.NA

    parts = []
    norm_func = value_normalizer if value_normalizer else (lambda x: x)

    # Check first element to decide strategy (heuristic for homogeneity)
    if len(value) > 0 and isinstance(value[0], dict):
        for item in value:
            if isinstance(item, dict):
                s = serialize_dict(item, value_normalizer=norm_func)
                if s is not pd.NA and s is not None:
                    parts.append(s)
    else:
        for item in value:
            if isinstance(item, (list, dict)):
                continue
            
            val_norm = norm_func(item)
            if val_norm is not pd.NA and val_norm is not None:
                parts.append(str(val_norm))
            
    if not parts:
        return pd.NA
        
    return "|".join(parts)


__all__ = ["serialize_dict", "serialize_list"]
