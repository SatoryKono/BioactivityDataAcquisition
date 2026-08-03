"""Factory helpers for storage write resilience policies."""

from __future__ import annotations

from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_ATOMIC_REPLACE_RETRY_POLICY,
    DEFAULT_SILVER_MERGE_POLICY,
    AdaptiveRetryPolicy,
    SilverMergeResiliencePolicy,
)

__all__ = [
    "create_silver_atomic_retry_policy",
    "create_silver_merge_resilience_policy",
]


def _resolve_merge_execution_timeout_seconds(timeout_cfg: object) -> float:
    """Resolve merge timeout from default/unit/e2e profile settings."""
    default_timeout = float(getattr(timeout_cfg, "execution_timeout_seconds", 45.0))
    profile = str(getattr(timeout_cfg, "profile", "default")).strip().lower()
    if profile == "unit":
        return float(
            getattr(timeout_cfg, "unit_execution_timeout_seconds", default_timeout)
        )
    if profile == "e2e":
        return float(
            getattr(timeout_cfg, "e2e_execution_timeout_seconds", default_timeout)
        )
    return default_timeout


def create_silver_atomic_retry_policy(settings: Settings) -> AdaptiveRetryPolicy:
    """Create atomic replace retry policy for Silver metadata writes.

    Args:
        settings: Application settings providing silver_resilience_enabled flag
            and silver_metadata_atomic_retry configuration.

    Returns:
        AdaptiveRetryPolicy configured for Silver metadata atomic replace operations.
    """
    if not settings.pipeline.silver_resilience_enabled:
        return DEFAULT_ATOMIC_REPLACE_RETRY_POLICY

    cfg = settings.pipeline.silver_metadata_atomic_retry
    return AdaptiveRetryPolicy(
        enabled=cfg.enabled,
        max_retries=cfg.max_retries,
        base_delay_seconds=cfg.base_delay_seconds,
        max_delay_seconds=cfg.max_delay_seconds,
        jitter_seconds=cfg.jitter_seconds,
        adaptive=cfg.adaptive_backoff,
    )


def create_silver_merge_resilience_policy(
    settings: Settings,
) -> SilverMergeResiliencePolicy:
    """Create merge timeout/retry policy bundle for Silver Delta writes.

    Args:
        settings: Application settings providing silver_resilience_enabled flag
            and silver_merge_retry / silver_merge_timeout configuration.

    Returns:
        SilverMergeResiliencePolicy with timeout and commit retry configuration.
    """
    if not settings.pipeline.silver_resilience_enabled:
        return DEFAULT_SILVER_MERGE_POLICY

    commit_cfg = settings.pipeline.silver_merge_retry
    timeout_cfg = settings.pipeline.silver_merge_timeout

    return SilverMergeResiliencePolicy(
        execution_timeout_seconds=_resolve_merge_execution_timeout_seconds(timeout_cfg),
        commit_retry=AdaptiveRetryPolicy(
            enabled=commit_cfg.enabled,
            max_retries=commit_cfg.max_retries,
            base_delay_seconds=commit_cfg.base_delay_seconds,
            max_delay_seconds=commit_cfg.max_delay_seconds,
            jitter_seconds=commit_cfg.jitter_seconds,
            adaptive=commit_cfg.adaptive_backoff,
        ),
        timeout_retry=AdaptiveRetryPolicy(
            enabled=timeout_cfg.retry_enabled,
            max_retries=timeout_cfg.max_retries,
            base_delay_seconds=timeout_cfg.base_delay_seconds,
            max_delay_seconds=timeout_cfg.max_delay_seconds,
            jitter_seconds=timeout_cfg.jitter_seconds,
            adaptive=timeout_cfg.adaptive_backoff,
        ),
        plain_write_process_isolation=timeout_cfg.plain_write_process_isolation,
    )
