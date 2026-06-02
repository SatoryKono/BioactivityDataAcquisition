"""Tests for the canonical datasource creator helper."""

from __future__ import annotations

from inspect import signature
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.datasource.data_source_factory import (
    get_data_source_creator,
)
from bioetl.composition.providers import ProviderRegistry, ensure_providers_loaded
from bioetl.composition.providers.provider_registry import (
    ProviderConfig,
    create_provider_registry,
)


pytestmark = pytest.mark.unit


class TestCanonicalDataSourceCreator:
    """Tests for the canonical provider-bound creator helper."""

    def test_get_chembl_creator(self):
        ensure_providers_loaded()
        assert callable(get_data_source_creator("chembl"))

    def test_get_pubchem_creator(self):
        ensure_providers_loaded()
        assert callable(get_data_source_creator("pubchem"))

    def test_get_uniprot_creator(self):
        ensure_providers_loaded()
        assert callable(get_data_source_creator("uniprot"))

    def test_get_pubmed_creator(self):
        ensure_providers_loaded()
        assert callable(get_data_source_creator("pubmed"))

    def test_unknown_provider_raises_key_error(self):
        ensure_providers_loaded()
        with pytest.raises(KeyError) as exc_info:
            get_data_source_creator("unknown_provider")

        error_message = str(exc_info.value)
        assert "unknown_provider" in error_message
        assert "Available:" in error_message

    def test_provider_registry_list_covers_common_helper_providers(self):
        ensure_providers_loaded()
        providers = set(ProviderRegistry.list_providers())
        assert {"chembl", "pubchem", "uniprot", "pubmed"} <= providers

    def test_get_data_source_creator_uses_explicit_registry_instance(self):
        isolated = create_provider_registry()
        expected = MagicMock(name="data_source")
        creator = MagicMock(return_value=expected)
        isolated.register(
            "isolated_provider",
            ProviderConfig(
                adapter_class=MagicMock(),
                requires_http_client=False,
                requires_logger=False,
                data_source_creator=creator,
            ),
        )

        bound_creator = get_data_source_creator(
            "isolated_provider",
            provider_registry=isolated,
        )

        result = bound_creator(
            settings=MagicMock(),
            pipeline_config=MagicMock(),
            logger=MagicMock(),
        )

        assert result is expected
        creator.assert_called_once()


class TestDataSourceCreatorProtocol:
    """Tests for provider-bound creator protocol compliance."""

    def test_all_creators_match_protocol(self):
        ensure_providers_loaded()

        expected_params = {
            "settings",
            "pipeline_config",
            "logger",
            "filter_config",
            "metrics",
            "pipeline_name",
        }

        for provider in ProviderRegistry.list_providers():
            creator = get_data_source_creator(provider)
            param_names = set(signature(creator).parameters.keys())
            assert expected_params <= param_names, (
                f"Creator for {provider} missing params: "
                f"{expected_params - param_names}"
            )


class TestWrapWithFilter:
    """Tests for _wrap_with_filter helper function."""

    def test_returns_original_when_no_filter(self):
        from bioetl.composition.providers._config_helpers import _wrap_with_filter

        mock_data_source = MagicMock()

        result = _wrap_with_filter(mock_data_source, None)

        assert result is mock_data_source

    def test_returns_original_when_filter_disabled(self):
        from bioetl.composition.providers._config_helpers import _wrap_with_filter

        mock_data_source = MagicMock()
        mock_filter = MagicMock()
        mock_filter.enabled = False

        result = _wrap_with_filter(mock_data_source, mock_filter)

        assert result is mock_data_source

    def test_wraps_when_filter_enabled(self):
        from bioetl.application.core.filtered_data_source import FilteredDataSource
        from bioetl.composition.providers._config_helpers import _wrap_with_filter

        mock_data_source = MagicMock()
        mock_filter = MagicMock()
        mock_filter.enabled = True

        result = _wrap_with_filter(mock_data_source, mock_filter)

        assert result is not mock_data_source
        assert isinstance(result, FilteredDataSource)

    def test_wraps_with_metrics(self):
        from bioetl.application.core.filtered_data_source import FilteredDataSource
        from bioetl.composition.providers._config_helpers import _wrap_with_filter

        mock_data_source = MagicMock()
        mock_filter = MagicMock()
        mock_filter.enabled = True
        mock_metrics = MagicMock()

        result = _wrap_with_filter(
            mock_data_source, mock_filter, metrics=mock_metrics, pipeline_name="test"
        )

        assert isinstance(result, FilteredDataSource)
