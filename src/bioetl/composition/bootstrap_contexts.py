"""Typed data containers shared by bootstrap and composition factories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime_public_exports import (
    GoldFilterCallback,
    GoldTransformCallback,
    TransformCallback,
)
from bioetl.composition.providers import CircuitBreakerConfig

if TYPE_CHECKING:
    from bioetl.composition.bootstrap.runtime_public_exports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        SilverDQConfigPort,
    )

__all__ = [
    "CircuitBreakerConfig",
    "DQConfigsContext",
    "DQOutputPathsContext",
    "PipelineCallbacksContext",
    "RateLimitContext",
]


@dataclass(frozen=True)
class PipelineCallbacksContext:
    """Pipeline transformation callbacks resolved by composition factories."""

    transform: TransformCallback
    gold_filter: GoldFilterCallback
    gold_transform: GoldTransformCallback


@dataclass(frozen=True)
class DQConfigsContext:
    """Optional Data Quality configuration for each medallion layer."""

    bronze: BronzeDQConfigPort | None
    silver: SilverDQConfigPort | None
    gold: GoldDQConfigPort | None


@dataclass(frozen=True)
class DQOutputPathsContext:
    """Data Quality output paths and layout selection."""

    bronze_path: str | None
    silver_path: str | None
    gold_path: str | None
    flat_structure: bool = False


@dataclass(frozen=True)
class RateLimitContext:
    """Token-bucket rate and burst capacity."""

    rate: float
    capacity: int
