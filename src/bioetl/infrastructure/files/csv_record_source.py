"""Compatibility shim: lazy access to application-layer CSV record sources."""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ["CsvRecordSourceImpl", "IdListRecordSourceImpl"]

CsvRecordSourceImpl: Any
IdListRecordSourceImpl: Any


def __getattr__(name: str) -> Any:  # pragma: no cover - thin shim
    if name in __all__:
        module = importlib.import_module("bioetl.application.files.csv_record_source")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:  # pragma: no cover - thin shim
    return sorted(list(globals().keys()) + __all__)
