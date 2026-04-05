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

    def _fake_resolve_provider_registry(candidate, *, ensure_ready=False):
        captured["registry"] = candidate
        captured["ensure_ready"] = ensure_ready
        return candidate

    monkeypatch.setattr(
        "bioetl.composition.factories.datasource.provider_registry_resolution.resolve_provider_registry",
        _fake_resolve_provider_registry,
    )

    result = resolve_datasource_provider_registry(registry)

    assert result is registry
    assert captured["registry"] is registry
    assert captured["ensure_ready"] is True


@pytest.mark.unit
def test_resolve_datasource_provider_registry_uses_provider_registry_default_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Implicit resolution should request the default path through one helper seam."""
    captured: dict[str, object] = {}

    sentinel_registry = MagicMock(name="sentinel_registry")

    monkeypatch.setattr(
        "bioetl.composition.factories.datasource.provider_registry_resolution.resolve_provider_registry",
        lambda candidate, *, ensure_ready=False: (
            captured.update(
                registry=candidate,
                ensure_ready=ensure_ready,
            )
            or sentinel_registry
        ),
    )

    result = resolve_datasource_provider_registry()

    assert result is sentinel_registry
    assert captured["registry"] is None
    assert captured["ensure_ready"] is True
