# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture tests for source configuration usage.

These tests verify that source configurations from configs/providers/*.yaml
are used instead of hardcoded values.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.architecture


class TestSourceConfigFilesExist:
    """Verify that source configuration files exist for all providers."""

    @pytest.fixture
    def provider_configs_dir(self) -> Path:
        """Get path to provider configs directory."""
        return Path("configs/providers")

    @pytest.mark.parametrize(
        "provider",
        ["chembl", "pubchem", "uniprot", "pubmed"],
    )
    def test_config_files_exist__source_config_exists__d188f2b9(
        self, provider_configs_dir: Path, provider: str
    ) -> None:
        """Each provider MUST have a source configuration file."""
        config_file = provider_configs_dir / f"{provider}.yaml"
        assert config_file.exists(), (
            f"Source config missing: {config_file}. "
            f"Create configs/providers/{provider}.yaml with source/rate_limit/circuit_breaker settings."
        )

    @pytest.mark.parametrize(
        "provider",
        ["chembl", "pubchem", "uniprot", "pubmed"],
    )
    def test_source_config_has_required_sections(
        self, provider_configs_dir: Path, provider: str
    ) -> None:
        """Source config MUST have rate_limit and circuit_breaker sections."""
        config_file = provider_configs_dir / f"{provider}.yaml"
        if not config_file.exists():
            pytest.skip(f"Config file {config_file} does not exist")

        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert "source" in config, f"{provider}: Missing 'source' section"
        source = config["source"]

        assert "rate_limit" in source, f"{provider}: Missing 'rate_limit' section"
        rate_limit = source["rate_limit"]
        assert "requests_per_second" in rate_limit, (
            f"{provider}: Missing 'rate_limit.requests_per_second'"
        )
        assert "burst" in rate_limit, f"{provider}: Missing 'rate_limit.burst'"

        assert "circuit_breaker" in source, (
            f"{provider}: Missing 'circuit_breaker' section"
        )
        cb = source["circuit_breaker"]
        assert "failure_threshold" in cb, (
            f"{provider}: Missing 'circuit_breaker.failure_threshold'"
        )
        assert "recovery_timeout" in cb, (
            f"{provider}: Missing 'circuit_breaker.recovery_timeout'"
        )


class TestSourceConfigLoading:
    """Verify that source configs are loaded and used."""

    def test_load_source_config_returns_valid_model(self) -> None:
        """load_source_config() should return validated SourceYamlConfig."""
        from bioetl.infrastructure.config.source_config_loader import load_source_config

        config = load_source_config("chembl")

        assert config.rate_limit.requests_per_second > 0
        assert config.rate_limit.burst > 0
        assert config.circuit_breaker.failure_threshold > 0
        assert config.circuit_breaker.recovery_timeout >= 60

    def test_load_source_config_raises_for_unknown_provider(self) -> None:
        """load_source_config() should raise ValueError for unknown provider."""
        from bioetl.infrastructure.config.source_config_loader import load_source_config

        with pytest.raises(ValueError, match="Source configuration file not found"):
            load_source_config("nonexistent_provider")

    @pytest.mark.parametrize(
        "provider",
        ["chembl", "pubchem", "uniprot", "pubmed"],
    )
    def test_source_config_rate_limit_matches_yaml(self, provider: str) -> None:
        """Rate limit from SourceYamlConfig should match YAML file."""
        from bioetl.infrastructure.config.source_config_loader import load_source_config

        config = load_source_config(provider)

        # Load raw YAML for comparison
        with open(f"configs/providers/{provider}.yaml", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        yaml_rate = raw["source"]["rate_limit"]["requests_per_second"]
        yaml_burst = raw["source"]["rate_limit"]["burst"]

        assert config.rate_limit.requests_per_second == yaml_rate, (
            f"{provider}: rate_limit.requests_per_second mismatch"
        )
        assert config.rate_limit.burst == yaml_burst, (
            f"{provider}: rate_limit.burst mismatch"
        )


class TestNoHardcodedRateLimits:
    """Verify that rate limits are not hardcoded in critical files."""

    def test_http_client_factory_uses_source_config(self) -> None:
        """HttpClientFactory should use load_source_config for rate limits."""
        import inspect

        from bioetl.composition.factories.datasource.http_client import (
            HttpClientFactory,
        )

        source = inspect.getsource(HttpClientFactory)

        # Should import and use load_source_config
        assert "load_source_config" in source, (
            "HttpClientFactory should use load_source_config"
        )

    def test_registration_uses_source_config(self) -> None:
        """registration.py (or its _config_helpers) should use load_source_config for rate limits."""
        import inspect

        from bioetl.composition.providers import _config_helpers, registration

        reg_source = inspect.getsource(registration)
        helpers_source = inspect.getsource(_config_helpers)
        combined = reg_source + helpers_source

        # Should import load_source_config (in _config_helpers after split)
        assert "load_source_config" in combined, (
            "registration providers should use load_source_config"
        )

        # Should have helper functions for getting config
        assert "_get_rate_limit_from_config" in combined
        assert "_get_circuit_breaker_from_config" in combined


class TestSourceConfigSchema:
    """Test SourceYamlConfig schema validation."""

    def test_chembl_config_has_page_size(self) -> None:
        """ChEMBL config should have page_size for API pagination."""
        from bioetl.infrastructure.config.source_config_loader import load_source_config

        config = load_source_config("chembl")

        # ChEMBL should have page_size configured
        assert config.page_size is not None, (
            "ChEMBL config should have page_size for API pagination"
        )
        assert config.page_size >= 100, "ChEMBL page_size should be at least 100"

    def test_chembl_config_disables_env_proxy_inheritance(self) -> None:
        """ChEMBL should not silently inherit shell proxy settings."""
        from bioetl.infrastructure.config.source_config_loader import load_source_config

        config = load_source_config("chembl")

        assert config.trust_env is False

    def test_source_config_batch_size_property(self) -> None:
        """batch_size property should prefer canonical pagination.id_batch_size."""
        from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

        config = SourceYamlConfig.model_validate(
            {
                "source": {
                    "provider_config": {
                        "provider": "test",
                        "pagination": {"id_batch_size": 50},
                    },
                }
            }
        )

        # pagination.id_batch_size takes precedence
        assert config.batch_size == 50

    def test_source_config_falls_back_to_default_batch_size(self) -> None:
        """batch_size should fall back to DEFAULT_BATCH_SIZE if not configured."""
        from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

        config = SourceYamlConfig.model_validate(
            {
                "source": {
                    "provider_config": {
                        "provider": "test",
                    },
                }
            }
        )

        assert config.batch_size == 100


class TestConfigValuesNotHardcoded:
    """Verify config values match YAML, proving they're not hardcoded."""

    def test_chembl_rate_limit_from_config(self) -> None:
        """ChEMBL rate limit should match configs/providers/chembl.yaml."""
        from bioetl.composition.providers._config_helpers import (
            _get_rate_limit_from_config,
        )

        rate_limit = _get_rate_limit_from_config("chembl")

        # Load expected values from YAML
        with open("configs/providers/chembl.yaml", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        expected_rate = raw["source"]["rate_limit"]["requests_per_second"]
        expected_capacity = raw["source"]["rate_limit"]["burst"]

        assert rate_limit.rate == expected_rate, (
            f"ChEMBL rate mismatch: got {rate_limit.rate}, expected {expected_rate}"
        )
        assert rate_limit.capacity == expected_capacity, (
            f"ChEMBL capacity mismatch: got {rate_limit.capacity}, expected {expected_capacity}"
        )

    def test_chembl_circuit_breaker_from_config(self) -> None:
        """ChEMBL circuit breaker should match configs/providers/chembl.yaml."""
        from bioetl.composition.providers._config_helpers import (
            _get_circuit_breaker_from_config,
        )

        cb_config = _get_circuit_breaker_from_config("chembl")

        # Load expected values from YAML
        with open("configs/providers/chembl.yaml", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        expected_threshold = raw["source"]["circuit_breaker"]["failure_threshold"]
        expected_timeout = raw["source"]["circuit_breaker"]["recovery_timeout"]

        assert cb_config.failure_threshold == expected_threshold
        assert cb_config.recovery_timeout == expected_timeout
