from __future__ import annotations

from enum import Enum


class PipelineType(str, Enum):
    EXTRACT_ONLY = "extract"
    FULL = "full"
    TRANSFORM_ONLY = "transform"


__all__ = ["PipelineType"]

