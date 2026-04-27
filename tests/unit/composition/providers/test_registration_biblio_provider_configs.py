"""Unit tests for bibliographic ProviderConfig assembly contracts."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.datasource.crossref import create_crossref_adapter
from bioetl.composition.providers.registration_biblio import (
    _create_openalex_adapter_from_settings,
    _create_pubmed_adapter_from_settings,
    _get_biblio_provider_configs,
)


def _rate_limit(rate: float, capacity: int) -> SimpleNamespace:
    """Build a simple rate-limit stub."""
    return SimpleNamespace(rate=rate, capacity=capacity)


@pytest.mark.unit
class TestGetBiblioProviderConfigs:
    """Tests for bibliographic ProviderConfig registry entries."""

    @patch(
        "bioetl.composition.providers._config_helpers._get_rate_limits_from_config"
    )
    def test_contains_expected_provider_keys(
        self,
        mock_get_rate_limits: MagicMock,
    ) -> None:
        mock_get_rate_limits.return_value = {
            "pubmed": _rate_limit(3.0, 6),
            "crossref": _rate_limit(50.0, 100),
            "openalex": _rate_limit(10.0, 20),
            "semanticscholar": _rate_limit(100.0, 200),
        }

        configs = _get_biblio_provider_configs(assembly_support=MagicMock())

        assert set(configs) == {
            "pubmed",
            "crossref",
            "openalex",
            "semanticscholar",
        }

    @patch(
        "bioetl.composition.providers._config_helpers._get_rate_limits_from_config"
    )
    def test_pubmed_provider_config_has_pubmed_api_key_rate_override(
        self,
        mock_get_rate_limits: MagicMock,
    ) -> None:
        mock_get_rate_limits.return_value = {
            "pubmed": _rate_limit(3.0, 6),
            "crossref": _rate_limit(50.0, 100),
            "openalex": _rate_limit(10.0, 20),
            "semanticscholar": _rate_limit(100.0, 200),
        }

        configs = _get_biblio_provider_configs(assembly_support=MagicMock())
        pubmed = configs["pubmed"]

        assert pubmed.http_config is not None
        assert pubmed.http_config.rate_overrides == {"pubmed_api_key": 10.0}

    @patch(
        "bioetl.composition.providers._config_helpers._get_rate_limits_from_config"
    )
    def test_crossref_provider_config_uses_crossref_adapter_factory(
        self,
        mock_get_rate_limits: MagicMock,
    ) -> None:
        mock_get_rate_limits.return_value = {
            "pubmed": _rate_limit(3.0, 6),
            "crossref": _rate_limit(50.0, 100),
            "openalex": _rate_limit(10.0, 20),
            "semanticscholar": _rate_limit(100.0, 200),
        }

        configs = _get_biblio_provider_configs(assembly_support=MagicMock())
        crossref = configs["crossref"]

        assert crossref.custom_creator is create_crossref_adapter
        assert crossref.requires_http_client is True
        assert crossref.requires_logger is True

    @patch(
        "bioetl.composition.providers._config_helpers._get_rate_limits_from_config"
    )
    def test_openalex_and_pubmed_use_composition_local_custom_creators(
        self,
        mock_get_rate_limits: MagicMock,
    ) -> None:
        mock_get_rate_limits.return_value = {
            "pubmed": _rate_limit(3.0, 6),
            "crossref": _rate_limit(50.0, 100),
            "openalex": _rate_limit(10.0, 20),
            "semanticscholar": _rate_limit(100.0, 200),
        }

        configs = _get_biblio_provider_configs(assembly_support=MagicMock())

        assert configs["pubmed"].custom_creator is _create_pubmed_adapter_from_settings
        assert (
            configs["openalex"].custom_creator is _create_openalex_adapter_from_settings
        )

    @patch(
        "bioetl.composition.providers._config_helpers._get_rate_limits_from_config"
    )
    def test_data_source_creators_capture_same_injected_support_instance(
        self,
        mock_get_rate_limits: MagicMock,
    ) -> None:
        mock_get_rate_limits.return_value = {
            "pubmed": _rate_limit(3.0, 6),
            "crossref": _rate_limit(50.0, 100),
            "openalex": _rate_limit(10.0, 20),
            "semanticscholar": _rate_limit(100.0, 200),
        }
        support = MagicMock(name="assembly_support")

        configs = _get_biblio_provider_configs(assembly_support=support)

        for provider_name in configs:
            creator = configs[provider_name].data_source_creator
            assert creator is not None
            assert creator.keywords["assembly_support"] is support
