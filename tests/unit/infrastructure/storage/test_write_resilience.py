"""Unit tests for storage write resilience policy builders."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.storage.delta.resilience import (
    build_default_silver_merge_policy,
)

pytestmark = pytest.mark.unit


def test_build_default_silver_merge_policy_matches_pipeline_defaults() -> None:
    """Default storage merge policy must stay aligned with PipelineSettings defaults."""
    policy = build_default_silver_merge_policy()

    assert policy.execution_timeout_seconds == pytest.approx(45.0)
    assert policy.commit_retry.enabled is True
    assert policy.commit_retry.max_retries == 3
    assert policy.commit_retry.base_delay_seconds == pytest.approx(0.250)
    assert policy.commit_retry.max_delay_seconds == pytest.approx(2.0)
    assert policy.commit_retry.jitter_seconds == pytest.approx(0.050)
    assert policy.commit_retry.adaptive is True
    assert policy.timeout_retry.enabled is True
    assert policy.timeout_retry.max_retries == 1
    assert policy.timeout_retry.base_delay_seconds == pytest.approx(0.200)
    assert policy.timeout_retry.max_delay_seconds == pytest.approx(2.0)
    assert policy.timeout_retry.jitter_seconds == pytest.approx(0.050)
    assert policy.timeout_retry.adaptive is True
    assert policy.plain_write_process_isolation is False
