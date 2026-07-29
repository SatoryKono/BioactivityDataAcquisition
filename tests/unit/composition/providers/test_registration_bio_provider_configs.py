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
"""Unit tests for bio ProviderConfig assembly contracts."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.providers.registration_bio import (
    _create_pubchem_adapter,
    _get_bio_provider_configs,
)


def _rate_limit(rate: float, capacity: int) -> SimpleNamespace:
    """Build a simple rate-limit stub."""
    return SimpleNamespace(rate=rate, capacity=capacity)


@pytest.mark.unit
class TestGetBioProviderConfigs:
    """Tests for bio ProviderConfig registry entries."""

    @patch("bioetl.composition.providers._config_helpers._get_rate_limits_from_config")
    def test_contains_expected_provider_keys__test_get_bio_provider_configs_composition_providers_test_registration_bio_provider_configs_26(
        self,
        mock_get_rate_limits: MagicMock,
    ) -> None:
        mock_get_rate_limits.return_value = {
            "chembl": _rate_limit(10.0, 20),
            "pubchem": _rate_limit(5.0, 10),
            "uniprot": _rate_limit(8.0, 16),
        }

        configs = _get_bio_provider_configs(assembly_support=MagicMock())

        assert set(configs) == {
            "chembl",
            "pubchem",
            "uniprot",
            "uniprot_idmapping",
        }

    @patch("bioetl.composition.providers._config_helpers._get_rate_limits_from_config")
    def test_uniprot_provider_configs_share_uniprot_rate_limit_and_override(
        self,
        mock_get_rate_limits: MagicMock,
    ) -> None:
        mock_get_rate_limits.return_value = {
            "chembl": _rate_limit(10.0, 20),
            "pubchem": _rate_limit(5.0, 10),
            "uniprot": _rate_limit(8.0, 16),
        }

        configs = _get_bio_provider_configs(assembly_support=MagicMock())
        uniprot = configs["uniprot"]
        uniprot_idmapping = configs["uniprot_idmapping"]

        assert uniprot.http_config is not None
        assert uniprot.http_config.rate == pytest.approx(8.0)
        assert uniprot.http_config.capacity == 16
        assert uniprot.http_config.rate_overrides == {"uniprot_api_key": 100.0}
        assert uniprot_idmapping.http_config is not None
        assert uniprot_idmapping.http_config.rate == pytest.approx(8.0)
        assert uniprot_idmapping.http_config.capacity == 16

    @patch("bioetl.composition.providers._config_helpers._get_rate_limits_from_config")
    def test_uniprot_api_key_rate_override_is_optional(
        self,
        mock_get_rate_limits: MagicMock,
    ) -> None:
        mock_get_rate_limits.return_value = {
            "chembl": _rate_limit(10.0, 20),
            "pubchem": _rate_limit(5.0, 10),
            "uniprot": _rate_limit(8.0, 16),
        }

        configs = _get_bio_provider_configs(assembly_support=MagicMock())
        uniprot = configs["uniprot"]

        assert uniprot.http_config is not None
        assert uniprot.http_config.rate == pytest.approx(8.0)
        assert uniprot.http_config.capacity == 16
        assert uniprot.http_config.rate_overrides == {"uniprot_api_key": 100.0}

    @patch("bioetl.composition.providers._config_helpers._get_rate_limits_from_config")
    def test_pubchem_provider_config_uses_non_http_special_case(
        self,
        mock_get_rate_limits: MagicMock,
    ) -> None:
        mock_get_rate_limits.return_value = {
            "chembl": _rate_limit(10.0, 20),
            "pubchem": _rate_limit(5.0, 10),
            "uniprot": _rate_limit(8.0, 16),
        }

        configs = _get_bio_provider_configs(assembly_support=MagicMock())
        pubchem = configs["pubchem"]

        assert pubchem.http_config is not None
        assert pubchem.http_config.rate == pytest.approx(5.0)
        assert pubchem.http_config.capacity == 10
        assert pubchem.adapter_creator is _create_pubchem_adapter
        assert pubchem.requires_http_client is False
        assert pubchem.requires_logger is True

    @patch("bioetl.composition.providers._config_helpers._get_rate_limits_from_config")
    def test_support_aware_creators_capture_same_injected_support_instance(
        self,
        mock_get_rate_limits: MagicMock,
    ) -> None:
        mock_get_rate_limits.return_value = {
            "chembl": _rate_limit(10.0, 20),
            "pubchem": _rate_limit(5.0, 10),
            "uniprot": _rate_limit(8.0, 16),
        }
        support = MagicMock(name="assembly_support")

        configs = _get_bio_provider_configs(assembly_support=support)

        for provider_name in ("chembl", "uniprot", "uniprot_idmapping"):
            creator = configs[provider_name].data_source_creator
            assert creator is not None
            assert creator.keywords["assembly_support"] is support
