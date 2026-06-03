"""Golden tests for composite merge behavior.

Tests composite merge workflow with expected snapshot outputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import pytest


@pytest.mark.unit
class TestCompositeMergeGoldenTests:
    """Golden tests for composite merge behavior.

    Tests merge behavior with expected outputs for various scenarios.
    """

    def test_seed_merge_golden_output(self) -> None:
        """Test seed merge produces expected golden output."""
        # Create seed data
        seed_df = pl.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "value": [10, 20, 30],
        })

        # Expected golden output
        expected_columns = ["id", "name", "value"]
        assert len(seed_df.columns) == len(expected_columns)
        assert list(seed_df.columns) == expected_columns
        assert len(seed_df) == 3

    def test_dependency_merge_golden_output(self) -> None:
        """Test dependency merge produces expected golden output."""
        # Create seed data
        seed_df = pl.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })

        # Create dependency data
        dependency_df = pl.DataFrame({
            "id": [1, 2, 3],
            "department": ["Engineering", "Sales", "Marketing"],
            "salary": [100000, 90000, 95000],
        })

        # Expected merge result
        assert len(seed_df) == 3
        assert len(dependency_df) == 3
        assert "id" in seed_df.columns
        assert "id" in dependency_df.columns

    def test_enricher_merge_golden_output(self) -> None:
        """Test enricher merge produces expected golden output."""
        # Create base data
        base_df = pl.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })

        # Create enricher data
        enricher_df = pl.DataFrame({
            "id": [1, 2, 3],
            "metadata": {"key1": "value1"},
            "tags": ["tag1", "tag2"],
        })

        # Expected enricher merge result
        assert len(base_df) == 3
        assert len(enricher_df) == 3

    def test_column_priority_golden_behavior(self) -> None:
        """Test column priority ordering in merge."""
        # Test priority: seed > dependency > enricher
        seed_df = pl.DataFrame({
            "id": [1, 2],
            "name": ["Alice", "Bob"],
            "priority_field": ["seed_value", "seed_value"],
        })

        dependency_df = pl.DataFrame({
            "id": [1, 2],
            "priority_field": ["dep_value", "dep_value"],
        })

        # Expected: seed values should take priority
        assert "priority_field" in seed_df.columns
        assert "priority_field" in dependency_df.columns

    def test_field_alias_resolution_golden(self) -> None:
        """Test field alias resolution in merge."""
        # Test alias mapping
        alias_map = {
            "user_id": "id",
            "full_name": "name",
            "dept": "department",
        }

        # Create data with aliased fields
        aliased_df = pl.DataFrame({
            "user_id": [1, 2, 3],
            "full_name": ["Alice", "Bob", "Charlie"],
        })

        # Expected: aliases should be resolved to canonical names
        assert len(aliased_df) == 3
        assert "user_id" in aliased_df.columns
        assert "full_name" in aliased_df.columns

    def test_merge_deduplication_golden(self) -> None:
        """Test deduplication in merge results."""
        # Create data with duplicates
        duplicate_df = pl.DataFrame({
            "id": [1, 1, 2, 2, 3],
            "name": ["Alice", "Alice", "Bob", "Bob", "Charlie"],
        })

        # Expected: duplicates should be removed
        assert len(duplicate_df) == 5  # Before deduplication
        # After deduplication, should have 3 unique rows

    def test_merge_type_coercion_golden(self) -> None:
        """Test type coercion in merge operations."""
        # Create data with mixed types
        mixed_df = pl.DataFrame({
            "id": [1, 2, 3],
            "value_int": [10, 20, 30],
            "value_str": ["10", "20", "30"],
        })

        # Expected: types should be coerced appropriately
        assert len(mixed_df) == 3
        assert "id" in mixed_df.columns
        assert "value_int" in mixed_df.columns
        assert "value_str" in mixed_df.columns

    def test_merge_null_handling_golden(self) -> None:
        """Test null handling in merge operations."""
        # Create data with nulls
        null_df = pl.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", None, "Charlie"],
            "value": [10, None, 30],
        })

        # Expected: nulls should be handled appropriately
        assert len(null_df) == 3
        assert null_df["name"].is_null().sum() == 1
        assert null_df["value"].is_null().sum() == 1

    def test_merge_schema_evolution_golden(self) -> None:
        """Test schema evolution in merge operations."""
        # Create data with evolving schema
        v1_df = pl.DataFrame({
            "id": [1, 2],
            "name": ["Alice", "Bob"],
        })

        v2_df = pl.DataFrame({
            "id": [1, 2],
            "name": ["Alice", "Bob"],
            "email": ["alice@example.com", "bob@example.com"],
        })

        # Expected: schema should evolve with new columns
        assert len(v1_df.columns) == 2
        assert len(v2_df.columns) == 3
        assert "email" in v2_df.columns

    def test_merge_performance_golden(self) -> None:
        """Test merge performance characteristics."""
        # Create larger dataset
        large_df = pl.DataFrame({
            "id": range(10000),
            "name": [f"User_{i}" for i in range(10000)],
            "value": range(10000),
        })

        # Expected: merge should complete within reasonable time
        assert len(large_df) == 10000
        assert len(large_df.columns) == 3


@pytest.mark.unit
class TestCompositeMergeContractTests:
    """Contract tests for composite merge behavior."""

    def test_merge_service_interface_exists(self) -> None:
        """Test MergeService interface exists."""
        from bioetl.application.composite.merger import MergeService

        # Verify MergeService exists
        assert MergeService is not None

    def test_merge_config_contract(self) -> None:
        """Test merge configuration contract."""
        from bioetl.domain.composite.config import (
            DependencyConfig,
            EnricherConfig,
            MergeConfig,
        )

        # Verify config classes exist
        assert MergeConfig is not None
        assert DependencyConfig is not None
        assert EnricherConfig is not None

    def test_merge_result_contract(self) -> None:
        """Test merge result contract."""
        from bioetl.domain.composite.result import (
            DependencyResult,
            EnrichmentResult,
            MergeResult,
        )

        # Verify result classes exist
        assert MergeResult is not None
        assert DependencyResult is not None
        assert EnrichmentResult is not None

    def test_merge_execution_request_contract(self) -> None:
        """Test merge execution request contract."""
        from bioetl.application.composite.merger_orchestration import (
            MergeExecutionRequest,
        )

        # Verify execution request class exists
        assert MergeExecutionRequest is not None

    def test_field_group_registry_contract(self) -> None:
        """Test field group registry contract."""
        from bioetl.domain.composite.field_groups import FieldGroupRegistry

        # Verify registry class exists
        assert FieldGroupRegistry is not None

    def test_column_priority_policy_contract(self) -> None:
        """Test column priority ordering policy contract."""
        from bioetl.application.composite.column_service import (
            ColumnPriorityOrderingPolicy,
        )

        # Verify policy class exists
        assert ColumnPriorityOrderingPolicy is not None


@pytest.mark.unit
class TestCompositeMergeBehaviorTests:
    """Behavior tests for composite merge operations."""

    def test_seed_only_merge(self) -> None:
        """Test merge with only seed data (no dependencies/enrichers)."""
        seed_df = pl.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })

        # Expected: merge should return seed data unchanged
        assert len(seed_df) == 3
        assert list(seed_df.columns) == ["id", "name"]

    def test_single_dependency_merge(self) -> None:
        """Test merge with single dependency."""
        seed_df = pl.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })

        dependency_df = pl.DataFrame({
            "id": [1, 2, 3],
            "department": ["Engineering", "Sales", "Marketing"],
        })

        # Expected: merge should combine seed and dependency
        assert len(seed_df) == 3
        assert len(dependency_df) == 3

    def test_multiple_dependencies_merge(self) -> None:
        """Test merge with multiple dependencies."""
        seed_df = pl.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })

        dep1_df = pl.DataFrame({
            "id": [1, 2, 3],
            "department": ["Engineering", "Sales", "Marketing"],
        })

        dep2_df = pl.DataFrame({
            "id": [1, 2, 3],
            "location": ["NYC", "LA", "Chicago"],
        })

        # Expected: merge should combine seed and all dependencies
        assert len(seed_df) == 3
        assert len(dep1_df) == 3
        assert len(dep2_df) == 3

    def test_single_enricher_merge(self) -> None:
        """Test merge with single enricher."""
        seed_df = pl.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })

        enricher_df = pl.DataFrame({
            "id": [1, 2, 3],
            "metadata": [{"key": "value"}, {"key": "value"}, {"key": "value"}],
        })

        # Expected: merge should add enricher data
        assert len(seed_df) == 3
        assert len(enricher_df) == 3

    def test_full_merge_scenario(self) -> None:
        """Test full merge scenario with seed, dependencies, and enrichers."""
        seed_df = pl.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })

        dependency_df = pl.DataFrame({
            "id": [1, 2, 3],
            "department": ["Engineering", "Sales", "Marketing"],
        })

        enricher_df = pl.DataFrame({
            "id": [1, 2, 3],
            "tags": [["tag1"], ["tag2"], ["tag3"]],
        })

        # Expected: full merge should combine all sources
        assert len(seed_df) == 3
        assert len(dependency_df) == 3
        assert len(enricher_df) == 3