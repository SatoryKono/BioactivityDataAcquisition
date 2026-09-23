"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

__all__ = [
    "DEFAULT_ROOT",
    "SRC_ROOT",
    "T",
]

T = TypeVar("T")

SRC_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOT = Path(__file__).resolve().parents[4]
