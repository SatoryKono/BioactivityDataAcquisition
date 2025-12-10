"""Типы пайплайнов для определения режима выполнения."""

from __future__ import annotations

from enum import Enum


class PipelineType(str, Enum):
    """Тип режима выполнения пайплайна."""

    EXTRACT_ONLY = "extract"
    FULL = "full"
    TRANSFORM_ONLY = "transform"


__all__ = ["PipelineType"]
