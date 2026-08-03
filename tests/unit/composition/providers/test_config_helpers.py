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
"""Unit tests for _config_helpers — generic HTTP data source creator."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_config_helpers_defer_filter_implementation_imports() -> None:
    """Filter implementation dependencies must load only for enabled filters."""
    from bioetl.composition.providers import _config_helpers as helpers

    assert not hasattr(helpers, "CsvFilterReader")
    assert not hasattr(helpers, "FilteredDataSource")


@pytest.mark.unit
class TestCreateHttpDataSource:
    """Tests for _create_http_data_source generic helper."""

    @patch(
        "bioetl.composition.providers._config_helpers._wrap_with_filter",
    )
    @patch(
        "bioetl.composition.factories.datasource.adapter_helpers.AdapterHelpersFactory",
    )
    def test_assembles_adapter_with_helpers_and_wraps(
        self,
        mock_helpers_factory_cls: MagicMock,
        mock_wrap: MagicMock,
    ) -> None:
        from bioetl.composition.providers._config_helpers import (
            _create_http_data_source,
        )

        # Setup HTTP client factory
        support = MagicMock()
        mock_http_client = MagicMock(name="http_client")
        support.create_http_client.return_value = mock_http_client

        # Setup helper services
        mock_helpers = MagicMock()
        mock_helpers.as_injection_kwargs.return_value = {
            "error_handler": MagicMock(),
            "adapter_metrics": MagicMock(),
        }
        mock_helpers_factory_cls.create_http_helpers.return_value = mock_helpers

        # Setup adapter factory
        mock_adapter = MagicMock(name="adapter")
        adapter_factory = MagicMock(return_value=mock_adapter)

        mock_wrapped = MagicMock(name="wrapped")
        mock_wrap.return_value = mock_wrapped

        settings = MagicMock()
        logger = MagicMock()
        metrics = MagicMock()

        result = _create_http_data_source(
            provider="test_provider",
            settings=settings,
            logger=logger,
            filter_config=None,
            metrics=metrics,
            pipeline_name="test_pipeline",
            adapter_factory=adapter_factory,
            extra_kwargs={"custom_param": "value"},
            assembly_support=support,
        )

        # Verify HTTP client created for provider
        support.create_http_client.assert_called_once_with(
            "test_provider", settings, metrics=metrics
        )

        # Verify helpers created
        mock_helpers_factory_cls.create_http_helpers.assert_called_once_with(
            provider="test_provider", logger=logger, metrics=metrics
        )

        # Verify adapter factory called with merged kwargs
        call_kwargs = adapter_factory.call_args.kwargs
        assert call_kwargs["http_client"] is mock_http_client
        assert call_kwargs["logger"] is logger
        assert call_kwargs["metrics"] is metrics
        assert call_kwargs["custom_param"] == "value"
        assert "error_handler" in call_kwargs

        # Verify wrap with filter
        mock_wrap.assert_called_once_with(
            mock_adapter, None, logger, metrics, "test_pipeline"
        )
        assert result is mock_wrapped


@pytest.mark.unit
def test_config_helpers_use_source_config_backed_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.composition.providers import _config_helpers as helpers

    source_config = SimpleNamespace(
        batch_size=321,
        rate_limit=SimpleNamespace(requests_per_second=2.5, burst=9),
        circuit_breaker=SimpleNamespace(failure_threshold=4, recovery_timeout=45),
        provider_config=SimpleNamespace(fallback="fallback-policy"),
        to_adapter_config=lambda *, default_page_size: (
            "adapter-config",
            default_page_size,
        ),
    )
    monkeypatch.setattr(helpers, "load_source_config", lambda provider: source_config)

    assert helpers._get_source_config("chembl") is source_config
    assert helpers._get_batch_size_from_config("chembl") == 321
    assert helpers._get_rate_limit_from_config("chembl").rate == 2.5
    assert helpers._get_rate_limit_from_config("chembl").capacity == 9
    assert (
        helpers._get_rate_limits_from_config("chembl", "pubchem")["pubchem"].rate == 2.5
    )
    assert helpers._get_circuit_breaker_from_config("chembl").failure_threshold == 4
    assert helpers._get_circuit_breaker_from_config("chembl").recovery_timeout == 45
    assert helpers._get_adapter_config("chembl", default_page_size=777) == (
        "adapter-config",
        777,
    )

    data_source = SimpleNamespace(
        provider_name="chembl",
        configure_fallback_policy=MagicMock(),
    )
    helpers._wire_composable_fallback(data_source)
    data_source.configure_fallback_policy.assert_called_once_with("fallback-policy")


@pytest.mark.unit
def test_config_helpers_fall_back_when_source_config_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.composition.providers import _config_helpers as helpers

    def _raise_value_error(provider: str) -> object:
        raise ValueError(provider)

    monkeypatch.setattr(helpers, "load_source_config", _raise_value_error)

    assert helpers._get_source_config("missing") is None
    assert helpers._get_batch_size_from_config("missing", default=25) == 25
    assert helpers._get_rate_limit_from_config("missing").rate == 5.0
    assert helpers._get_rate_limit_from_config("missing").capacity == 10
    assert helpers._get_circuit_breaker_from_config("missing").failure_threshold == 5
    assert (
        helpers._get_adapter_config("missing", default_page_size=123).page_size == 123
    )

    no_provider = SimpleNamespace(provider_name=" ")
    helpers._wire_composable_fallback(no_provider)
    assert not hasattr(no_provider, "configure_fallback_policy")


@pytest.mark.unit
def test_config_helpers_warn_about_extraction_input_filter_overlap() -> None:
    from bioetl.composition.providers import _config_helpers as helpers

    logger = MagicMock()
    extraction_params = SimpleNamespace(
        is_empty=False,
        params={"target_id": "CHEMBL1", "component_id": "10"},
    )
    input_filter = SimpleNamespace(
        enabled=True,
        filter_field="target_id",
        columns=(SimpleNamespace(filter_field="component_id"),),
    )

    helpers._validate_extraction_input_filter_overlap(
        extraction_params,
        input_filter,
        logger,
    )

    assert logger.warning.call_count == 2

    logger.reset_mock()
    helpers._validate_extraction_input_filter_overlap(
        extraction_params,
        SimpleNamespace(enabled=False, filter_field="target_id", columns=()),
        logger,
    )
    assert logger.warning.call_count == 0


@pytest.mark.unit
def test_config_helpers_build_provider_family_config_maps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.composition.providers import _config_helpers as helpers

    support = object()
    rate_limits = {"chembl": object()}
    monkeypatch.setattr(
        helpers,
        "_resolve_provider_family_registration_context",
        lambda *providers, assembly_support=None: (support, rate_limits),
    )
    monkeypatch.setattr(
        helpers,
        "_build_provider_family_http_config_map",
        lambda **kwargs: {"http": kwargs},
    )

    result = helpers._build_provider_family_config_map(
        "chembl",
        assembly_support=object(),
        http_spec_builder=lambda rates: ("spec", rates),
        extra_config_builder=lambda rates, resolved_support: {
            "extra": (rates, resolved_support)
        },
    )

    assert result["http"]["rate_limits"] is rate_limits
    assert result["http"]["assembly_support"] is support
    assert result["extra"] == (rate_limits, support)


@pytest.mark.unit
def test_config_helpers_build_http_map_via_registration_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.composition.providers import _config_helpers as helpers
    from bioetl.composition.providers import _registration_contracts as contracts

    support = object()
    monkeypatch.setattr(
        contracts,
        "build_http_provider_config_map",
        lambda *, specs, assembly_support: {
            "specs": specs,
            "support": assembly_support,
        },
    )

    result = helpers._build_provider_family_http_config_map(
        rate_limits={"chembl": object()},
        assembly_support=support,
        spec_builder=lambda rate_limits: ("chembl-spec", rate_limits),
    )

    assert result["specs"][0] == "chembl-spec"
    assert result["support"] is support


@pytest.mark.unit
def test_normalize_optional_override_treats_placeholders_as_unset() -> None:
    from bioetl.composition.providers import _config_helpers as helpers

    assert helpers._normalize_optional_override(None) is None
    assert helpers._normalize_optional_override("  ") is None
    assert helpers._normalize_optional_override("${BIOETL_OUTPUT}") is None
    assert helpers._normalize_optional_override(" output/path ") == "output/path"
