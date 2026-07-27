"""Verify bootstrap suite wires bootstrap_cache fixtures (T-04 / #6599)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.bootstrap_cache import (
    BootstrapMetadataCache,
    CachedBootstrapMetadata,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONFIGS_ROOT = _REPO_ROOT / "configs"


def test_cached_bootstrap_metadata_is_immutable_and_reusable(
    bootstrap_metadata_cache: BootstrapMetadataCache,
    cached_bootstrap_metadata: CachedBootstrapMetadata,
) -> None:
    second = bootstrap_metadata_cache.get_or_build(configs_root=_CONFIGS_ROOT)
    assert isinstance(cached_bootstrap_metadata, CachedBootstrapMetadata)
    assert cached_bootstrap_metadata.pipeline_names
    assert cached_bootstrap_metadata.provider_definitions
    assert bootstrap_metadata_cache.build_count >= 1
    assert second.cache_key == cached_bootstrap_metadata.cache_key
    assert second is cached_bootstrap_metadata


def test_fresh_registries_are_isolated_clones(
    fresh_pipeline_registry,
    fresh_provider_registry,
    cached_bootstrap_metadata: CachedBootstrapMetadata,
) -> None:
    pipelines = list(fresh_pipeline_registry.list_pipelines())
    providers = list(fresh_provider_registry.list_providers())
    assert pipelines
    assert providers
    assert set(pipelines) == set(cached_bootstrap_metadata.pipeline_names)
    assert set(providers) == {
        definition.name for definition in cached_bootstrap_metadata.provider_definitions
    }
