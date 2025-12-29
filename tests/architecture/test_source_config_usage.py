"""Architecture tests for source configuration usage.

These tests verify that source configurations from configs/sources/*.yaml
are used instead of hardcoded values.

Related to: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/XXX
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

if TYPE_CHECKING:
    pass


class TestSourceConfigFilesExist:
    """Verify that source configuration files exist for all providers."""

    @pytest.fixture
    def source_configs_dir(self) -> Path:
        """Get path to source configs directory."""
        return Path("configs/sources")

    @pytest.mark.parametrize(
        "provider",
        ["chembl", "pubchem", "uniprot", "pubmed"],
    )
    def test_source_config_exists(self, source_configs_dir: Path, provider: str) -> None:
        """Each provider MUST have a source configuration file."""
        config_file = source_configs_dir / f"{provider}.yaml"
        assert config_file.exists(), (
            f"Source config missing: {config_file}. "
            f"Create configs/sources/{provider}.yaml with rate_limit and circuit_breaker settings."
        )

    @pytest.mark.parametrize(
        "provider",
        ["chembl", "pubchem", "uniprot", "pubmed"],
    )
    def test_source_config_has_required_sections(
        self, source_configs_dir: Path, provider: str
    ) -> None:
        """Source config MUST have rate_limit and circuit_breaker sections."""
        config_file = source_configs_dir / f"{provider}.yaml"
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
        from bioetl.infrastructure.config import load_source_config

        config = load_source_config("chembl")

        assert config.rate_limit.requests_per_second > 0
        assert config.rate_limit.burst > 0
        assert config.circuit_breaker.failure_threshold > 0
        assert config.circuit_breaker.recovery_timeout >= 60

    def test_load_source_config_raises_for_unknown_provider(self) -> None:
        """load_source_config() should raise ValueError for unknown provider."""
        from bioetl.infrastructure.config import load_source_config

        with pytest.raises(ValueError, match="Source configuration file not found"):
            load_source_config("nonexistent_provider")

    @pytest.mark.parametrize(
        "provider",
        ["chembl", "pubchem", "uniprot", "pubmed"],
    )
    def test_source_config_rate_limit_matches_yaml(self, provider: str) -> None:
        """Rate limit from SourceYamlConfig should match YAML file."""
        from bioetl.infrastructure.config import load_source_config

        config = load_source_config(provider)

        # Load raw YAML for comparison
        with open(f"configs/sources/{provider}.yaml", encoding="utf-8") as f:
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

        from bioetl.composition.factories.http_client_factory import HttpClientFactory

        source = inspect.getsource(HttpClientFactory)

        # Should import and use load_source_config
        assert "load_source_config" in source, (
            "HttpClientFactory should use load_source_config"
        )

    def test_registration_uses_source_config(self) -> None:
        """registration.py should use load_source_config for rate limits."""
        import inspect

        from bioetl.composition.providers import registration

        source = inspect.getsource(registration)

        # Should import load_source_config
        assert "load_source_config" in source, (
            "registration.py should use load_source_config"
        )

        # Should have helper functions for getting config
        assert "_get_rate_limit_from_config" in source
        assert "_get_circuit_breaker_from_config" in source


class TestSourceConfigSchema:
    """Test SourceYamlConfig schema validation."""

    def test_chembl_config_has_page_size(self) -> None:
        """ChEMBL config should have page_size for API pagination."""
        from bioetl.infrastructure.config import load_source_config

        config = load_source_config("chembl")

        # ChEMBL should have page_size configured
        assert config.page_size is not None, (
            "ChEMBL config should have page_size for API pagination"
        )
        assert config.page_size >= 100, "ChEMBL page_size should be at least 100"

    def test_source_config_batch_size_property(self) -> None:
        """batch_size property should return provider_config.batch_size if set."""
        from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

        config = SourceYamlConfig.model_validate({
            "source": {
                "batch_size": 100,
                "provider_config": {
                    "provider": "test",
                    "batch_size": 50,
                },
            }
        })

        # provider_config.batch_size takes precedence
        assert config.batch_size == 50

    def test_source_config_falls_back_to_source_batch_size(self) -> None:
        """batch_size should fall back to source.batch_size if not in provider_config."""
        from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

        config = SourceYamlConfig.model_validate({
            "source": {
                "batch_size": 100,
                "provider_config": {
                    "provider": "test",
                },
            }
        })

        assert config.batch_size == 100


class TestConfigValuesNotHardcoded:
    """Verify config values match YAML, proving they're not hardcoded."""

    def test_chembl_rate_limit_from_config(self) -> None:
        """ChEMBL rate limit should match configs/sources/chembl.yaml."""
        from bioetl.composition.providers.registration import _get_rate_limit_from_config

        rate, capacity = _get_rate_limit_from_config("chembl")

        # Load expected values from YAML
        with open("configs/sources/chembl.yaml", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        expected_rate = raw["source"]["rate_limit"]["requests_per_second"]
        expected_capacity = raw["source"]["rate_limit"]["burst"]

        assert rate == expected_rate, (
            f"ChEMBL rate mismatch: got {rate}, expected {expected_rate}"
        )
        assert capacity == expected_capacity, (
            f"ChEMBL capacity mismatch: got {capacity}, expected {expected_capacity}"
        )

    def test_chembl_circuit_breaker_from_config(self) -> None:
        """ChEMBL circuit breaker should match configs/sources/chembl.yaml."""
        from bioetl.composition.providers.registration import (
            _get_circuit_breaker_from_config,
        )

        threshold, timeout = _get_circuit_breaker_from_config("chembl")

        # Load expected values from YAML
        with open("configs/sources/chembl.yaml", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        expected_threshold = raw["source"]["circuit_breaker"]["failure_threshold"]
        expected_timeout = raw["source"]["circuit_breaker"]["recovery_timeout"]

        assert threshold == expected_threshold
        assert timeout == expected_timeout
