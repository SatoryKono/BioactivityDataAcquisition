# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for the canonical datasource creator helper."""

from __future__ import annotations

from inspect import signature
from unittest.mock import MagicMock

import pytest

import bioetl.composition.factories.datasource.data_source_factory as data_source_factory_module
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

    def test_bound_creator_builds_registry_callback_once(self) -> None:
        """Repeated calls reuse the provider-bound callback after lazy resolution."""
        registry = MagicMock()
        registry.list_providers.return_value = ["isolated_provider"]
        registry.is_registered.return_value = True
        expected = MagicMock(name="data_source")
        registered_creator = MagicMock(return_value=expected)
        registry.build_data_source_creator.return_value = registered_creator

        bound_creator = get_data_source_creator(
            "isolated_provider",
            provider_registry=registry,
        )
        call_kwargs = {
            "settings": MagicMock(),
            "pipeline_config": MagicMock(),
            "logger": MagicMock(),
        }

        assert bound_creator(**call_kwargs) is expected
        assert bound_creator(**call_kwargs) is expected
        registry.build_data_source_creator.assert_called_once_with("isolated_provider")
        assert registered_creator.call_count == 2

    def test_default_registry_rejects_name_outside_configured_provider_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An unloaded default registry still fails closed on unknown config names."""
        registry = MagicMock()
        registry.list_providers.return_value = []
        registry.is_registered.return_value = False
        monkeypatch.setattr(
            data_source_factory_module,
            "resolve_provider_registry",
            lambda *_args, **_kwargs: registry,
        )
        monkeypatch.setattr(
            data_source_factory_module,
            "_get_default_provider_names",
            lambda: frozenset({"chembl", "pubchem"}),
        )

        with pytest.raises(
            KeyError,
            match="Unknown provider: missing. Available: chembl, pubchem",
        ):
            get_data_source_creator("missing")

    def test_default_provider_names_resolve_through_config_root_seam(
        self,
        tmp_path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        providers_dir = tmp_path / "providers"
        providers_dir.mkdir()
        (providers_dir / "chembl.yaml").write_text("provider: chembl\n")
        (providers_dir / "ignored.yml").write_text("provider: ignored\n")

        data_source_factory_module._get_default_provider_names.cache_clear()
        monkeypatch.setattr(
            data_source_factory_module,
            "resolve_config_subdir",
            lambda _subdir: providers_dir,
        )

        try:
            provider_names = data_source_factory_module._get_default_provider_names()
        finally:
            data_source_factory_module._get_default_provider_names.cache_clear()

        assert provider_names == frozenset({"chembl", "uniprot_idmapping"})


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
