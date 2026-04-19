"""Unit tests for LockConfig.for_pipeline adaptive TTL logic."""

from __future__ import annotations


from bioetl.application.core.config import LockConfig
from bioetl.domain.types import RunType


class TestLockConfigAdaptiveTTL:
    """Verify TTL behaviour of LockConfig.for_pipeline."""

    def test_default_ttl_without_hint(self) -> None:
        """No batch_size_hint → TTL equals configured default (90 s)."""
        cfg = LockConfig.for_pipeline("chembl", "activity", RunType.INCREMENTAL)
        assert cfg.lock_ttl == 90

    def test_adaptive_ttl_scales_with_batch(self) -> None:
        """1 000 records * 0.3 s = 300 s, which exceeds default 90 s."""
        cfg = LockConfig.for_pipeline(
            "chembl", "activity", RunType.INCREMENTAL, batch_size_hint=1000
        )
        assert cfg.lock_ttl == 300  # 1000 * 0.3

    def test_adaptive_ttl_ceiling(self) -> None:
        """Very large batch must be capped at 600 s."""
        cfg = LockConfig.for_pipeline(
            "chembl", "activity", RunType.INCREMENTAL, batch_size_hint=10000
        )
        assert cfg.lock_ttl == 600  # ceiling

    def test_adaptive_ttl_does_not_reduce(self) -> None:
        """adaptive_ttl < lock_ttl → configured lock_ttl wins (max guard)."""
        cfg = LockConfig.for_pipeline(
            "chembl",
            "activity",
            RunType.INCREMENTAL,
            lock_ttl=200,
            batch_size_hint=100,
        )
        assert cfg.lock_ttl == 200  # max(200, 100*0.3=30) = 200

    def test_batch_size_hint_zero_ignored(self) -> None:
        """batch_size_hint=0 must be treated as 'no hint' (guard: > 0)."""
        cfg = LockConfig.for_pipeline(
            "chembl", "activity", RunType.INCREMENTAL, batch_size_hint=0
        )
        assert cfg.lock_ttl == 90  # unchanged default

    def test_batch_size_hint_none_is_backward_compatible(self) -> None:
        """Explicitly passing None must be identical to omitting the parameter."""
        cfg_implicit = LockConfig.for_pipeline(
            "chembl", "activity", RunType.INCREMENTAL
        )
        cfg_explicit = LockConfig.for_pipeline(
            "chembl", "activity", RunType.INCREMENTAL, batch_size_hint=None
        )
        assert cfg_implicit.lock_ttl == cfg_explicit.lock_ttl

    def test_exclusive_lock_key_for_rebuild(self) -> None:
        """REBUILD run type must produce an exclusive lock key regardless of TTL."""
        cfg = LockConfig.for_pipeline(
            "chembl", "activity", RunType.REBUILD, batch_size_hint=500
        )
        assert cfg.exclusive is True
        assert cfg.lock_key == "lock:chembl_activity:exclusive"
        assert cfg.lock_ttl == 150  # 500 * 0.3, above default 90

    def test_ceiling_with_custom_lock_ttl(self) -> None:
        """Even with a high lock_ttl, ceiling must not exceed 600 s."""
        cfg = LockConfig.for_pipeline(
            "chembl",
            "activity",
            RunType.INCREMENTAL,
            lock_ttl=500,
            batch_size_hint=10000,
        )
        assert cfg.lock_ttl == 600
