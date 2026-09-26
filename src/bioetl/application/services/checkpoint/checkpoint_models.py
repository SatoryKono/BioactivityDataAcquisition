"""Shared service-model seams for checkpoint administration surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import JsonDict

__all__ = ["CheckpointInfo"]


@dataclass(frozen=True, slots=True)
class CheckpointInfo:
    """Bounded checkpoint evidence exposed by application services."""

    pipeline_name: str
    run_id: str | None
    metadata: JsonDict
