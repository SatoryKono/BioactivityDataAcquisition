"""QuarantineEntry public compatibility facade."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from bioetl.domain.aggregates._quarantine_value_objects import (
    QuarantineStatus,
    ResolutionInfo,
)

if TYPE_CHECKING:
    from bioetl.domain.aggregates._quarantine_aggregate import QuarantineEntry

__all__ = ["QuarantineEntry", "QuarantineStatus", "ResolutionInfo"]


def __getattr__(name: str) -> object:
    if name == "QuarantineEntry":
        module = importlib.import_module(
            "bioetl.domain.aggregates._quarantine_aggregate"
        )
        return module.QuarantineEntry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
