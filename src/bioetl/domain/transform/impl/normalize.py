"""
Normalization implementation for domain entities.
"""

from typing import Any

import pandas as pd

from bioetl.domain.transform.normalizers import (
    normalize_pcid,
    normalize_pmid,
    normalize_uniprot,
)

# Aliases for backward compatibility or convenience
normalize_pubmed_id = normalize_pmid
normalize_pubchem_cid = normalize_pcid
normalize_uniprot_id = normalize_uniprot


def normalize_scalar(value: Any, mode: str = "default") -> Any:
    """
    Нормализует скалярное значение.

    Modes:
    - "default": trim + lower (str), round 3 (float)
    - "id": trim + upper (str)
    - "sensitive": trim only (str)
    """
    if value is None:
        return None

    if isinstance(value, (list, tuple, dict)):
        if not value:
            return None
        raise ValueError(f"Expected scalar, got {type(value).__name__}")

    if _is_missing_value(value):
        return None

    if isinstance(value, float):
        return round(value, 3)

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        return _normalize_string_value(value, mode)

    return value


def _is_missing_value(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except ValueError:
        return False


def _normalize_string_value(value: str, mode: str) -> str | None:
    val = value.strip()
    if not val:
        return None
    if mode == "id":
        return val.upper()
    if mode == "sensitive":
        return val
    return val.lower()


__all__ = [
    "normalize_scalar",
    "normalize_pubmed_id",
    "normalize_pubchem_cid",
    "normalize_uniprot_id",
]


