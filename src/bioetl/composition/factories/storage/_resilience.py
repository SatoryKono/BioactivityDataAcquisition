"""Backward-compatible re-export for `bioetl.composition.factories.storage.resilience`."""

from __future__ import annotations

from bioetl.composition.factories.storage import resilience as _public

create_silver_atomic_retry_policy = _public.create_silver_atomic_retry_policy
create_silver_merge_resilience_policy = _public.create_silver_merge_resilience_policy

__all__ = ['create_silver_atomic_retry_policy', 'create_silver_merge_resilience_policy']
