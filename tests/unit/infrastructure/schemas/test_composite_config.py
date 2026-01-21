"""Unit tests for composite pipeline configuration schemas.

Tests validation logic and domain conversion for composite pipeline configs.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.domain.composite.strategy import (
    ConflictResolution,
    FallbackStrategy,
    MergeStrategy,
)
from bioetl.infrastructure.schemas.composite_config import (
    CompositeConfigFileSchema,
    CompositeConfigSchema,
    CompositeDQSchema,
    DQOverrideSchema,
    EnricherSchema,
    ExecutionSchema,
    LineageSchema,
    MergeOutputSchema,
    MergeSchema,
    SeedSchema,
)


class TestSeedSchema:
    """Tests for SeedSchema validation."""

    def test_valid_seed_config(self) -> None:
        """Test valid seed configuration."""
        schema = SeedSchema(
            pipeline="chembl.activity",
            output_keys=["id", "smiles"],
            silver_table="s3://bucket/silver",
            limit=100,
        )
        assert schema.pipeline == "chembl.activity"
        assert schema.output_keys == ["id", "smiles"]
        assert schema.silver_table == "s3://bucket/silver"
        assert schema.limit == 100

    def test_invalid_output_keys(self) -> None:
        """Test validation of output_keys."""
        # Empty list - caught by min_length=1
        with pytest.raises(ValidationError, match="List should have at least 1 item"):
            SeedSchema(
                pipeline="test",
                output_keys=[],
                silver_table="path",
            )

        # Empty string in list - caught by custom validator
        with pytest.raises(
            ValidationError, match="output_keys cannot contain empty strings"
        ):
            SeedSchema(
                pipeline="test",
                output_keys=["id", ""],
                silver_table="path",
            )

    def test_to_domain(self) -> None:
        """Test conversion to domain object."""
        schema = SeedSchema(
            pipeline="test",
            output_keys=["id"],
            silver_table="path",
            limit=50,
        )
        domain = schema.to_domain()
        assert domain.pipeline == "test"
        assert domain.output_keys == ("id",)
        assert domain.silver_table == "path"
        assert domain.limit == 50


class TestEnricherSchema:
    """Tests for EnricherSchema validation."""

    def test_valid_enricher_config(self) -> None:
        """Test valid enricher configuration."""
        schema = EnricherSchema(
            pipeline="pubchem.compound",
            join_keys=["inchi_key"],
            required=True,
            filter_condition="mw > 500",
            timeout_seconds=300,
            fallback_strategy="use_cached",
            silver_table="path",
            limit=100,
        )
        assert schema.pipeline == "pubchem.compound"
        assert schema.join_keys == ["inchi_key"]
        assert schema.required is True
        assert schema.filter_condition == "mw > 500"
        assert schema.timeout_seconds == 300
        assert schema.fallback_strategy == "use_cached"

    def test_invalid_join_keys(self) -> None:
        """Test validation of join_keys."""
        # Empty list - caught by min_length=1
        with pytest.raises(ValidationError, match="List should have at least 1 item"):
            EnricherSchema(
                pipeline="test",
                join_keys=[],
            )

        # Empty string in list - caught by custom validator
        with pytest.raises(
            ValidationError, match="join_keys cannot contain empty strings"
        ):
            EnricherSchema(
                pipeline="test",
                join_keys=[""],
            )

    def test_to_domain(self) -> None:
        """Test conversion to domain object."""
        schema = EnricherSchema(
            pipeline="test",
            join_keys=["key"],
            fallback_strategy="fail",
        )
        domain = schema.to_domain()
        assert domain.pipeline == "test"
        assert domain.join_keys == ("key",)
        assert domain.fallback_strategy == FallbackStrategy.FAIL


class TestMergeSchema:
    """Tests for MergeSchema validation."""

    def test_valid_merge_config(self) -> None:
        """Test valid merge configuration."""
        schema = MergeSchema(
            strategy="inner",
            conflict_resolution="seed_priority",
            output=MergeOutputSchema(silver="s_path", gold="g_path"),
        )
        assert schema.strategy == "inner"
        assert schema.conflict_resolution == "seed_priority"

    def test_explicit_rules_requires_priorities(self) -> None:
        """Test explicit_rules requires field_priorities."""
        with pytest.raises(ValidationError, match="field_priorities required"):
            MergeSchema(
                conflict_resolution="explicit_rules",
                output=MergeOutputSchema(silver="s", gold="g"),
            )

        # Should pass with priorities
        MergeSchema(
            conflict_resolution="explicit_rules",
            field_priorities={"field1": ["source1", "source2"]},
            output=MergeOutputSchema(silver="s", gold="g"),
        )

    def test_to_domain(self) -> None:
        """Test conversion to domain object."""
        schema = MergeSchema(
            strategy="union",
            conflict_resolution="coalesce",
            field_mappings={"old": "new"},
            output=MergeOutputSchema(silver="s", gold="g"),
        )
        domain = schema.to_domain()
        assert domain.strategy == MergeStrategy.UNION
        assert domain.conflict_resolution == ConflictResolution.COALESCE
        assert domain.field_mappings == {"old": "new"}
        assert domain.output_silver_path == "s"
        assert domain.output_gold_path == "g"


class TestDQSchemas:
    """Tests for DQ-related schemas."""

    def test_dq_override_threshold_validation(self) -> None:
        """Test DQOverrideSchema threshold validation."""
        # Valid
        DQOverrideSchema(soft_fail_threshold=0.1, hard_fail_threshold=0.2)

        # Invalid: soft >= hard
        with pytest.raises(
            ValidationError, match="soft_fail_threshold must be less than"
        ):
            DQOverrideSchema(soft_fail_threshold=0.5, hard_fail_threshold=0.5)

    def test_dq_override_to_domain(self) -> None:
        """Test DQOverrideSchema conversion to domain."""
        schema = DQOverrideSchema(soft_fail_threshold=0.1)
        domain = schema.to_domain()
        assert domain.soft_fail_threshold == 0.1
        assert domain.hard_fail_threshold is None

    def test_composite_dq_threshold_validation(self) -> None:
        """Test CompositeDQSchema threshold validation."""
        # Valid
        CompositeDQSchema(soft_fail_threshold=0.1, hard_fail_threshold=0.2)

        # Invalid: soft >= hard
        with pytest.raises(ValidationError, match="must be < hard_fail_threshold"):
            CompositeDQSchema(soft_fail_threshold=0.5, hard_fail_threshold=0.4)

    def test_composite_dq_to_domain(self) -> None:
        """Test CompositeDQSchema conversion to domain."""
        schema = CompositeDQSchema(
            enricher_overrides={"e1": DQOverrideSchema(soft_fail_threshold=0.5)},
            required_fields=["id"],
        )
        domain = schema.to_domain()
        assert "e1" in domain.enricher_overrides
        assert domain.required_fields == ("id",)


class TestCompositeConfigSchema:
    """Tests for CompositeConfigSchema validation."""

    @pytest.fixture
    def valid_config_data(self) -> dict:
        """Return valid composite config data."""
        return {
            "name": "test_composite",
            "version": "1.0.0",
            "seed": {
                "pipeline": "seed_pipe",
                "output_keys": ["id", "key1"],
                "silver_table": "s3://seed",
            },
            "enrichers": [
                {
                    "pipeline": "enricher1",
                    "join_keys": ["id"],
                    "silver_table": "s3://e1",
                }
            ],
            "merge": {"output": {"silver": "s3://merged/s", "gold": "s3://merged/g"}},
        }

    def test_valid_config(self, valid_config_data: dict) -> None:
        """Test full valid configuration."""
        schema = CompositeConfigSchema(**valid_config_data)
        assert schema.name == "test_composite"
        assert len(schema.enrichers) == 1

    def test_validate_enricher_join_keys(self, valid_config_data: dict) -> None:
        """Test validation of join keys against seed keys."""
        data = valid_config_data.copy()
        data["enrichers"] = [
            {
                "pipeline": "enricher1",
                "join_keys": ["missing_key"],
                "silver_table": "s3://e1",
            }
        ]

        with pytest.raises(
            ValidationError, match="join_key 'missing_key' not found in seed"
        ):
            CompositeConfigSchema(**data)

    def test_validate_unique_enricher_names(self, valid_config_data: dict) -> None:
        """Test validation of unique enricher names."""
        data = valid_config_data.copy()
        enricher = {
            "pipeline": "enricher1",
            "join_keys": ["id"],
            "silver_table": "s3://e1",
        }
        data["enrichers"] = [enricher, enricher]

        with pytest.raises(ValidationError, match="Duplicate enricher pipelines"):
            CompositeConfigSchema(**data)

    def test_to_domain(self, valid_config_data: dict) -> None:
        """Test conversion to full domain config."""
        schema = CompositeConfigSchema(**valid_config_data)
        domain = schema.to_domain()
        assert domain.name == "test_composite"
        assert domain.seed.pipeline == "seed_pipe"
        assert len(domain.enrichers) == 1


class TestCompositeConfigFileSchema:
    """Tests for CompositeConfigFileSchema."""

    def test_full_file_schema(self) -> None:
        """Test valid file schema."""
        data = {
            "schema_version": "2.0.0",
            "composite": {
                "name": "test",
                "seed": {
                    "pipeline": "seed",
                    "output_keys": ["id"],
                    "silver_table": "path",
                },
                "enrichers": [
                    {
                        "pipeline": "e1",
                        "join_keys": ["id"],
                    }
                ],
                "merge": {"output": {"silver": "s", "gold": "g"}},
            },
            "gold_filters": {"key": "val"},
            "maintenance": {"enabled": True},
        }
        # Use explicit instantiation to satisfy mypy
        schema = CompositeConfigFileSchema(
            schema_version=str(data["schema_version"]),
            composite=CompositeConfigSchema(**data["composite"]),  # type: ignore[arg-type]
            gold_filters=data["gold_filters"],  # type: ignore[arg-type]
            maintenance=data["maintenance"],  # type: ignore[arg-type]
        )
        assert schema.schema_version == "2.0.0"
        assert schema.gold_filters == {"key": "val"}
        assert schema.maintenance == {"enabled": True}

        domain = schema.to_domain()
        assert domain.name == "test"


class TestExecutionLineageSchemas:
    """Tests for Execution and Lineage schemas."""

    def test_execution_schema_defaults(self) -> None:
        schema = ExecutionSchema()
        assert schema.max_concurrency == 4
        assert schema.retry.max_attempts == 3

        domain = schema.to_domain()
        assert domain.max_concurrency == 4

    def test_lineage_schema_defaults(self) -> None:
        schema = LineageSchema()
        assert schema.track_field_sources is True

        domain = schema.to_domain()
        assert domain.track_field_sources is True
