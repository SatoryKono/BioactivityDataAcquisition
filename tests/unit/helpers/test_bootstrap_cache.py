"""Tests for opt-in bootstrap registry cache helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.bootstrap_cache import (
    BootstrapCacheKey,
    BootstrapRegistryCache,
    fingerprint_bootstrap_inputs,
)

pytestmark = pytest.mark.unit


def test_bootstrap_cache_reuses_registries_for_same_fingerprint(tmp_path: Path) -> None:
    configs_root = tmp_path / "configs"
    configs_root.mkdir()
    (configs_root / "entity.yaml").write_text("pipeline: alpha\n", encoding="utf-8")
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "registry.py").write_text("REGISTRY = 'alpha'\n", encoding="utf-8")

    def fingerprint(configs_root: Path) -> BootstrapCacheKey:
        return fingerprint_bootstrap_inputs(
            configs_root=configs_root,
            source_roots=(source_root,),
        )

    cache = BootstrapRegistryCache(
        pipeline_metadata_builder=lambda: ("pipeline",),
        provider_metadata_builder=tuple,
        fingerprint_builder=fingerprint,
    )

    first = cache.get_or_build(configs_root=configs_root)
    second = cache.get_or_build(configs_root=configs_root)

    assert first is second
    assert cache.build_count == 1


def test_bootstrap_cache_invalidates_when_config_content_changes(
    tmp_path: Path,
) -> None:
    configs_root = tmp_path / "configs"
    configs_root.mkdir()
    config_file = configs_root / "entity.yaml"
    config_file.write_text("pipeline: alpha\n", encoding="utf-8")

    cache = BootstrapRegistryCache(
        pipeline_metadata_builder=tuple,
        provider_metadata_builder=tuple,
    )

    first = cache.get_or_build(configs_root=configs_root)
    config_file.write_text("pipeline: beta\n", encoding="utf-8")
    second = cache.get_or_build(configs_root=configs_root)

    assert first is not second
    assert first.cache_key != second.cache_key
    assert cache.build_count == 2
