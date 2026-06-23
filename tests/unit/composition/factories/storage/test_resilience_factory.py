"""Unit tests for storage resilience factory helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.composition.factories.storage.resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)


def _build_settings(*, profile: str = "default") -> SimpleNamespace:
    return SimpleNamespace(
        pipeline=SimpleNamespace(
            silver_resilience_enabled=True,
            silver_metadata_atomic_retry=SimpleNamespace(
                enabled=True,
                adaptive_backoff=False,
                max_retries=5,
                base_delay_seconds=0.01,
                max_delay_seconds=0.08,
                jitter_seconds=0.0,
            ),
            silver_merge_retry=SimpleNamespace(
                enabled=True,
                adaptive_backoff=False,
                max_retries=2,
                base_delay_seconds=0.2,
                max_delay_seconds=1.0,
                jitter_seconds=0.0,
            ),
            silver_merge_timeout=SimpleNamespace(
                profile=profile,
                execution_timeout_seconds=45.0,
                unit_execution_timeout_seconds=12.0,
                e2e_execution_timeout_seconds=80.0,
                retry_enabled=True,
                adaptive_backoff=False,
                max_retries=1,
                base_delay_seconds=0.1,
                max_delay_seconds=0.5,
                jitter_seconds=0.0,
            ),
        )
    )


@pytest.mark.unit
def test_create_silver_atomic_retry_policy_uses_settings_values() -> None:
    settings = _build_settings()
    policy = create_silver_atomic_retry_policy(settings)  # type: ignore[arg-type]
    assert policy.max_retries == 5
    assert policy.base_delay_seconds == pytest.approx(0.01)
    assert policy.max_delay_seconds == pytest.approx(0.08)
    assert policy.adaptive is False


@pytest.mark.unit
@pytest.mark.parametrize(
    ("profile", "expected_timeout"),
    [
        ("default", 45.0),
        ("unit", 12.0),
        ("e2e", 80.0),
    ],
)
def test_create_silver_merge_policy_resolves_profile_timeout(
    profile: str,
    expected_timeout: float,
) -> None:
    settings = _build_settings(profile=profile)
    policy = create_silver_merge_resilience_policy(settings)  # type: ignore[arg-type]
    assert policy.execution_timeout_seconds == expected_timeout
