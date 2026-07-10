"""Repo-backed checks for opt-in bootstrap cache fixtures."""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def test_cached_populated_isolated_registry_contains_pipeline_factories(
    cached_populated_isolated_registry: Any,
) -> None:
    """Cached pipeline registry clones should expose registered pipelines."""
    pipeline_names = cached_populated_isolated_registry.list_pipelines()

    assert "chembl_activity" in pipeline_names
    assert "pubchem_compound" in pipeline_names


def test_cached_provider_registry_contains_provider_registrations(
    cached_provider_registry: Any,
) -> None:
    """Cached provider registry clones should expose registered providers."""
    provider_names = cached_provider_registry.list_providers()

    assert "chembl" in provider_names
    assert "pubchem" in provider_names


def test_cached_registry_clones_do_not_mutate_session_cache(
    cached_bootstrap_registries: Any,
    cached_populated_isolated_registry: Any,
    cached_provider_registry: Any,
) -> None:
    """Per-test clones can be cleared without corrupting cached baseline state."""
    cached_populated_isolated_registry.clear()
    cached_provider_registry.clear()

    assert "chembl_activity" in (
        cached_bootstrap_registries.pipeline_registry.list_pipelines()
    )
    assert "chembl" in cached_bootstrap_registries.provider_registry.list_providers()
