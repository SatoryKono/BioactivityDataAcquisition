"""Public resilience-policy facade for storage factory wiring."""

from __future__ import annotations

from bioetl.composition.factories.storage._resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)

__all__ = [
    "create_silver_atomic_retry_policy",
    "create_silver_merge_resilience_policy",
]

