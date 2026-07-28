"""Isolation proof for session-scoped bootstrap metadata cache (#6892)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.bootstrap_cache import (
    BootstrapMetadataCache,
    CachedBootstrapMetadata,
    clone_pipeline_registry,
)

pytestmark = pytest.mark.unit


def test_session_cached_bootstrap_metadata_is_immutable_catalog(
    cached_bootstrap_metadata: CachedBootstrapMetadata,
    bootstrap_metadata_cache: BootstrapMetadataCache,
) -> None:
    """Session fixture reuses one catalog build for immutable metadata."""
    configs_root = Path(cached_bootstrap_metadata.cache_key.configs_root)
    again = bootstrap_metadata_cache.get_or_build(configs_root=configs_root)
    assert bootstrap_metadata_cache.build_count >= 1
    assert again.cache_key == cached_bootstrap_metadata.cache_key
    assert again.pipeline_names == cached_bootstrap_metadata.pipeline_names
    assert cached_bootstrap_metadata.pipeline_names
    assert cached_bootstrap_metadata.provider_definitions


def test_fresh_pipeline_registry_clones_are_independent(
    cached_bootstrap_metadata: CachedBootstrapMetadata,
) -> None:
    left = clone_pipeline_registry(cached_bootstrap_metadata)
    right = clone_pipeline_registry(cached_bootstrap_metadata)
    assert left is not right
    assert left.list_pipelines() == right.list_pipelines()
