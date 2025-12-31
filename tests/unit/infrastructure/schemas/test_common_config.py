"""Tests for common configuration schemas.

Tests Pydantic models used for parsing pipeline YAML configurations.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.infrastructure.schemas.common_config import (
    ApiConfig,
    CircuitBreakerConfig,
    CsvExportConfig,
    DQConfig,
    InputFilterConfig,
    MaintenanceConfig,
)


@pytest.mark.unit
class TestDQConfig:
    """Test Data Quality configuration schema."""

    def test_default_values(self) -> None:
        """Test default threshold values."""
        config = DQConfig()
        assert config.soft_fail_threshold == 0.05
        assert config.hard_fail_threshold == 0.20
        assert config.strict_validation is False

    def test_custom_thresholds(self) -> None:
        """Test custom threshold values."""
        config = DQConfig(
            soft_fail_threshold=0.10,
            hard_fail_threshold=0.30,
            strict_validation=True,
        )
        assert config.soft_fail_threshold == 0.10
        assert config.hard_fail_threshold == 0.30
        assert config.strict_validation is True

    def test_invalid_threshold_order_raises(self) -> None:
        """Test that soft > hard threshold raises validation error."""
        with pytest.raises(ValidationError):
            DQConfig(
                soft_fail_threshold=0.30,
                hard_fail_threshold=0.10,
            )

    def test_to_domain_conversion(self) -> None:
        """Test conversion to domain DQConfig."""
        config = DQConfig(
            soft_fail_threshold=0.08,
            hard_fail_threshold=0.25,
            strict_validation=True,
        )
        domain = config.to_domain()

        assert domain.soft_fail_threshold == 0.08
        assert domain.hard_fail_threshold == 0.25
        assert domain.strict_validation is True


@pytest.mark.unit
class TestCircuitBreakerConfig:
    """Test Circuit Breaker configuration schema."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 300

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=600,
        )
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 600

    def test_failure_threshold_minimum(self) -> None:
        """Test failure_threshold has minimum of 1."""
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(failure_threshold=0)

    def test_recovery_timeout_minimum(self) -> None:
        """Test recovery_timeout has minimum of 60."""
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(recovery_timeout=30)

    def test_to_domain_conversion(self) -> None:
        """Test conversion to domain CircuitBreakerConfig."""
        config = CircuitBreakerConfig(
            failure_threshold=8,
            recovery_timeout=450,
        )
        domain = config.to_domain()

        assert domain.failure_threshold == 8
        assert domain.recovery_timeout == 450


@pytest.mark.unit
class TestCsvExportConfig:
    """Test CSV export configuration schema."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = CsvExportConfig()
        assert config.enabled is False
        assert config.path is None
        assert config.delimiter == ","
        assert config.header is True
        assert config.encoding == "utf-8"

    def test_enabled_with_path(self) -> None:
        """Test enabled CSV export with path."""
        config = CsvExportConfig(
            enabled=True,
            path="/tmp/export.csv",
            delimiter=";",
            header=False,
            encoding="latin-1",
        )
        assert config.enabled is True
        assert config.path == "/tmp/export.csv"
        assert config.delimiter == ";"
        assert config.header is False
        assert config.encoding == "latin-1"


@pytest.mark.unit
class TestInputFilterConfig:
    """Test input filter configuration schema."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = InputFilterConfig()
        assert config.enabled is False
        assert config.source_path is None
        assert config.column_name == "id"
        assert config.filter_field == "molecule_chembl_id"
        assert config.batch_size == 100

    def test_enabled_with_path(self) -> None:
        """Test enabled filter with source path."""
        config = InputFilterConfig(
            enabled=True,
            source_path="/data/ids.csv",
            column_name="chembl_id",
            filter_field="molecule_chembl_id",
            batch_size=50,
        )
        assert config.enabled is True
        assert config.source_path == "/data/ids.csv"
        assert config.column_name == "chembl_id"
        assert config.batch_size == 50

    def test_batch_size_minimum(self) -> None:
        """Test batch_size has minimum of 1."""
        with pytest.raises(ValidationError):
            InputFilterConfig(batch_size=0)

    def test_batch_size_maximum(self) -> None:
        """Test batch_size has maximum of 1000."""
        with pytest.raises(ValidationError):
            InputFilterConfig(batch_size=1001)

    def test_to_domain_conversion_disabled(self) -> None:
        """Test conversion to domain when disabled."""
        config = InputFilterConfig(enabled=False)
        domain = config.to_domain()

        assert domain.enabled is False
        assert domain.column_name is None
        assert domain.filter_field is None

    def test_to_domain_conversion_enabled(self) -> None:
        """Test conversion to domain when enabled."""
        config = InputFilterConfig(
            enabled=True,
            source_path="/data/ids.csv",
            column_name="my_id",
            filter_field="target_field",
            batch_size=200,
        )
        domain = config.to_domain()

        assert domain.enabled is True
        assert domain.column_name == "my_id"
        assert domain.filter_field == "target_field"
        assert domain.batch_size == 200


@pytest.mark.unit
class TestMaintenanceConfig:
    """Test maintenance configuration schema."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = MaintenanceConfig()
        assert config.auto_vacuum is False
        assert config.vacuum_retention_days == 7

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = MaintenanceConfig(
            auto_vacuum=True,
            vacuum_retention_days=30,
        )
        assert config.auto_vacuum is True
        assert config.vacuum_retention_days == 30

    def test_retention_days_minimum(self) -> None:
        """Test vacuum_retention_days has minimum of 1."""
        with pytest.raises(ValidationError):
            MaintenanceConfig(vacuum_retention_days=0)

    def test_retention_days_maximum(self) -> None:
        """Test vacuum_retention_days has maximum of 365."""
        with pytest.raises(ValidationError):
            MaintenanceConfig(vacuum_retention_days=400)


@pytest.mark.unit
class TestApiConfig:
    """Test API configuration schema."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ApiConfig()
        assert config.base_url is None
        assert config.rate_limit is None
        assert config.timeout is None

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ApiConfig(
            base_url="https://api.example.com",
            rate_limit=10.0,
            timeout=60,
        )
        assert config.base_url == "https://api.example.com"
        assert config.rate_limit == 10.0
        assert config.timeout == 60

    def test_to_domain_conversion_defaults(self) -> None:
        """Test conversion to domain with defaults."""
        config = ApiConfig()
        domain = config.to_domain()

        assert domain.timeout == 30  # Default timeout
        assert domain.rate_limit.requests_per_second == 5.0  # Default rate limit

    def test_to_domain_conversion_custom(self) -> None:
        """Test conversion to domain with custom values."""
        config = ApiConfig(
            base_url="https://custom.api",
            rate_limit=15.0,
            timeout=90,
        )
        domain = config.to_domain()

        assert domain.base_url == "https://custom.api"
        assert domain.timeout == 90
        assert domain.rate_limit.requests_per_second == 15.0
