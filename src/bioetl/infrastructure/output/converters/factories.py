"""Фабрика конвертеров DataFrame для пост-обработки перед записью.

Naming convention:
- create_*() - creates a new instance each time
- get_*() - returns singleton/cached instance
- build_*() - uses builder pattern
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Callable
import warnings

import pandas as pd

from bioetl.domain.clients.base.output.contracts import OutputFrameConverterABC


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=lambda c: str(c).replace("_", "-").lower())


def _dropna_all_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna(how="all")


def _compose(*funcs: Callable[[pd.DataFrame], pd.DataFrame]) -> OutputFrameConverterABC:
    def _convert(df: pd.DataFrame) -> pd.DataFrame:
        out = df
        for fn in funcs:
            out = fn(out)
        return out

    return SimpleNamespace(convert=_convert)  # type: ignore[return-value]


def create_output_frame_converter(
    converter_id: str | None = None,
) -> OutputFrameConverterABC:
    """Create a new output frame converter by identifier.

    Supported values:
      - None | "noop"
      - "rename_columns"
      - "dropna"
      - "rename_and_dropna"
    """

    key = (converter_id or "noop").strip().lower()

    if key in {"", "noop", "none"}:
        return SimpleNamespace(convert=lambda df: df)  # type: ignore[return-value]
    if key == "rename_columns":
        return _compose(_rename_columns)
    if key == "dropna":
        return _compose(_dropna_all_rows)
    if key == "rename_and_dropna":
        return _compose(_rename_columns, _dropna_all_rows)

    return SimpleNamespace(convert=lambda df: df)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Deprecated aliases for backward compatibility
# ---------------------------------------------------------------------------


def default_output_frame_converter(
    converter_id: str | None = None,
) -> OutputFrameConverterABC:
    """DEPRECATED: Use create_output_frame_converter() instead."""
    warnings.warn(
        "default_output_frame_converter is deprecated, "
        "use create_output_frame_converter instead. Will be removed in v3.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_output_frame_converter(converter_id)


__all__ = ["create_output_frame_converter", "default_output_frame_converter"]
