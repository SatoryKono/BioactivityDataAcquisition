"""Tests for base configuration schemas.

Tests the base classes in base_schemas.py that provide shared
configuration components to eliminate duplication across schema files.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.infrastructure.schemas.base_schemas import (
    BaseApiConfig,
    BaseCircuitBreakerConfig,
    HttpClientConfig,
    BaseCsvExportConfig,
    BaseDQConfig,
    BaseDQThresholds,
    BaseFilterColumnSchema,
    BaseGoldColumnFilterConfig,
    BaseGoldFiltersConfig,
    BaseGoldListContainsFilterConfig,
    BaseGoldListLengthFilterConfig,
    BaseGoldRangeFilterConfig,
    BaseInputFilterConfig,
    BaseMaintenanceConfig,
    BaseRateLimitConfig,
)


@pytest.mark.unit
class TestBaseDQThresholds:
    """Test BaseDQThresholds configuration."""

    def test_default_values(self) -> None:
        """Test default threshold values."""
        config = BaseDQThresholds()
        assert config.soft_fail_threshold == pytest.approx(0.05)
        assert config.hard_fail_threshold == pytest.approx(0.20)

    def test_custom_values(self) -> None:
        """Test custom threshold values."""
        config = BaseDQThresholds(soft_fail_threshold=0.10, hard_fail_threshold=0.30)
        assert config.soft_fail_threshold == pytest.approx(0.10)
        assert config.hard_fail_threshold == pytest.approx(0.30)

    def test_soft_must_be_less_than_hard(self) -> None:
        """Test validation that soft < hard."""
        with pytest.raises(ValidationError):
            BaseDQThresholds(soft_fail_threshold=0.25, hard_fail_threshold=0.20)

    def test_thresholds_equal_fails(self) -> None:
        """Test that equal thresholds fail validation."""
        with pytest.raises(ValidationError):
            BaseDQThresholds(soft_fail_threshold=0.20, hard_fail_threshold=0.20)

    def test_threshold_range_validation_min(self) -> None:
        """Test minimum threshold value is 0.0."""
        with pytest.raises(ValidationError):
            BaseDQThresholds(soft_fail_threshold=-0.01)

    def test_threshold_range_validation_max(self) -> None:
        """Test maximum threshold value is 1.0."""
        with pytest.raises(ValidationError):
            BaseDQThresholds(hard_fail_threshold=1.01)


@pytest.mark.unit
class TestBaseDQConfig:
    """Test BaseDQConfig configuration."""

    def test_inherits_thresholds(self) -> None:
        """Test that BaseDQConfig inherits from BaseDQThresholds."""
        config = BaseDQConfig()
        assert config.soft_fail_threshold == pytest.approx(0.05)
        assert config.hard_fail_threshold == pytest.approx(0.20)

    def test_strict_validation_default(self) -> None:
        """Test strict_validation defaults to False."""
        config = BaseDQConfig()
        assert config.strict_validation is False

    def test_strict_validation_enabled(self) -> None:
        """Test strict_validation can be enabled."""
        config = BaseDQConfig(strict_validation=True)
        assert config.strict_validation is True

    def test_to_domain_conversion(self) -> None:
        """Test conversion to domain object."""
        config = BaseDQConfig(
            soft_fail_threshold=0.08,
            hard_fail_threshold=0.25,
            strict_validation=True,
        )
        domain = config.to_domain()
        assert domain.soft_fail_threshold == pytest.approx(0.08)
        assert domain.hard_fail_threshold == pytest.approx(0.25)
        assert domain.strict_validation is True


@pytest.mark.unit
class TestBaseCircuitBreakerConfig:
    """Test BaseCircuitBreakerConfig configuration."""

    def test_default_values(self) -> None:
        """Test default circuit breaker values."""
        config = BaseCircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 300

    def test_custom_values(self) -> None:
        """Test custom circuit breaker values."""
        config = BaseCircuitBreakerConfig(failure_threshold=10, recovery_timeout=600)
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 600

    def test_failure_threshold_minimum(self) -> None:
        """Test failure_threshold has minimum of 1."""
        with pytest.raises(ValidationError):
            BaseCircuitBreakerConfig(failure_threshold=0)

    def test_failure_threshold_maximum(self) -> None:
        """Test failure_threshold has maximum of 20."""
        with pytest.raises(ValidationError):
            BaseCircuitBreakerConfig(failure_threshold=21)

    def test_recovery_timeout_minimum(self) -> None:
        """Test recovery_timeout has minimum of 60."""
        with pytest.raises(ValidationError):
            BaseCircuitBreakerConfig(recovery_timeout=59)

    def test_recovery_timeout_maximum(self) -> None:
        """Test recovery_timeout has maximum of 3600."""
        with pytest.raises(ValidationError):
            BaseCircuitBreakerConfig(recovery_timeout=3601)

    def test_to_domain_conversion(self) -> None:
        """Test conversion to domain object."""
        config = BaseCircuitBreakerConfig(failure_threshold=7, recovery_timeout=450)
        domain = config.to_domain()
        assert domain.failure_threshold == 7
        assert domain.recovery_timeout == 450


@pytest.mark.unit
class TestBaseRateLimitConfig:
    """Test BaseRateLimitConfig configuration."""

    def test_default_values(self) -> None:
        """Test default rate limit values."""
        config = BaseRateLimitConfig()
        assert config.requests_per_second == pytest.approx(5.0)
        assert config.burst == 10

    def test_custom_values(self) -> None:
        """Test custom rate limit values."""
        config = BaseRateLimitConfig(requests_per_second=10.0, burst=20)
        assert config.requests_per_second == pytest.approx(10.0)
        assert config.burst == 20

    def test_rps_minimum(self) -> None:
        """Test requests_per_second has minimum of 0.1."""
        with pytest.raises(ValidationError):
            BaseRateLimitConfig(requests_per_second=0.05)

    def test_rps_maximum(self) -> None:
        """Test requests_per_second has maximum of 100.0."""
        with pytest.raises(ValidationError):
            BaseRateLimitConfig(requests_per_second=101.0)

    def test_burst_minimum(self) -> None:
        """Test burst has minimum of 1."""
        with pytest.raises(ValidationError):
            BaseRateLimitConfig(burst=0)

    def test_burst_maximum(self) -> None:
        """Test burst has maximum of 200."""
        with pytest.raises(ValidationError):
            BaseRateLimitConfig(burst=201)


@pytest.mark.unit
class TestHttpClientConfig:
    """Test HttpClientConfig configuration."""

    def test_default_values(self) -> None:
        """Test default client config values."""
        config = HttpClientConfig()
        assert config.timeout_sec == pytest.approx(30.0)
        assert config.max_retries == 3

    def test_custom_values(self) -> None:
        """Test custom client config values."""
        config = HttpClientConfig(timeout_sec=60.0, max_retries=5)
        assert config.timeout_sec == pytest.approx(60.0)
        assert config.max_retries == 5

    def test_timeout_minimum(self) -> None:
        """Test timeout_sec has minimum of 1.0."""
        with pytest.raises(ValidationError):
            HttpClientConfig(timeout_sec=0.5)

    def test_timeout_maximum(self) -> None:
        """Test timeout_sec has maximum of 300.0."""
        with pytest.raises(ValidationError):
            HttpClientConfig(timeout_sec=301.0)

    def test_max_retries_minimum(self) -> None:
        """Test max_retries has minimum of 0."""
        config = HttpClientConfig(max_retries=0)
        assert config.max_retries == 0

    def test_max_retries_maximum(self) -> None:
        """Test max_retries has maximum of 10."""
        with pytest.raises(ValidationError):
            HttpClientConfig(max_retries=11)


@pytest.mark.unit
class TestBaseApiConfig:
    """Test BaseApiConfig configuration."""

    def test_default_values(self) -> None:
        """Test default API config values."""
        config = BaseApiConfig()
        assert config.base_url is None
        assert config.rate_limit is None
        assert config.timeout is None

    def test_custom_values(self) -> None:
        """Test custom API config values."""
        config = BaseApiConfig(
            base_url="https://api.example.com",
            rate_limit=10.0,
            timeout=60,
        )
        assert config.base_url == "https://api.example.com"
        assert config.rate_limit == pytest.approx(10.0)
        assert config.timeout == 60

    def test_to_domain_with_defaults(self) -> None:
        """Test conversion to domain uses defaults when values not specified."""
        config = BaseApiConfig()
        domain = config.to_domain()
        assert domain.timeout == 30
        assert domain.rate_limit.requests_per_second == pytest.approx(5.0)

    def test_to_domain_with_custom_values(self) -> None:
        """Test conversion to domain with custom values."""
        config = BaseApiConfig(rate_limit=10.0, timeout=60)
        domain = config.to_domain()
        assert domain.timeout == 60
        assert domain.rate_limit.requests_per_second == pytest.approx(10.0)


@pytest.mark.unit
class TestBaseGoldColumnFilterTypedValues:
    """Typed literals in filter config must survive schema-to-domain conversion."""

    def test_typed_scalar_values_are_preserved(self) -> None:
        config = BaseGoldFiltersConfig(
            columns={
                "potential_duplicate": BaseGoldColumnFilterConfig(values=[0]),
                "reviewed": BaseGoldColumnFilterConfig(values=[True]),
            }
        )

        domain = config.to_domain()
        by_column = {
            column_filter.column: column_filter
            for column_filter in domain.column_filters
        }

        assert by_column["potential_duplicate"].values == frozenset([0])
        assert by_column["reviewed"].values == frozenset([True])


@pytest.mark.unit
class TestBaseCsvExportConfig:
    """Test BaseCsvExportConfig configuration."""

    def test_default_values(self) -> None:
        """Test default CSV export values."""
        config = BaseCsvExportConfig()
        assert config.enabled is False
        assert config.path is None
        assert config.delimiter == ","
        assert config.header is True
        assert config.encoding == "utf-8"

    def test_custom_values(self) -> None:
        """Test custom CSV export values."""
        config = BaseCsvExportConfig(
            enabled=True,
            path="/output/data.csv",
            delimiter=";",
            header=False,
            encoding="latin-1",
        )
        assert config.enabled is True
        assert config.path == "/output/data.csv"
        assert config.delimiter == ";"
        assert config.header is False
        assert config.encoding == "latin-1"


@pytest.mark.unit
class TestBaseInputFilterConfig:
    """Test BaseInputFilterConfig configuration."""

    def test_default_values(self) -> None:
        """Test default input filter values.

        Note: column_name and filter_field are None by default because
        there is no universally applicable default value across providers.
        """
        config = BaseInputFilterConfig()
        assert config.enabled is False
        assert config.source_path is None
        assert config.column_name is None
        assert config.filter_field is None
        assert config.columns is None
        assert config.batch_size == 100
        assert config.fallback_column is None

    def test_single_column_mode(self) -> None:
        """Test single-column filtering mode."""
        config = BaseInputFilterConfig(
            enabled=True,
            source_path="/data/ids.csv",
            column_name="chembl_id",
            filter_field="molecule_id",
            batch_size=50,
        )
        assert config.enabled is True
        assert config.source_path == "/data/ids.csv"
        assert config.column_name == "chembl_id"
        assert config.filter_field == "molecule_id"
        assert config.batch_size == 50

    def test_multi_column_mode(self) -> None:
        """Test multi-column filtering mode."""
        config = BaseInputFilterConfig(
            enabled=True,
            source_path="/data/ids.csv",
            columns=[
                BaseFilterColumnSchema(column_name="id1", filter_field="field1"),
                BaseFilterColumnSchema(column_name="id2", filter_field="field2"),
            ],
            batch_size=100,
        )
        assert config.enabled is True
        assert len(config.columns) == 2

    def test_enabled_requires_column_config(self) -> None:
        """Test that enabled filter requires column configuration."""
        with pytest.raises(ValidationError):
            BaseInputFilterConfig(enabled=True, source_path="/data/ids.csv")

    def test_single_column_requires_both_fields(self) -> None:
        """Test that single-column mode requires both column_name and filter_field."""
        with pytest.raises(ValidationError):
            BaseInputFilterConfig(
                enabled=True,
                source_path="/data/ids.csv",
                column_name="id",
            )

    def test_batch_size_range(self) -> None:
        """Test batch_size range validation."""
        with pytest.raises(ValidationError):
            BaseInputFilterConfig(batch_size=0)
        with pytest.raises(ValidationError):
            BaseInputFilterConfig(batch_size=1001)

    def test_to_domain_disabled(self) -> None:
        """Test to_domain for disabled filter."""
        config = BaseInputFilterConfig()
        domain = config.to_domain()
        assert domain.enabled is False
        assert domain.column_name is None
        assert domain.filter_field is None

    def test_to_domain_single_column(self) -> None:
        """Test to_domain for single-column mode."""
        config = BaseInputFilterConfig(
            enabled=True,
            source_path="/data/ids.csv",
            column_name="chembl_id",
            filter_field="molecule_id",
        )
        domain = config.to_domain()
        assert domain.enabled is True
        assert domain.column_name == "chembl_id"
        assert domain.filter_field == "molecule_id"


@pytest.mark.unit
class TestBaseMaintenanceConfig:
    """Test BaseMaintenanceConfig configuration."""

    def test_default_values(self) -> None:
        """Test default maintenance config values."""
        config = BaseMaintenanceConfig()
        assert config.auto_vacuum is False
        assert config.vacuum_retention_days == 7

    def test_custom_values(self) -> None:
        """Test custom maintenance config values."""
        config = BaseMaintenanceConfig(auto_vacuum=True, vacuum_retention_days=30)
        assert config.auto_vacuum is True
        assert config.vacuum_retention_days == 30

    def test_retention_days_range(self) -> None:
        """Test vacuum_retention_days range validation."""
        with pytest.raises(ValidationError):
            BaseMaintenanceConfig(vacuum_retention_days=0)
        with pytest.raises(ValidationError):
            BaseMaintenanceConfig(vacuum_retention_days=366)


@pytest.mark.unit
class TestBaseGoldColumnFilterConfig:
    """Test BaseGoldColumnFilterConfig configuration."""

    def test_default_in_operator(self) -> None:
        """Test default operator is 'in'."""
        config = BaseGoldColumnFilterConfig(values=["value1", "value2"])
        assert config.operator == "in"

    def test_in_operator_requires_values(self) -> None:
        """Test 'in' operator requires values."""
        with pytest.raises(ValidationError):
            BaseGoldColumnFilterConfig(operator="in")

    def test_not_in_operator_requires_values(self) -> None:
        """Test 'not_in' operator requires values."""
        with pytest.raises(ValidationError):
            BaseGoldColumnFilterConfig(operator="not_in")

    def test_is_null_operator_no_values(self) -> None:
        """Test 'is_null' operator must not have values."""
        config = BaseGoldColumnFilterConfig(operator="is_null")
        assert config.values is None
        with pytest.raises(ValidationError):
            BaseGoldColumnFilterConfig(operator="is_null", values=["x"])

    def test_is_not_null_operator(self) -> None:
        """Test 'is_not_null' operator."""
        config = BaseGoldColumnFilterConfig(operator="is_not_null")
        assert config.values is None

    def test_all_operators__test_base_gold_column_filter_config_infrastructure_schemas_test_base_schemas_453(
        self,
    ) -> None:
        """Test all valid operators."""
        operators = [
            "in",
            "not_in",
            "is_null",
            "is_not_null",
            "is_empty",
            "is_not_empty",
        ]
        for op in operators:
            if op in ("in", "not_in"):
                config = BaseGoldColumnFilterConfig(operator=op, values=["x"])
            else:
                config = BaseGoldColumnFilterConfig(operator=op)
            assert config.operator == op


@pytest.mark.unit
class TestBaseGoldFiltersConfig:
    """Test BaseGoldFiltersConfig configuration."""

    def test_default_empty_config(self) -> None:
        """Test default empty filter config."""
        config = BaseGoldFiltersConfig()
        assert config.columns == {}
        assert config.ranges == {}
        assert config.list_lengths == {}
        assert config.list_contains == {}
        assert config.required_fields == []
        assert config.exclude_if_present == []

    def test_legacy_column_format(self) -> None:
        """Test legacy list format for columns."""
        config = BaseGoldFiltersConfig(
            columns={"status": ["active", "inactive"]},
        )
        assert config.columns["status"] == ["active", "inactive"]

    def test_new_column_format(self) -> None:
        """Test new operator format for columns."""
        config = BaseGoldFiltersConfig(
            columns={
                "status": BaseGoldColumnFilterConfig(operator="in", values=["active"]),
            },
        )
        assert config.columns["status"].operator == "in"

    def test_range_filters(self) -> None:
        """Test range filter configuration."""
        config = BaseGoldFiltersConfig(
            ranges={
                "score": BaseGoldRangeFilterConfig(min=0.0, max=100.0),
            },
        )
        assert config.ranges["score"].min == pytest.approx(0.0)
        assert config.ranges["score"].max == pytest.approx(100.0)

    def test_list_length_filters(self) -> None:
        """Test list length filter configuration."""
        config = BaseGoldFiltersConfig(
            list_lengths={
                "tags": BaseGoldListLengthFilterConfig(min=1, max=10),
            },
        )
        assert config.list_lengths["tags"].min == 1
        assert config.list_lengths["tags"].max == 10

    def test_list_contains_filters(self) -> None:
        """Test list contains filter configuration."""
        config = BaseGoldFiltersConfig(
            list_contains={
                "tags": BaseGoldListContainsFilterConfig(
                    values=["required"], mode="any"
                ),
            },
        )
        assert config.list_contains["tags"].values == ["required"]
        assert config.list_contains["tags"].mode == "any"

    def test_to_domain_conversion(self) -> None:
        """Test conversion to domain object."""
        config = BaseGoldFiltersConfig(
            columns={"status": ["active"]},
            required_fields=["id", "name"],
            exclude_if_present=["deprecated"],
        )
        domain = config.to_domain()
        assert len(domain.column_filters) == 1
        assert domain.required_fields == ("id", "name")
        assert domain.exclude_if_present == ("deprecated",)


@pytest.mark.unit
class TestInheritanceChain:
    """Test that inheritance chain works correctly."""

    def test_source_config_inherits_base(self) -> None:
        """Test that source_config classes inherit from base classes."""
        from bioetl.infrastructure.schemas.source_config import (
            ClientYamlConfig,
            RateLimitYamlConfig,
            SourceCircuitBreakerYamlConfig,
        )

        assert issubclass(RateLimitYamlConfig, BaseRateLimitConfig)
        assert issubclass(SourceCircuitBreakerYamlConfig, BaseCircuitBreakerConfig)
        assert issubclass(ClientYamlConfig, HttpClientConfig)

    def test_filter_config_inherits_base(self) -> None:
        """Test that filter_config classes inherit from base classes."""
        from bioetl.infrastructure.schemas.filter_config import (
            GoldFiltersFileConfig,
            InputFilterFileConfig,
        )

        assert issubclass(InputFilterFileConfig, BaseInputFilterConfig)
        assert issubclass(GoldFiltersFileConfig, BaseGoldFiltersConfig)


@pytest.mark.unit
class TestConfigDictSettings:
    """Test that ConfigDict settings are properly applied."""

    def test_extra_ignore_dq_thresholds(self) -> None:
        """Test that extra fields are ignored in BaseDQThresholds."""
        config = BaseDQThresholds(
            soft_fail_threshold=0.05,
            hard_fail_threshold=0.20,
            unknown_field="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(config, "unknown_field")

    def test_extra_ignore_circuit_breaker(self) -> None:
        """Test that extra fields are ignored in BaseCircuitBreakerConfig."""
        config = BaseCircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=300,
            unknown_field="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(config, "unknown_field")
