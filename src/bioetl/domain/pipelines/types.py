"""Pipeline types for defining execution mode."""

from __future__ import annotations

from enum import Enum


class PipelineType(str, Enum):
    """Pipeline execution mode type."""

    EXTRACT_ONLY = "extract"
    FULL = "full"
    TRANSFORM_ONLY = "transform"


__all__ = ["PipelineType"]
