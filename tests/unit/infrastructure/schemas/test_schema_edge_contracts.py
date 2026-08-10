"""Compatibility and accessor edges for infrastructure configuration schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.resilience import CircuitBreakerConfig
from bioetl.domain.value_objects.dq_report import DQReportFormat
from bioetl.infrastructure.schemas.dq_report_config import SilverDQReportConfig
from bioetl.infrastructure.schemas.source_config import (
    ProviderConfigYaml,
    SourceCircuitBreakerYamlConfig,
    SourceYamlConfig,
)
from bioetl.infrastructure.validation.contract_validator import (
    ContractAwareGoldValidator,
)

pytestmark = pytest.mark.unit


def test_source_circuit_breaker_converts_to_domain_policy() -> None:
    """Source YAML values survive the schema-to-domain boundary."""
    source = SourceCircuitBreakerYamlConfig(
        failure_threshold=7,
        recovery_timeout=420,
    )

    assert source.to_domain() == CircuitBreakerConfig(
        failure_threshold=7,
        recovery_timeout=420,
    )


def test_provider_config_non_mapping_input_is_rejected_by_model_validation() -> None:
    """The compatibility validator passes non-mappings to Pydantic for rejection."""
    with pytest.raises(ValidationError):
        ProviderConfigYaml.model_validate("not-a-mapping")


def test_source_http_accessors_and_fallback_expose_nested_config() -> None:
    """Runtime accessors reflect the canonical nested HTTP and fallback settings."""
    config = SourceYamlConfig.model_validate(
        {
            "source": {
                "provider_config": {
                    "client": {
                        "max_connections": 37,
                        "max_keepalive_connections": 13,
                        "trust_env": False,
                    },
                    "fallback": {
                        "enabled": True,
                        "primary_lookup_method": "fetch_one",
                    },
                }
            }
        }
    )

    assert config.max_connections == 37
    assert config.max_keepalive_connections == 13
    assert config.trust_env is False
    assert config.fallback is not None
    assert config.fallback.primary_lookup_method == "fetch_one"


def test_silver_dq_report_format_uses_domain_enum() -> None:
    """A validated Silver report format converts to the shared domain enum."""
    assert SilverDQReportConfig(format="yaml").get_format_enum() is DQReportFormat.YAML


def test_gold_contract_validator_rebind_preserves_policy_and_strictness() -> None:
    """Schema rebinding creates an equivalent validator with the same DQ policy."""
    dq_config = DQConfig(
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        rule_bundle_version="2026.08",
    )
    validator = ContractAwareGoldValidator(
        schema=None,
        strict=False,
        dq_config=dq_config,
    )

    rebound = validator.rebind_schema(None)

    assert rebound is not validator
    assert rebound._schema is None
    assert rebound._strict is False
    assert rebound.policy_ref == validator.policy_ref
