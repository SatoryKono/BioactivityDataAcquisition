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
"""Unit tests for SourceYamlConfig schema — coverage of uncovered properties.

Focuses on the property resolution logic:
- batch_size resolution order
- page_size resolution order
- max_url_length resolution order
- to_adapter_config() with override
- retired legacy alias rejection
"""

from __future__ import annotations

import pytest

from bioetl.infrastructure.schemas.source_config import (
    PaginationConfig,
    ProviderConfigYaml,
    SourceYamlConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source_config(
    *,
    page_size: int | None = None,
    id_batch_size: int | None = None,
    max_url_length: int | None = None,
    strategy: str = "offset",
) -> SourceYamlConfig:
    """Build a SourceYamlConfig with specific pagination values."""
    pagination_data: dict = {"strategy": strategy}
    if page_size is not None:
        pagination_data["page_size"] = page_size
    if id_batch_size is not None:
        pagination_data["id_batch_size"] = id_batch_size
    if max_url_length is not None:
        pagination_data["max_url_length"] = max_url_length

    provider_data: dict = {
        "provider": "test_provider",
        "base_url": "https://api.example.com",
        "pagination": pagination_data,
    }

    return SourceYamlConfig.model_validate(
        {
            "source": {
                "provider_config": provider_data,
                "circuit_breaker": {},
                "rate_limit": {},
            }
        }
    )


# ---------------------------------------------------------------------------
# batch_size property resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchSizeResolution:
    """Tests for SourceYamlConfig.batch_size property resolution order."""

    def test_prefers_pagination_id_batch_size(self) -> None:
        """Canonical pagination.id_batch_size takes highest priority."""
        cfg = _make_source_config(id_batch_size=500)
        assert cfg.batch_size == 500

    def test_falls_back_to_default_batch_size(self) -> None:
        """Falls back to DEFAULT_BATCH_SIZE when pagination.id_batch_size is absent."""
        cfg = _make_source_config()
        assert cfg.batch_size == 100

    def test_default_batch_size_is_100(self) -> None:
        """Default ID batch size is 100."""
        cfg = _make_source_config()
        assert cfg.batch_size == 100


# ---------------------------------------------------------------------------
# page_size property resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPageSizeResolution:
    """Tests for SourceYamlConfig.page_size property resolution order."""

    def test_prefers_pagination_page_size(self) -> None:
        """Canonical pagination.page_size takes highest priority."""
        cfg = _make_source_config(page_size=1000)
        assert cfg.page_size == 1000

    def test_returns_none_when_not_set(self) -> None:
        """Returns None when neither pagination nor provider page_size set."""
        cfg = _make_source_config()
        assert cfg.page_size is None


# ---------------------------------------------------------------------------
# max_url_length property resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMaxUrlLengthResolution:
    """Tests for SourceYamlConfig.max_url_length property resolution order."""

    def test_prefers_pagination_max_url_length(self) -> None:
        """Canonical pagination.max_url_length takes highest priority."""
        cfg = _make_source_config(max_url_length=8000)
        assert cfg.max_url_length == 8000

    def test_url_length_resolution__none_when_not_set__f388103b(self) -> None:
        """Returns None when neither set."""
        cfg = _make_source_config()
        assert cfg.max_url_length is None


# ---------------------------------------------------------------------------
# Convenience properties
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSourceYamlConfigConvenienceProperties:
    """Tests for convenience properties on SourceYamlConfig."""

    def test_provider_property(self) -> None:
        """provider property returns provider name."""
        cfg = _make_source_config()
        assert cfg.provider == "test_provider"

    def test_base_url_property(self) -> None:
        """base_url returns the configured URL."""
        cfg = _make_source_config()
        assert cfg.base_url == "https://api.example.com"

    def test_timeout_sec_default(self) -> None:
        """timeout_sec returns client default."""
        cfg = _make_source_config()
        assert cfg.timeout_sec > 0

    def test_max_retries_default(self) -> None:
        """max_retries returns client default."""
        cfg = _make_source_config()
        assert cfg.max_retries >= 0

    def test_retry_base_delay_default(self) -> None:
        """retry_base_delay returns client default."""
        cfg = _make_source_config()
        assert cfg.retry_base_delay >= 0

    def test_retry_max_delay_default(self) -> None:
        """retry_max_delay returns client default."""
        cfg = _make_source_config()
        assert cfg.retry_max_delay >= 0

    def test_pagination_property(self) -> None:
        """pagination returns PaginationConfig instance."""
        cfg = _make_source_config(page_size=500, strategy="cursor")
        pag = cfg.pagination
        assert isinstance(pag, PaginationConfig)
        assert pag.page_size == 500
        assert pag.strategy == "cursor"

    def test_rate_limit_property(self) -> None:
        """rate_limit returns the RateLimitYamlConfig."""
        cfg = _make_source_config()
        assert cfg.rate_limit is not None

    def test_circuit_breaker_property(self) -> None:
        """circuit_breaker returns CircuitBreakerYamlConfig."""
        cfg = _make_source_config()
        assert cfg.circuit_breaker is not None

    def test_provider_config_property(self) -> None:
        """provider_config returns ProviderConfigYaml."""
        cfg = _make_source_config()
        assert isinstance(cfg.provider_config, ProviderConfigYaml)


# ---------------------------------------------------------------------------
# to_adapter_config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestToAdapterConfig:
    """Tests for SourceYamlConfig.to_adapter_config()."""

    def test_default_page_size_used_when_not_configured(self) -> None:
        """Uses default_page_size when config has no page_size."""
        cfg = _make_source_config()
        adapter = cfg.to_adapter_config(default_page_size=999)
        assert adapter.page_size == 999

    def test_config_page_size_overrides_default(self) -> None:
        """Configured page_size overrides default_page_size."""
        cfg = _make_source_config(page_size=1000)
        adapter = cfg.to_adapter_config(default_page_size=500)
        assert adapter.page_size == 1000

    def test_page_size_override_takes_highest_priority(self) -> None:
        """page_size_override takes priority over both config and default."""
        cfg = _make_source_config(page_size=1000)
        adapter = cfg.to_adapter_config(default_page_size=500, page_size_override=250)
        assert adapter.page_size == 250

    def test_batch_size_propagated(self) -> None:
        """batch_size from config is propagated to AdapterConfig."""
        cfg = _make_source_config(id_batch_size=300)
        adapter = cfg.to_adapter_config()
        assert adapter.batch_size == 300

    def test_returns_domain_adapter_config(self) -> None:
        """Returns a DomainAdapterConfig instance."""
        from bioetl.domain.resilience import AdapterConfig

        cfg = _make_source_config()
        adapter = cfg.to_adapter_config()
        assert isinstance(adapter, AdapterConfig)


# ---------------------------------------------------------------------------
# Retired legacy aliases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRetiredLegacyAliases:
    """Tests for retired provider-level pagination aliases."""

    @pytest.mark.parametrize(
        ("payload", "expected_fragment"),
        [
            (
                {
                    "source": {
                        "provider_config": {
                            "provider": "test",
                            "batch_size": 250,
                        }
                    }
                },
                "batch_size",
            ),
            (
                {
                    "source": {
                        "provider_config": {
                            "provider": "test",
                            "page_size": 500,
                        }
                    }
                },
                "page_size",
            ),
            (
                {
                    "source": {
                        "provider_config": {
                            "provider": "test",
                            "max_url_length": 5000,
                        }
                    }
                },
                "max_url_length",
            ),
            (
                {
                    "source": {
                        "provider_config": {
                            "provider": "test",
                            "cursor_pagination": True,
                        }
                    }
                },
                "cursor_pagination",
            ),
        ],
    )
    def test_retired_aliases_are_rejected(
        self, payload: dict[str, object], expected_fragment: str
    ) -> None:
        with pytest.raises(
            ValueError, match="Retired source provider pagination aliases"
        ) as exc:
            SourceYamlConfig.model_validate(payload)

        assert expected_fragment in str(exc.value)


@pytest.mark.unit
def test_api_key_env_rejects_untyped_or_malformed_secret_source() -> None:
    """Credential source identity is constrained without reading a secret value."""
    with pytest.raises(ValueError, match="api_key_env"):
        SourceYamlConfig.model_validate(
            {
                "source": {
                    "provider_config": {
                        "provider": "test",
                        "api_key_env": "API_KEY",
                    }
                }
            }
        )
