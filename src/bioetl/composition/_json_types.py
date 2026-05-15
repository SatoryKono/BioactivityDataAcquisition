"""Composition-local JSON typing helpers.

These aliases keep root composition APIs typed without pulling broad runtime
typing contracts from ``bioetl.domain.types`` into otherwise thin entrypoint
modules.
"""

from __future__ import annotations

from typing import Any

type JsonDict = dict[str, Any]

__all__ = ["JsonDict"]
