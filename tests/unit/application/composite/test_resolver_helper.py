"""Test resolver helper functionality."""

import pytest

from unittest.mock import MagicMock

import polars as pl

from bioetl.application.composite.helpers.resolver_helper import (
    ResolverHelper,
    create_resolver_helper,
)
from bioetl.application.composite.join_key_normalization import (
    JOIN_KEY_NORMALIZATION_POLICIES,
)


pytestmark = pytest.mark.unit

class TestResolverHelper:
    """Test ResolverHelper class functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.helper = create_resolver_helper(
            logger=self.mock_logger,
            normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
        )

    def test_create_resolver_helper(self) -> None:
        """Test that create_resolver_helper creates a proper instance."""
        assert isinstance(self.helper, ResolverHelper)
        assert self.helper._logger == self.mock_logger
        assert self.helper._normalization_policies == JOIN_KEY_NORMALIZATION_POLICIES

    def test_normalize_join_keys(self) -> None:
        """Test join key normalization."""
        # Create test DataFrame with mixed case keys
        df = pl.DataFrame(
            {
                "CHEMBL_ID": ["CHEMBL1", "CHEMBL2"],
                "pubchem_cid": [123, 456],
                "other_col": ["a", "b"],
            }
        )

        # Normalize the keys
        result = self.helper.normalize_join_keys(
            df=df, join_keys=["CHEMBL_ID", "pubchem_cid"]
        )

        # Verify normalization occurred - should keep original column names
        assert "CHEMBL_ID" in result.columns
        assert "pubchem_cid" in result.columns
        # For keys without specific policies, values should remain unchanged
        assert result["CHEMBL_ID"][0] == "CHEMBL1"

    def test_log_methods(self) -> None:
        """Test that logging methods work correctly."""
        # Test each logging method
        self.helper.log_info("Test info", key="value")
        self.mock_logger.info.assert_called_with("Test info", key="value")

        self.helper.log_warning("Test warning", key="value")
        self.mock_logger.warning.assert_called_with("Test warning", key="value")

        self.helper.log_debug("Test debug", key="value")
        self.mock_logger.debug.assert_called_with("Test debug", key="value")

        self.helper.log_error("Test error", key="value")
        self.mock_logger.error.assert_called_with("Test error", key="value")

    def test_create_resolver_service(self) -> None:
        """Test creating a resolver service."""

        # Create a simple mock service class
        class MockService:
            def __init__(self, logger, normalization_policies, extra_param=None):
                self.logger = logger
                self.normalization_policies = normalization_policies
                self.extra_param = extra_param

        # Create service using helper
        service = self.helper.create_resolver_service(MockService, extra_param="test")

        # Verify service was created correctly
        assert isinstance(service, MockService)
        assert service.logger == self.mock_logger
        assert service.normalization_policies == JOIN_KEY_NORMALIZATION_POLICIES
        assert service.extra_param == "test"


class TestResolverHelperIntegration:
    """Test ResolverHelper integration with existing services."""

    def test_seed_key_resolver_integration(self) -> None:
        """Test that SeedKeyResolver works with ResolverHelper."""
        from bioetl.application.composite.dependency_key_resolvers import (
            SeedKeyResolver,
        )

        mock_logger = MagicMock()
        helper = create_resolver_helper(mock_logger)

        # Create resolver using helper
        resolver = SeedKeyResolver(resolver_helper=helper)

        # Verify it has the helper
        assert hasattr(resolver, "_resolver_helper")
        assert resolver._resolver_helper == helper

    def test_chained_key_resolver_integration(self) -> None:
        """Test that ChainedKeyResolver works with ResolverHelper."""
        from bioetl.application.composite.dependency_key_resolvers import (
            ChainedKeyResolver,
        )

        mock_logger = MagicMock()
        helper = create_resolver_helper(mock_logger)

        # Create resolver using helper
        resolver = ChainedKeyResolver(resolver_helper=helper)

        # Verify it has the helper
        assert hasattr(resolver, "_resolver_helper")
        assert resolver._resolver_helper == helper


class TestDuplicationReduction:
    """Test that duplication has been reduced."""

    def test_resolver_helper_reduces_duplication(self) -> None:
        """Test that ResolverHelper consolidates common functionality."""
        from bioetl.application.composite.dependency_key_resolvers import (
            SeedKeyResolver,
            ChainedKeyResolver,
        )

        # Both resolvers should use the same helper interface
        mock_logger = MagicMock()
        helper = create_resolver_helper(mock_logger)

        seed_resolver = SeedKeyResolver(resolver_helper=helper)
        chained_resolver = ChainedKeyResolver(resolver_helper=helper)

        # Both should use the same helper instance
        assert seed_resolver._resolver_helper is chained_resolver._resolver_helper

        # Both should have access to the same methods
        assert hasattr(seed_resolver._resolver_helper, "normalize_join_keys")
        assert hasattr(seed_resolver._resolver_helper, "log_info")
        assert hasattr(chained_resolver._resolver_helper, "normalize_join_keys")
        assert hasattr(chained_resolver._resolver_helper, "log_info")
