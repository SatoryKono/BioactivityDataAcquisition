"""Unit tests for Grafana-related routing functionality."""

import pytest

from bioetl.interfaces.http.health_server_routing_mixin import (
    HealthServerRoutingMixin,
)


class TestGrafanaScopeHandling:
    """Test Grafana scope token handling in health server routing."""

    def test_is_all_scope_token_with_all(self):
        """Test that 'All' is recognized as Grafana All scope."""
        assert HealthServerRoutingMixin._is_all_scope_token("All")

    def test_is_all_scope_token_with_dollar_all(self):
        """Test that '$__all' is recognized as Grafana All scope."""
        assert HealthServerRoutingMixin._is_all_scope_token("$__all")

    def test_is_all_scope_token_with_double_underscore_all(self):
        """Test that '__all' is recognized as Grafana All scope."""
        assert HealthServerRoutingMixin._is_all_scope_token("__all")

    def test_is_all_scope_token_with_asterisk(self):
        """Test that '*' is recognized as Grafana All scope."""
        assert HealthServerRoutingMixin._is_all_scope_token("*")

    def test_is_all_scope_token_with_none(self):
        """Test that None is not recognized as Grafana All scope."""
        assert not HealthServerRoutingMixin._is_all_scope_token(None)

    def test_is_all_scope_token_with_specific_value(self):
        """Test that specific values are not recognized as Grafana All scope."""
        assert not HealthServerRoutingMixin._is_all_scope_token("chembl")
        assert not HealthServerRoutingMixin._is_all_scope_token("pubchem")

    def test_is_all_scope_token_with_whitespace(self):
        """Test that whitespace is handled correctly."""
        assert HealthServerRoutingMixin._is_all_scope_token(" All ")
        assert HealthServerRoutingMixin._is_all_scope_token(" $__all ")
        assert not HealthServerRoutingMixin._is_all_scope_token(" chembl ")


class TestQueryParameterParsing:
    """Test query parameter parsing for Grafana integration."""

    def test_read_csv_param_empty(self):
        """Test CSV param parsing with empty value."""
        result = HealthServerRoutingMixin._read_csv_param({}, "scope")
        assert result == ()

    def test_read_csv_param_single(self):
        """Test CSV param parsing with single value."""
        result = HealthServerRoutingMixin._read_csv_param({"scope": "chembl"}, "scope")
        assert result == ("chembl",)

    def test_read_csv_param_multiple(self):
        """Test CSV param parsing with multiple values."""
        result = HealthServerRoutingMixin._read_csv_param(
            {"scope": "chembl,pubchem,drugbank"}, "scope"
        )
        assert result == ("chembl", "pubchem", "drugbank")

    def test_read_csv_param_with_braces(self):
        """Test CSV param parsing with Grafana brace syntax."""
        result = HealthServerRoutingMixin._read_csv_param(
            {"scope": "{chembl,pubchem,drugbank}"}, "scope"
        )
        assert result == ("chembl", "pubchem", "drugbank")

    def test_read_csv_param_deduplicates(self):
        """Test CSV param parsing removes duplicates."""
        result = HealthServerRoutingMixin._read_csv_param(
            {"scope": "chembl,pubchem,chembl"}, "scope"
        )
        assert result == ("chembl", "pubchem")

    def test_read_csv_param_whitespace(self):
        """Test CSV param parsing handles whitespace."""
        result = HealthServerRoutingMixin._read_csv_param(
            {"scope": " chembl , pubchem , drugbank "}, "scope"
        )
        assert result == ("chembl", "pubchem", "drugbank")

    def test_read_scope_csv_param_with_all(self):
        """Test scope CSV param collapses Grafana All to empty."""
        result = HealthServerRoutingMixin._read_scope_csv_param(
            {"scope": "All"}, "scope"
        )
        assert result == ()

    def test_read_scope_csv_param_with_dollar_all(self):
        """Test scope CSV param collapses $__all to empty."""
        result = HealthServerRoutingMixin._read_scope_csv_param(
            {"scope": "$__all"}, "scope"
        )
        assert result == ()

    def test_read_scope_csv_param_mixed_with_all(self):
        """Test scope CSV param collapses mixed values with All to empty."""
        result = HealthServerRoutingMixin._read_scope_csv_param(
            {"scope": "chembl,All,pubchem"}, "scope"
        )
        assert result == ()

    def test_read_scope_csv_param_specific_values(self):
        """Test scope CSV param preserves specific values."""
        result = HealthServerRoutingMixin._read_scope_csv_param(
            {"scope": "chembl,pubchem,drugbank"}, "scope"
        )
        assert result == ("chembl", "pubchem", "drugbank")

    def test_read_optional_param_empty(self):
        """Test optional param parsing with missing value."""
        result = HealthServerRoutingMixin._read_optional_param({}, "missing")
        assert result is None

    def test_read_optional_param_present(self):
        """Test optional param parsing with value."""
        result = HealthServerRoutingMixin._read_optional_param(
            {"value": "test"}, "value"
        )
        assert result == "test"

    def test_read_optional_param_whitespace(self):
        """Test optional param parsing strips whitespace."""
        result = HealthServerRoutingMixin._read_optional_param(
            {"value": " test "}, "value"
        )
        assert result == "test"

    def test_read_optional_param_empty_string(self):
        """Test optional param parsing returns None for empty string."""
        result = HealthServerRoutingMixin._read_optional_param(
            {"value": ""}, "value"
        )
        assert result is None

    def test_read_optional_param_whitespace_only(self):
        """Test optional param parsing returns None for whitespace only."""
        result = HealthServerRoutingMixin._read_optional_param(
            {"value": "   "}, "value"
        )
        assert result is None
