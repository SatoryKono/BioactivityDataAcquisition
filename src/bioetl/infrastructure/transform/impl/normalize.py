"""
Normalization implementation for domain entities.
"""

from typing import TYPE_CHECKING, Any
import warnings

import pandas as pd

from bioetl.domain.transform.normalizers import (
    normalize_pcid,
    normalize_pmid,
    normalize_uniprot,
)
from bioetl.domain.transform.normalizers.registry import get_normalizer

if TYPE_CHECKING:
    from bioetl.infrastructure.transform.impl.default_normalization_transformer_impl import (  # noqa: E501
        DefaultNormalizationTransformerImpl,
    )

# Aliases for backward compatibility or convenience
normalize_pubmed_id = normalize_pmid
normalize_pubchem_cid = normalize_pcid
normalize_uniprot_id = normalize_uniprot


def normalize_scalar(value: Any, mode: str = "default") -> Any:
    """
    Normalize a scalar value.

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


def __getattr__(name: str) -> Any:
    """Emit deprecation warnings for legacy aliases and lazy imports."""
    # Lazy import to avoid circular dependency
    from bioetl.infrastructure.transform.impl.default_normalization_transformer_impl import (  # noqa: E501
        DefaultNormalizationTransformerImpl as _DefaultImpl,
    )

    if name == "DefaultNormalizationTransformerImpl":
        return _DefaultImpl

    deprecated_aliases = {
        "NormalizationTransformer": _DefaultImpl,
        "NormalizationServiceImpl": _DefaultImpl,
        "NormalizationService": _DefaultImpl,
    }
    if name in deprecated_aliases:
        warnings.warn(
            f"{name} is deprecated. Use DefaultNormalizationTransformerImpl instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return deprecated_aliases[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "normalize_scalar",
    "normalize_pubmed_id",
    "normalize_pubchem_cid",
    "normalize_uniprot_id",
    "get_normalizer",
    "DefaultNormalizationTransformerImpl",
]
