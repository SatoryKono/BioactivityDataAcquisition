# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Fixtures for integration tests."""

from __future__ import annotations

import platform
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

import pytest


class _CacheClearable(Protocol):
    def cache_clear(self) -> None: ...


if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter


def _build_token_bucket_rate_limiter() -> TokenBucketRateLimiter:
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

    return TokenBucketRateLimiter(rate=10.0, capacity=100)


def _build_circuit_breaker_guard() -> CircuitBreakerGuard:
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard

    return CircuitBreakerGuard(provider="integration_test")


def _clear_runtime_config_caches() -> None:
    """Clear runtime settings/config caches after environment mutations."""
    from bioetl.infrastructure.config._base import get_pipeline_config, get_settings
    from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
    from bioetl.infrastructure.config.source_config_loader import load_source_config

    for cached_function in (
        get_settings,
        get_pipeline_config,
        load_pipeline_config,
        load_source_config,
    ):
        cast(_CacheClearable, cached_function).cache_clear()


def _is_wsl() -> bool:
    """Return whether integration tests run inside Windows Subsystem for Linux."""
    return "microsoft" in platform.release().lower()


@pytest.fixture
def replay_runtime_root(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide replay I/O on a native filesystem and clean it deterministically.

    WSL checkouts commonly live below ``/mnt`` on cloud-backed Windows storage.
    Replay gates perform real control-plane and Delta writes, so their sandbox
    must live on the native Linux filesystem instead of suppressing the tests.
    Other platforms retain pytest's normal per-test ``tmp_path`` isolation.
    """
    if not _is_wsl():
        yield tmp_path
        return

    native_tmp = Path("/tmp")
    if not native_tmp.is_dir():
        pytest.fail("WSL replay gates require the native Linux /tmp filesystem")
    sandbox = Path(tempfile.mkdtemp(prefix="bioetl-replay-", dir=native_tmp))
    try:
        yield sandbox
    finally:
        _clear_runtime_config_caches()
        shutil.rmtree(sandbox, ignore_errors=False)


@pytest.fixture
def relaxed_dq_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Enable relaxed DQ thresholds explicitly for replay-heavy integration tests."""
    _clear_runtime_config_caches()
    monkeypatch.setenv("BIOETL_TEST_RELAXED_DQ", "1")
    monkeypatch.setenv("BIOETL_PIPELINE__RELAXED_DQ", "1")
    _clear_runtime_config_caches()
    yield
    _clear_runtime_config_caches()


@pytest.fixture
def strict_dq_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Force strict DQ mode for integration tests that validate strict behavior."""
    _clear_runtime_config_caches()
    monkeypatch.delenv("BIOETL_TEST_RELAXED_DQ", raising=False)
    monkeypatch.setenv("BIOETL_PIPELINE__RELAXED_DQ", "0")
    _clear_runtime_config_caches()
    yield
    _clear_runtime_config_caches()


@pytest.fixture
def token_bucket() -> TokenBucketRateLimiter:
    """Default rate limiter for integration HTTP clients."""
    return _build_token_bucket_rate_limiter()


@pytest.fixture
def circuit_breaker() -> CircuitBreakerGuard:
    """Default circuit breaker for integration HTTP clients."""
    return _build_circuit_breaker_guard()
