"""Typed contexts for bootstrap functions returning multiple dependencies.

This module provides frozen dataclasses that replace untyped tuples
in bootstrap and factory functions, enabling IDE autocomplete and
type-safe access to returned dependencies.

All contexts are immutable (frozen=True) and contain only data, no logic.

Usage:
    >>> context = PipelineCallbacksContext(
    ...     transform=transform_fn,
    ...     gold_filter=filter_fn,
    ...     gold_transform=gold_transform_fn,
    ... )
    >>> context.transform  # IDE autocomplete works
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.resilience import CircuitBreakerConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        SilverDQConfigPort,
    )

from bioetl.domain.ports.pipeline_callbacks import (
    GoldFilterCallback,
    GoldTransformCallback,
    TransformCallback,
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
    """Typed context for pipeline transformation callbacks.

    Replaces untyped callback tuple from extract_pipeline_callbacks().

    Attributes:
        transform: Bronze to Silver transformation callback.
            Expected signature: (context, record, index) -> Awaitable[dict | None]
            Implements TransformCallback protocol.
        gold_filter: Callback to determine if record should be written to Gold.
            Expected signature: (context, record) -> bool
            Implements GoldFilterCallback protocol.
        gold_transform: Silver to Gold transformation callback.
            Expected signature: (context, silver_record) -> dict
            Implements GoldTransformCallback protocol.
    """

    transform: TransformCallback
    gold_filter: GoldFilterCallback
    gold_transform: GoldTransformCallback


@dataclass(frozen=True)
class DQConfigsContext:
    """Typed context for Data Quality report configurations.

    Replaces untyped tuple[BronzeDQConfigPort | None, SilverDQConfigPort | None,
    GoldDQConfigPort | None] from _extract_dq_configs().

    Attributes:
        bronze: DQ report configuration for Bronze layer (None if disabled).
        silver: DQ report configuration for Silver layer (None if disabled).
        gold: DQ report configuration for Gold layer (None if disabled).
    """

    bronze: BronzeDQConfigPort | None
    silver: SilverDQConfigPort | None
    gold: GoldDQConfigPort | None


@dataclass(frozen=True)
class DQOutputPathsContext:
    """Typed context for DQ report output paths.

    Replaces untyped tuple[str | None, str | None, str | None, bool]
    from _extract_dq_output_paths().

    Attributes:
        bronze_path: Output path for Bronze DQ reports (None if not configured).
        silver_path: Output path for Silver DQ reports (None if not configured).
        gold_path: Output path for Gold DQ reports (None if not configured).
        flat_structure: Whether to use flat directory structure for DQ reports.
    """

    bronze_path: str | None
    silver_path: str | None
    gold_path: str | None
    flat_structure: bool = False


@dataclass(frozen=True)
class RateLimitContext:
    """Typed context for rate limiting configuration.

    Replaces untyped tuple[float, int] from _get_rate_limit_from_config().

    Attributes:
        rate: Requests per second.
        capacity: Token bucket capacity (burst limit).
    """

    rate: float
    capacity: int


# CircuitBreakerConfig is imported from bioetl.domain.resilience (canonical definition)
# and re-exported via __all__ for backward compatibility.
