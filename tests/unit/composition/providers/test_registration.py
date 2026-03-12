"""Unit tests for provider registration aggregate module.

Tests register_all_providers function — idempotency, composition of bio
and biblio configs, and integration with ProviderRegistry.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.providers.provider_registry import (
    ProviderConfig,
    ProviderRegistry,
)
from bioetl.composition.providers.registration import (
    _build_provider_configs,
    register_all_providers,
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
        mock_adapter = MagicMock()
        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter),
        }
        mock_biblio.return_value = {}

        register_all_providers()

        assert ProviderRegistry.is_registered("chembl")

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_registers_biblio_providers(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """Should register providers returned by _get_biblio_provider_configs."""
        mock_adapter = MagicMock()
        mock_bio.return_value = {}
        mock_biblio.return_value = {
            "pubmed": ProviderConfig(adapter_class=mock_adapter),
        }

        register_all_providers()

        assert ProviderRegistry.is_registered("pubmed")

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_idempotent_does_not_overwrite(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """Second call should skip already-registered providers (idempotent)."""
        mock_adapter_v1 = MagicMock(name="v1")
        mock_adapter_v2 = MagicMock(name="v2")

        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter_v1),
        }
        mock_biblio.return_value = {}

        register_all_providers()

        # Change config for second call
        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter_v2),
        }

        register_all_providers()

        # Original config should still be in place
        config = ProviderRegistry.get("chembl")
        assert config.adapter_class is mock_adapter_v1

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_registers_multiple_providers_from_both_groups(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """Should merge bio and biblio configs and register all."""
        mock_adapter = MagicMock()
        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter),
            "pubchem": ProviderConfig(adapter_class=mock_adapter),
        }
        mock_biblio.return_value = {
            "pubmed": ProviderConfig(adapter_class=mock_adapter),
            "crossref": ProviderConfig(adapter_class=mock_adapter),
        }

        register_all_providers()

        for name in ("chembl", "pubchem", "pubmed", "crossref"):
            assert ProviderRegistry.is_registered(name), f"Missing: {name}"

    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_safe_to_call_multiple_times(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
    ) -> None:
        """register_all_providers should not raise when called multiple times."""
        mock_adapter = MagicMock()
        mock_bio.return_value = {
            "chembl": ProviderConfig(adapter_class=mock_adapter),
        }
        mock_biblio.return_value = {}

        # Should not raise
        register_all_providers()
        register_all_providers()
        register_all_providers()


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
        mock_biblio.return_value = {"pubmed": ProviderConfig(adapter_class=mock_adapter)}

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
        mock_bio.return_value = {"shared": ProviderConfig(adapter_class=mock_adapter_bio)}
        mock_biblio.return_value = {"shared": ProviderConfig(adapter_class=mock_adapter_biblio)}

        result = _build_provider_configs()

        assert result["shared"].adapter_class is mock_adapter_biblio
