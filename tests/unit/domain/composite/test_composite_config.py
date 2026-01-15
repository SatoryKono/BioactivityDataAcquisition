"""Unit tests for composite pipeline configuration models.

Tests for CompositeConfig, EnricherConfig, SeedConfig, MergeConfig.
"""

from __future__ import annotations

import pytest

from bioetl.domain.composite.config import (
    CompositeDQConfig,
    CompositeConfig,
    DQOverrideConfig,
    EnricherConfig,
    ExecutionConfig,
    LineageConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.strategy import (
    ConflictResolution,
    FallbackStrategy,
    MergeStrategy,
)


class TestSeedConfig:
    """Tests for SeedConfig."""

    def test_valid_seed_config(self):
        """Valid seed config should be created successfully."""
        config = SeedConfig(
            pipeline="chembl_publication",
            output_keys=("document_id", "doi", "pmid"),
            silver_table="silver/chembl/publication",
        )
        assert config.pipeline == "chembl_publication"
        assert config.output_keys == ("document_id", "doi", "pmid")
        assert config.silver_table == "silver/chembl/publication"
        assert config.limit is None

    def test_seed_config_with_limit(self):
        """Seed config with limit should work."""
        config = SeedConfig(
            pipeline="chembl_publication",
            output_keys=("doi",),
            silver_table="silver/chembl/publication",
            limit=100,
        )
        assert config.limit == 100

    def test_seed_config_converts_list_to_tuple(self):
        """Lists should be converted to tuples for immutability."""
        config = SeedConfig(
            pipeline="chembl_publication",
            output_keys=["doi", "pmid"],  # type: ignore
            silver_table="silver/chembl/publication",
        )
        assert isinstance(config.output_keys, tuple)
        assert config.output_keys == ("doi", "pmid")

    def test_seed_config_empty_pipeline_raises(self):
        """Empty pipeline name should raise ValueError."""
        with pytest.raises(ValueError, match="pipeline name cannot be empty"):
            SeedConfig(
                pipeline="",
                output_keys=("doi",),
                silver_table="silver/chembl/publication",
            )

    def test_seed_config_empty_output_keys_raises(self):
        """Empty output_keys should raise ValueError."""
        with pytest.raises(ValueError, match="output_keys cannot be empty"):
            SeedConfig(
                pipeline="chembl_publication",
                output_keys=(),
                silver_table="silver/chembl/publication",
            )

    def test_seed_config_invalid_limit_raises(self):
        """Non-positive limit should raise ValueError."""
        with pytest.raises(ValueError, match="limit must be positive"):
            SeedConfig(
                pipeline="chembl_publication",
                output_keys=("doi",),
                silver_table="silver/chembl/publication",
                limit=0,
            )


class TestEnricherConfig:
    """Tests for EnricherConfig."""

    def test_valid_enricher_config(self):
        """Valid enricher config should be created successfully."""
        config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=True,
            timeout_seconds=600,
        )
        assert config.pipeline == "crossref_publication"
        assert config.join_keys == ("doi",)
        assert config.required is True
        assert config.timeout_seconds == 600
        assert config.fallback_strategy == FallbackStrategy.SKIP

    def test_enricher_config_with_fallback_keys(self):
        """Enricher with multiple join keys should work."""
        config = EnricherConfig(
            pipeline="openalex_publication",
            join_keys=("doi", "pmid"),
            required=False,
        )
        assert config.join_keys == ("doi", "pmid")
        assert config.primary_join_key == "doi"
        assert config.has_fallback_keys is True

    def test_enricher_config_single_key_no_fallback(self):
        """Enricher with single key should have no fallback."""
        config = EnricherConfig(
            pipeline="pubmed_publication",
            join_keys=("pmid",),
        )
        assert config.has_fallback_keys is False

    def test_enricher_config_filter_condition(self):
        """Enricher with filter condition should store it."""
        config = EnricherConfig(
            pipeline="pubmed_publication",
            join_keys=("pmid",),
            filter_condition="pmid IS NOT NULL",
        )
        assert config.filter_condition == "pmid IS NOT NULL"

    def test_enricher_config_string_fallback_strategy(self):
        """String fallback strategy should be converted to enum."""
        config = EnricherConfig(
            pipeline="test",
            join_keys=("id",),
            fallback_strategy="use_cached",  # type: ignore
        )
        assert config.fallback_strategy == FallbackStrategy.USE_CACHED

    def test_enricher_config_empty_pipeline_raises(self):
        """Empty pipeline should raise ValueError."""
        with pytest.raises(ValueError, match="pipeline name cannot be empty"):
            EnricherConfig(
                pipeline="",
                join_keys=("doi",),
            )

    def test_enricher_config_empty_join_keys_raises(self):
        """Empty join_keys should raise ValueError."""
        with pytest.raises(ValueError, match="join_keys cannot be empty"):
            EnricherConfig(
                pipeline="crossref",
                join_keys=(),
            )


class TestMergeConfig:
    """Tests for MergeConfig."""

    def test_valid_merge_config(self):
        """Valid merge config should be created successfully."""
        config = MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver/composite/publication",
            output_gold_path="gold/publication_enriched",
        )
        assert config.strategy == MergeStrategy.LEFT_OUTER
        assert config.conflict_resolution == ConflictResolution.SEED_PRIORITY
        assert config.output_silver_path == "silver/composite/publication"
        assert config.output_gold_path == "gold/publication_enriched"

    def test_merge_config_string_strategy(self):
        """String strategy should be converted to enum."""
        config = MergeConfig(
            strategy="inner",  # type: ignore
            conflict_resolution="coalesce",  # type: ignore
            output_silver_path="silver/test",
            output_gold_path="gold/test",
        )
        assert config.strategy == MergeStrategy.INNER
        assert config.conflict_resolution == ConflictResolution.COALESCE

    def test_merge_config_with_field_priorities(self):
        """Merge config with field priorities should work."""
        config = MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.EXPLICIT_RULES,
            output_silver_path="silver/test",
            output_gold_path="gold/test",
            field_priorities={
                "title": ("chembl", "crossref"),
                "abstract": ("pubmed", "openalex"),
            },
        )
        assert config.get_field_priority("title") == ("chembl", "crossref")
        assert config.get_field_priority("nonexistent") is None

    def test_merge_config_explicit_rules_requires_priorities(self):
        """EXPLICIT_RULES without field_priorities should raise."""
        with pytest.raises(ValueError, match="field_priorities required"):
            MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.EXPLICIT_RULES,
                output_silver_path="silver/test",
                output_gold_path="gold/test",
            )


class TestCompositeDQConfig:
    """Tests for CompositeDQConfig."""

    def test_valid_dq_config(self):
        """Valid DQ config should be created successfully."""
        config = CompositeDQConfig(
            soft_fail_threshold=0.10,
            hard_fail_threshold=0.30,
        )
        assert config.soft_fail_threshold == 0.10
        assert config.hard_fail_threshold == 0.30

    def test_dq_config_with_overrides(self):
        """DQ config with enricher overrides should work."""
        config = CompositeDQConfig(
            soft_fail_threshold=0.10,
            hard_fail_threshold=0.30,
            enricher_overrides={
                "semanticscholar": DQOverrideConfig(
                    soft_fail_threshold=0.20,
                    hard_fail_threshold=0.50,
                ),
            },
        )
        assert config.get_enricher_soft_threshold("semanticscholar") == 0.20
        assert config.get_enricher_hard_threshold("semanticscholar") == 0.50
        # Non-overridden enrichers use defaults
        assert config.get_enricher_soft_threshold("crossref") == 0.10
        assert config.get_enricher_hard_threshold("crossref") == 0.30

    def test_dq_config_invalid_thresholds(self):
        """Invalid threshold order should raise ValueError."""
        with pytest.raises(ValueError, match="soft_fail_threshold must be less than"):
            CompositeDQConfig(
                soft_fail_threshold=0.50,
                hard_fail_threshold=0.30,
            )


class TestCompositeConfig:
    """Tests for CompositeConfig."""

    @pytest.fixture
    def valid_composite_config(self):
        """Create a valid composite config for testing."""
        return CompositeConfig(
            name="composite_publication",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_publication",
                output_keys=("document_id", "doi", "pmid"),
                silver_table="silver/chembl/publication",
            ),
            enrichers=(
                EnricherConfig(
                    pipeline="crossref_publication",
                    join_keys=("doi",),
                    required=True,
                ),
                EnricherConfig(
                    pipeline="pubmed_publication",
                    join_keys=("pmid",),
                    required=False,
                ),
            ),
            merge=MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.SEED_PRIORITY,
                output_silver_path="silver/composite/publication",
                output_gold_path="gold/publication_enriched",
            ),
        )

    def test_valid_composite_config(self, valid_composite_config):
        """Valid composite config should be created successfully."""
        config = valid_composite_config
        assert config.name == "composite_publication"
        assert config.version == "1.0.0"
        assert len(config.enrichers) == 2

    def test_composite_config_required_enrichers(self, valid_composite_config):
        """Required enrichers should be correctly identified."""
        config = valid_composite_config
        assert config.required_enrichers == ("crossref_publication",)
        assert config.optional_enrichers == ("pubmed_publication",)

    def test_composite_config_get_enricher(self, valid_composite_config):
        """get_enricher should return correct enricher config."""
        config = valid_composite_config
        enricher = config.get_enricher("crossref_publication")
        assert enricher is not None
        assert enricher.pipeline == "crossref_publication"
        assert enricher.required is True
        assert config.get_enricher("nonexistent") is None

    def test_composite_config_lock_key(self, valid_composite_config):
        """Lock key should be generated correctly."""
        config = valid_composite_config
        assert config.lock_key == "composite:composite_publication"

    def test_composite_config_validates_join_keys(self):
        """Join keys must exist in seed output_keys."""
        with pytest.raises(ValueError, match="join_key 'invalid' not found"):
            CompositeConfig(
                name="test",
                version="1.0.0",
                seed=SeedConfig(
                    pipeline="seed",
                    output_keys=("id", "doi"),
                    silver_table="silver/test",
                ),
                enrichers=(
                    EnricherConfig(
                        pipeline="enricher",
                        join_keys=("invalid",),  # Not in seed output_keys
                    ),
                ),
                merge=MergeConfig(
                    strategy=MergeStrategy.LEFT_OUTER,
                    conflict_resolution=ConflictResolution.SEED_PRIORITY,
                    output_silver_path="silver/test",
                    output_gold_path="gold/test",
                ),
            )

    def test_composite_config_validates_unique_enrichers(self):
        """Enricher pipeline names must be unique."""
        with pytest.raises(ValueError, match="Duplicate enricher pipelines"):
            CompositeConfig(
                name="test",
                version="1.0.0",
                seed=SeedConfig(
                    pipeline="seed",
                    output_keys=("id",),
                    silver_table="silver/test",
                ),
                enrichers=(
                    EnricherConfig(
                        pipeline="enricher",
                        join_keys=("id",),
                    ),
                    EnricherConfig(
                        pipeline="enricher",  # Duplicate
                        join_keys=("id",),
                    ),
                ),
                merge=MergeConfig(
                    strategy=MergeStrategy.LEFT_OUTER,
                    conflict_resolution=ConflictResolution.SEED_PRIORITY,
                    output_silver_path="silver/test",
                    output_gold_path="gold/test",
                ),
            )

    def test_composite_config_to_dict(self, valid_composite_config):
        """to_dict should serialize config correctly."""
        config = valid_composite_config
        data = config.to_dict()
        assert data["name"] == "composite_publication"
        assert data["version"] == "1.0.0"
        assert len(data["enrichers"]) == 2
