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
    cached_bootstrap_metadata: Any,
    cached_populated_isolated_registry: Any,
    cached_provider_registry: Any,
) -> None:
    """Per-test clones can be cleared without corrupting cached baseline state."""
    cached_populated_isolated_registry.clear()
    cached_provider_registry.clear()

    assert "chembl_activity" in cached_bootstrap_metadata.pipeline_names
    assert "chembl" in {
        definition.name for definition in cached_bootstrap_metadata.provider_definitions
    }


def test_two_registry_clones_do_not_share_mutable_provider_config(
    cached_bootstrap_metadata: Any,
) -> None:
    """Mutation of one reconstructed config must not leak to another clone."""
    from tests.helpers.bootstrap_cache import clone_provider_registry

    first = clone_provider_registry(cached_bootstrap_metadata)
    second = clone_provider_registry(cached_bootstrap_metadata)
    first_config = first.get("chembl")
    second_config = second.get("chembl")

    first_config.default_kwargs["leak"] = True
    if first_config.http_config is not None:
        first_config.http_config.rate_overrides["leak"] = 1.0

    assert "leak" not in second_config.default_kwargs
    assert second_config.http_config is None or (
        "leak" not in second_config.http_config.rate_overrides
    )
