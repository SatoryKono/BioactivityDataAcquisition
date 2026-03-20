"""Unit tests for provider registration aggregate module.

Tests register_all_providers function — idempotency, composition of bio
and biblio configs, and integration with ProviderRegistry.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.providers.provider_registry import (
    ProviderConfig,
    ProviderRegistry,
    create_provider_registry,
)
from bioetl.composition.providers.registration import (
    _build_provider_configs,
    register_all_providers,
)
from bioetl.composition.providers._registration_contracts import (
    create_provider_assembly_support,
)


@pytest.fixture(autouse=True)
def _isolated_registry():
    """Restore ProviderRegistry state after each test."""
    original = dict(ProviderRegistry._providers)
    ProviderRegistry._providers.clear()
    yield
    ProviderRegistry._providers.clear()
    ProviderRegistry._providers.update(original)


@pytest.mark.unit
class TestRegisterAllProviders:
    """Tests for register_all_providers function."""

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_registers_bio_providers(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """Should register providers returned by _get_bio_provider_configs."""
        registry = create_provider_registry()
        mock_adapter = MagicMock()
        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter),
        }
        mock_biblio.return_value = {}

        register_all_providers(registry=registry)

        assert registry.is_registered("chembl")

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_registers_biblio_providers(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """Should register providers returned by _get_biblio_provider_configs."""
        registry = create_provider_registry()
        mock_adapter = MagicMock()
        mock_bio.return_value = {}
        mock_biblio.return_value = {
            "pubmed": ProviderConfig(adapter_class=mock_adapter),
        }

        register_all_providers(registry=registry)

        assert registry.is_registered("pubmed")

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_idempotent_does_not_overwrite(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """Second call should skip already-registered providers (idempotent)."""
        registry = create_provider_registry()
        mock_adapter_v1 = MagicMock(name="v1")
        mock_adapter_v2 = MagicMock(name="v2")

        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter_v1),
        }
        mock_biblio.return_value = {}

        register_all_providers(registry=registry)

        # Change config for second call
        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter_v2),
        }

        register_all_providers(registry=registry)

        # Original config should still be in place
        config = registry.get("chembl")
        assert config.adapter_class is mock_adapter_v1

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_registers_multiple_providers_from_both_groups(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """Should merge bio and biblio configs and register all."""
        registry = create_provider_registry()
        mock_adapter = MagicMock()
        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter),
            "pubchem": ProviderConfig(adapter_class=mock_adapter),
        }
        mock_biblio.return_value = {
            "pubmed": ProviderConfig(adapter_class=mock_adapter),
            "crossref": ProviderConfig(adapter_class=mock_adapter),
        }

        register_all_providers(registry=registry)

        for name in ("chembl", "pubchem", "pubmed", "crossref"):
            assert registry.is_registered(name), f"Missing: {name}"

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_safe_to_call_multiple_times(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """register_all_providers should not raise when called multiple times."""
        registry = create_provider_registry()
        mock_adapter = MagicMock()
        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter),
        }
        mock_biblio.return_value = {}

        # Should not raise
        register_all_providers(registry=registry)
        register_all_providers(registry=registry)
        register_all_providers(registry=registry)

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_injected_registry_isolated_from_default_singleton(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """Explicit registry injection should not mutate the default singleton."""
        registry = create_provider_registry()
        mock_adapter = MagicMock()
        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter),
        }
        mock_biblio.return_value = {}

        register_all_providers(registry=registry)

        assert registry.is_registered("chembl")
        assert not ProviderRegistry.is_registered("chembl")

    @patch("bioetl.composition.providers.registration.create_provider_assembly_support")
    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_builds_default_assembly_support_bound_to_explicit_registry(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
        mock_create_support: MagicMock,
    ) -> None:
        """Explicit registry registration should bind default support to that registry."""
        registry = create_provider_registry()
        support = MagicMock(name="support")
        mock_create_support.return_value = support
        mock_bio.return_value = {}
        mock_biblio.return_value = {}

        register_all_providers(registry=registry)

        mock_create_support.assert_called_once_with(provider_registry=registry)


@pytest.mark.unit
class TestBuildProviderConfigs:
    """Tests for _build_provider_configs helper."""

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_returns_merged_dict(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """Should return a merged dict of bio + biblio configs."""
        mock_adapter = MagicMock()
        mock_bio.return_value = {"chembl": ProviderConfig(adapter_class=mock_adapter)}
        mock_biblio.return_value = {
            "pubmed": ProviderConfig(adapter_class=mock_adapter)
        }

        result = _build_provider_configs()

        assert "chembl" in result
        assert "pubmed" in result
        assert len(result) == 2

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_biblio_overrides_bio_on_conflict(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """When same key in both groups, biblio wins (dict merge order)."""
        mock_adapter_bio = MagicMock(name="bio")
        mock_adapter_biblio = MagicMock(name="biblio")
        mock_bio.return_value = {
            "shared": ProviderConfig(adapter_class=mock_adapter_bio)
        }
        mock_biblio.return_value = {
            "shared": ProviderConfig(adapter_class=mock_adapter_biblio)
        }

        result = _build_provider_configs()

        assert result["shared"].adapter_class is mock_adapter_biblio

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_passes_shared_assembly_support_to_group_builders(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """Bio and biblio builders should receive the same support bundle."""

        @dataclass(frozen=True)
        class StubSupport:
            marker: str = "support"

        support = StubSupport()
        mock_bio.return_value = {}
        mock_biblio.return_value = {}

        _build_provider_configs(assembly_support=support)

        mock_bio.assert_called_once_with(assembly_support=support)
        mock_biblio.assert_called_once_with(assembly_support=support)


@pytest.mark.unit
def test_default_provider_assembly_support_binds_explicit_registry_for_http_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Support bundle should thread explicit registry into HTTP client creation."""
    registry = create_provider_registry()
    captured: dict[str, object] = {}

    def _fake_create_for_provider(provider: str, settings=None, **kwargs: object) -> str:
        captured["provider"] = provider
        captured["provider_registry"] = kwargs.get("provider_registry")
        return "client"

    monkeypatch.setattr(
        "bioetl.composition.factories.datasource.http_client.HttpClientFactory.create_for_provider",
        _fake_create_for_provider,
    )

    support = create_provider_assembly_support(provider_registry=registry)
    result = support.create_http_client("chembl")

    assert result == "client"
    assert captured["provider"] == "chembl"
    assert captured["provider_registry"] is registry
