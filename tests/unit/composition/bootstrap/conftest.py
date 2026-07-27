"""Bootstrap unit suite fixtures with optional immutable metadata reuse (T-04).

Session-scoped payloads are limited to immutable pipeline/provider catalog
metadata (see ``tests/helpers/bootstrap_cache.py``). Mutable services, ports,
and observability exporters are never cached.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.bootstrap_cache import (
    BootstrapMetadataCache,
    CachedBootstrapMetadata,
    clone_pipeline_registry,
    clone_provider_registry,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONFIGS_ROOT = _REPO_ROOT / "configs"


@pytest.fixture(scope="session")
def bootstrap_metadata_cache() -> BootstrapMetadataCache:
    """Session-scoped fingerprint cache for immutable bootstrap catalogs."""
    return BootstrapMetadataCache()


@pytest.fixture(scope="session")
def cached_bootstrap_metadata(
    bootstrap_metadata_cache: BootstrapMetadataCache,
) -> CachedBootstrapMetadata:
    """Immutable pipeline/provider catalog for the current configs fingerprint."""
    return bootstrap_metadata_cache.get_or_build(configs_root=_CONFIGS_ROOT)


@pytest.fixture
def fresh_pipeline_registry(cached_bootstrap_metadata: CachedBootstrapMetadata):
    """Per-test pipeline registry clone rebuilt from immutable metadata."""
    return clone_pipeline_registry(cached_bootstrap_metadata)


@pytest.fixture
def fresh_provider_registry(cached_bootstrap_metadata: CachedBootstrapMetadata):
    """Per-test provider registry clone rebuilt from immutable metadata."""
    return clone_provider_registry(cached_bootstrap_metadata)
