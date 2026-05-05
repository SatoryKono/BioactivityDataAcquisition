"""Leaf observability helpers shared by pipeline observer modules."""

from __future__ import annotations

from enum import StrEnum

from bioetl.domain.observability_contract import (
    build_observability_contract_payload,
)

__all__ = [
    "LifecyclePhase",
    "build_observability_contract_payload",
]


class LifecyclePhase(StrEnum):
    """Pipeline lifecycle phases for structured observability."""

    STARTUP = "startup"
    PREFLIGHT = "preflight"
    LIFECYCLE_CLEAR = "lifecycle_clear"
    EXECUTION = "execution"
    POSTRUN = "postrun"
    CLEANUP = "cleanup"
