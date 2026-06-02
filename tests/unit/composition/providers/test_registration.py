"""Unit tests for provider registration aggregate module.

Tests register_all_providers function — idempotency, composition of bio
and biblio configs, and integration with ProviderRegistry.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch
from unittest.mock import call

import pytest

from bioetl.composition.providers.provider_registry import (
    ProviderConfig,
    ProviderRegistry,
    create_provider_registry,
)
from bioetl.composition.providers.registration import (
    _build_provider_configs,
    _merge_provider_config_families,
    register_all_providers,
)
from bioetl.composition.providers._config_helpers import (
    _build_provider_family_config_map,
    _build_provider_family_http_config_map,
    _resolve_provider_family_registration_context,
)
from bioetl.composition.providers._registration_contracts import (
    HttpProviderConfigSpec,
    bind_provider_data_source_creator,
    build_data_source_provider_config,
    build_http_provider_config,
    build_http_provider_config_map,
    create_provider_assembly_support,
    resolve_provider_assembly_support,
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

        assert registry.is_registered("chembl")

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

    @patch(
        "bioetl.composition.providers.registration.resolve_provider_assembly_support"
    )
    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_builds_default_assembly_support_bound_to_explicit_registry(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
        mock_resolve_support: MagicMock,
    ) -> None:
        """Explicit registry registration should bind default support to that registry."""
        registry = create_provider_registry()
        support = MagicMock(name="support")
        mock_resolve_support.return_value = support
        mock_bio.return_value = {}
        mock_biblio.return_value = {}

        register_all_providers(registry=registry)

        assert mock_resolve_support.call_args_list == [
            call(None, provider_registry=registry),
            call(support),
        ]

    @patch("bioetl.composition.providers.registration.resolve_provider_registry")
    @patch("bioetl.composition.providers.registration._get_bio_provider_configs")
    @patch("bioetl.composition.providers.registration._get_biblio_provider_configs")
    def test_default_registration_uses_default_registry_helper(
        self,
        mock_biblio: MagicMock,
        mock_bio: MagicMock,
        mock_resolve_provider_registry: MagicMock,
    ) -> None:
        """Implicit registration should resolve the default registry via helper."""
        default_registry = create_provider_registry()
        mock_resolve_provider_registry.return_value = default_registry
        mock_bio.return_value = {}
        mock_biblio.return_value = {}

        register_all_providers()

        mock_resolve_provider_registry.assert_called_once_with(None)


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
def test_merge_provider_config_families_uses_declared_builder_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Family merge helper should preserve ordered override semantics."""

    def _build_alpha(*, assembly_support):
        assert assembly_support == "support"
        return {
            "shared": ProviderConfig(adapter_class=MagicMock(name="alpha")),
            "alpha": ProviderConfig(adapter_class=MagicMock(name="alpha_only")),
        }

    def _build_beta(*, assembly_support):
        assert assembly_support == "support"
        return {
            "shared": ProviderConfig(adapter_class=MagicMock(name="beta")),
            "beta": ProviderConfig(adapter_class=MagicMock(name="beta_only")),
        }

    monkeypatch.setattr(
        "bioetl.composition.providers.registration._iter_provider_config_family_builders",
        lambda: (_build_alpha, _build_beta),
    )

    result = _merge_provider_config_families(assembly_support="support")

    assert set(result) == {"shared", "alpha", "beta"}
    assert result["shared"].adapter_class._mock_name == "beta"


@pytest.mark.unit
def test_default_provider_assembly_support_binds_explicit_registry_for_http_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Support bundle should thread explicit registry into HTTP client creation."""
    registry = create_provider_registry()
    captured: dict[str, object] = {}

    def _fake_create_for_provider(
        provider: str, settings=None, **kwargs: object
    ) -> str:
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


@pytest.mark.unit
def test_resolve_provider_assembly_support_returns_injected_support_unchanged() -> None:
    """Injected assembly support should remain the canonical owner when present."""
    support = MagicMock(name="support")

    assert resolve_provider_assembly_support(support) is support


@pytest.mark.unit
def test_resolve_provider_assembly_support_binds_explicit_registry_when_building_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default support creation should thread the explicit registry once."""
    registry = create_provider_registry()
    sentinel_support = MagicMock(name="support")
    captured: dict[str, object] = {}

    def _fake_create_provider_assembly_support(*, provider_registry=None):
        captured["provider_registry"] = provider_registry
        return sentinel_support

    monkeypatch.setattr(
        "bioetl.composition.providers._registration_contracts.create_provider_assembly_support",
        _fake_create_provider_assembly_support,
    )

    result = resolve_provider_assembly_support(None, provider_registry=registry)

    assert result is sentinel_support
    assert captured["provider_registry"] is registry


@pytest.mark.unit
def test_resolve_provider_family_registration_context_reuses_injected_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Family registration helper should preserve the injected support owner."""
    support = MagicMock(name="support")
    rate_limits = {"chembl": MagicMock(name="chembl_rate")}

    monkeypatch.setattr(
        "bioetl.composition.providers._config_helpers._get_rate_limits_from_config",
        lambda *providers: rate_limits,
    )

    resolved_support, resolved_rate_limits = (
        _resolve_provider_family_registration_context(
            "chembl",
            assembly_support=support,
        )
    )

    assert resolved_support is support
    assert resolved_rate_limits is rate_limits


@pytest.mark.unit
def test_resolve_provider_family_registration_context_builds_default_support_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Family registration helper should delegate default support creation once."""
    sentinel_support = MagicMock(name="support")
    rate_limits = {"pubmed": MagicMock(name="pubmed_rate")}
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "bioetl.composition.providers._config_helpers._get_rate_limits_from_config",
        lambda *providers: captured.update(providers=providers) or rate_limits,
    )
    monkeypatch.setattr(
        "bioetl.composition.providers._registration_contracts.resolve_provider_assembly_support",
        lambda assembly_support: (
            captured.update(assembly_support=assembly_support) or sentinel_support
        ),
    )

    resolved_support, resolved_rate_limits = (
        _resolve_provider_family_registration_context(
            "pubmed",
            "crossref",
        )
    )

    assert resolved_support is sentinel_support
    assert resolved_rate_limits is rate_limits
    assert captured["assembly_support"] is None
    assert captured["providers"] == ("pubmed", "crossref")


@pytest.mark.unit
def test_build_provider_family_http_config_map_uses_shared_manifest_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Family HTTP config builder should delegate through the canonical map helper."""
    support = MagicMock(name="support")
    rate_limits = {"chembl": MagicMock(name="chembl_rate")}
    sentinel_spec = MagicMock(name="spec")
    sentinel_config_map = {"chembl": MagicMock(name="config")}
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "bioetl.composition.providers._registration_contracts.build_http_provider_config_map",
        lambda *, specs, assembly_support: (
            captured.update(
                specs=specs,
                assembly_support=assembly_support,
            )
            or sentinel_config_map
        ),
    )

    result = _build_provider_family_http_config_map(
        rate_limits=rate_limits,
        assembly_support=support,
        spec_builder=lambda incoming_rate_limits: (
            captured.update(rate_limits=incoming_rate_limits) or (sentinel_spec,)
        ),
    )

    assert result is sentinel_config_map
    assert captured["rate_limits"] is rate_limits
    assert captured["specs"] == (sentinel_spec,)
    assert captured["assembly_support"] is support


@pytest.mark.unit
def test_build_provider_family_config_map_composes_context_http_and_extra_builders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Top-level family config builder should compose the full scaffold once."""
    support = MagicMock(name="support")
    rate_limits = {"chembl": MagicMock(name="chembl_rate")}
    http_configs = {"chembl": MagicMock(name="http_config")}
    extra_configs = {"pubchem": MagicMock(name="extra_config")}
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "bioetl.composition.providers._config_helpers._resolve_provider_family_registration_context",
        lambda *providers, assembly_support=None: (
            captured.update(
                providers=providers,
                assembly_support=assembly_support,
            )
            or (support, rate_limits)
        ),
    )
    monkeypatch.setattr(
        "bioetl.composition.providers._config_helpers._build_provider_family_http_config_map",
        lambda *, rate_limits, assembly_support, spec_builder: (
            captured.update(
                http_rate_limits=rate_limits,
                http_assembly_support=assembly_support,
                http_spec_builder=spec_builder,
            )
            or http_configs
        ),
    )

    sentinel_spec_builder = MagicMock(name="spec_builder")
    sentinel_extra_builder = MagicMock(name="extra_builder", return_value=extra_configs)

    result = _build_provider_family_config_map(
        "chembl",
        "pubchem",
        assembly_support=None,
        http_spec_builder=sentinel_spec_builder,
        extra_config_builder=sentinel_extra_builder,
    )

    assert result == http_configs | extra_configs
    assert captured["providers"] == ("chembl", "pubchem")
    assert captured["assembly_support"] is None
    assert captured["http_rate_limits"] is rate_limits
    assert captured["http_assembly_support"] is support
    assert captured["http_spec_builder"] is sentinel_spec_builder
    sentinel_extra_builder.assert_called_once_with(rate_limits, support)


@pytest.mark.unit
def test_bind_provider_data_source_creator_captures_shared_support_instance() -> None:
    """Support-aware creators should be bound through one canonical helper path."""
    support = MagicMock(name="support")

    def _creator(settings, pipeline_config, logger, **kwargs):
        return kwargs["assembly_support"]

    bound = bind_provider_data_source_creator(
        _creator,
        assembly_support=support,
    )

    result = bound(MagicMock(), MagicMock(), MagicMock())

    assert result is support


@pytest.mark.unit
def test_build_http_provider_config_uses_canonical_http_provider_shape() -> None:
    """HTTP-oriented provider configs should be assembled through one shared path."""
    support = MagicMock(name="support")
    adapter_creator = MagicMock(name="adapter_creator")

    def _creator(settings, pipeline_config, logger, **kwargs):
        return kwargs["assembly_support"]

    config = build_http_provider_config(
        adapter_class=MagicMock(name="adapter_class"),
        rate=7.5,
        capacity=15,
        rate_overrides={"api_key": 30.0},
        adapter_creator=adapter_creator,
        data_source_creator=_creator,
        assembly_support=support,
    )

    assert config.http_config is not None
    assert config.http_config.rate == pytest.approx(7.5)
    assert config.http_config.capacity == 15
    assert config.http_config.rate_overrides == {"api_key": 30.0}
    assert config.requires_http_client is True
    assert config.requires_logger is True
    assert config.adapter_creator is adapter_creator
    assert config.data_source_creator is not None
    assert config.data_source_creator(MagicMock(), MagicMock(), MagicMock()) is support


@pytest.mark.unit
def test_build_data_source_provider_config_supports_non_http_special_case() -> None:
    """Non-HTTP provider entries should still use one canonical assembly helper."""
    creator = MagicMock(name="creator")
    adapter_creator = MagicMock(name="adapter_creator")

    config = build_data_source_provider_config(
        adapter_class=MagicMock(name="adapter_class"),
        http_config=None,
        requires_http_client=False,
        requires_logger=True,
        adapter_creator=adapter_creator,
        data_source_creator=creator,
    )

    assert config.http_config is None
    assert config.requires_http_client is False
    assert config.requires_logger is True
    assert config.adapter_creator is adapter_creator
    assert config.data_source_creator is creator


@pytest.mark.unit
def test_build_http_provider_config_map_builds_multiple_entries_from_manifest() -> None:
    """HTTP provider manifests should reuse one shared map-construction helper."""
    support = MagicMock(name="support")
    adapter_creator = MagicMock(name="adapter_creator")

    def _creator(settings, pipeline_config, logger, **kwargs):
        return kwargs["assembly_support"]

    configs = build_http_provider_config_map(
        specs=(
            HttpProviderConfigSpec(
                provider_name="alpha",
                adapter_class=MagicMock(name="alpha_adapter"),
                rate=1.5,
                capacity=3,
                data_source_creator=_creator,
            ),
            HttpProviderConfigSpec(
                provider_name="beta",
                adapter_class=MagicMock(name="beta_adapter"),
                rate=7.5,
                capacity=15,
                rate_overrides={"api_key": 30.0},
                adapter_creator=adapter_creator,
                data_source_creator=_creator,
            ),
        ),
        assembly_support=support,
    )

    assert set(configs) == {"alpha", "beta"}
    assert configs["alpha"].http_config is not None
    assert configs["alpha"].http_config.rate == pytest.approx(1.5)
    assert configs["beta"].http_config is not None
    assert configs["beta"].http_config.capacity == 15
    assert configs["beta"].http_config.rate_overrides == {"api_key": 30.0}
    assert configs["beta"].adapter_creator is adapter_creator
    assert configs["alpha"].data_source_creator is not None
    assert (
        configs["alpha"].data_source_creator(MagicMock(), MagicMock(), MagicMock())
        is support
    )
