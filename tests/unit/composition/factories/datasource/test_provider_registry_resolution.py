"""Unit tests for datasource provider-registry resolution helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.datasource.provider_registry_resolution import (
    resolve_datasource_provider_registry,
)
from bioetl.composition.providers.provider_registry import create_provider_registry


@pytest.mark.unit
def test_resolve_datasource_provider_registry_uses_explicit_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit registry should bypass the default singleton path."""
    registry = create_provider_registry()
    captured: dict[str, object] = {}

    def _fake_ensure_provider_registry_ready(candidate):
        captured["registry"] = candidate
        return candidate

    monkeypatch.setattr(
        "bioetl.composition.factories.datasource.provider_registry_resolution.ensure_provider_registry_ready",
        _fake_ensure_provider_registry_ready,
    )

    result = resolve_datasource_provider_registry(registry)

    assert result is registry
    assert captured["registry"] is registry


@pytest.mark.unit
def test_resolve_datasource_provider_registry_uses_provider_registry_default_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Implicit resolution should route through ProviderRegistry._get_default()."""
    default_registry = create_provider_registry()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "bioetl.composition.factories.datasource.provider_registry_resolution.ProviderRegistry._get_default",
        classmethod(lambda cls: default_registry),
    )

    def _fake_ensure_provider_registry_ready(candidate):
        captured["registry"] = candidate
        return candidate

    monkeypatch.setattr(
        "bioetl.composition.factories.datasource.provider_registry_resolution.ensure_provider_registry_ready",
        _fake_ensure_provider_registry_ready,
    )

    result = resolve_datasource_provider_registry()

    assert result is default_registry
    assert captured["registry"] is default_registry
