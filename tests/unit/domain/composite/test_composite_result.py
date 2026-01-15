"""Unit tests for composite pipeline result models.

Tests for EnrichmentResult, MergeResult, CompositeResult.
"""

from __future__ import annotations

import pytest

from bioetl.domain.composite.result import (
    CompositeResult,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)


class TestEnrichmentResult:
    """Tests for EnrichmentResult."""

    def test_success_factory(self):
        """success factory should create SUCCESS result."""
        result = EnrichmentResult.success(
            enricher_name="crossref",
            records_input=100,
            records_enriched=95,
            records_not_found=5,
            duration_seconds=10.5,
        )
        assert result.status == EnrichmentStatus.SUCCESS
        assert result.is_success is True
        assert result.enrichment_rate == 0.95
        assert result.not_found_rate == 0.05

    def test_failed_factory(self):
        """failed factory should create FAILED result."""
        result = EnrichmentResult.failed(
            enricher_name="crossref",
            error_message="Connection timeout",
            records_input=100,
        )
        assert result.status == EnrichmentStatus.FAILED
        assert result.is_success is False
        assert result.error_message == "Connection timeout"

    def test_skipped_factory(self):
        """skipped factory should create SKIPPED result."""
        result = EnrichmentResult.skipped(
            enricher_name="pubmed",
            reason="Filter excluded all records",
        )
        assert result.status == EnrichmentStatus.SKIPPED
        assert result.is_success is False

    def test_timeout_factory(self):
        """timeout factory should create TIMEOUT result."""
        result = EnrichmentResult.timeout(
            enricher_name="semanticscholar",
            timeout_seconds=600,
            records_input=100,
        )
        assert result.status == EnrichmentStatus.TIMEOUT
        assert result.is_success is False
        assert "600" in result.error_message

    def test_enrichment_rate_with_zero_input(self):
        """enrichment_rate should return 0 for zero input."""
        result = EnrichmentResult(
            enricher_name="test",
            status=EnrichmentStatus.SKIPPED,
            records_input=0,
        )
        assert result.enrichment_rate == 0.0

    def test_partial_status_is_success(self):
        """PARTIAL status should be considered success."""
        result = EnrichmentResult(
            enricher_name="test",
            status=EnrichmentStatus.PARTIAL,
            records_input=100,
            records_enriched=50,
        )
        assert result.is_success is True

    def test_invalid_dq_error_rate_raises(self):
        """DQ error rate outside 0-1 should raise ValueError."""
        with pytest.raises(ValueError, match=r"dq_error_rate must be 0\.0-1\.0"):
            EnrichmentResult(
                enricher_name="test",
                status=EnrichmentStatus.SUCCESS,
                dq_error_rate=1.5,
            )

    def test_negative_duration_raises(self):
        """Negative duration should raise ValueError."""
        with pytest.raises(ValueError, match="duration_seconds must be >= 0"):
            EnrichmentResult(
                enricher_name="test",
                status=EnrichmentStatus.SUCCESS,
                duration_seconds=-1.0,
            )


class TestSeedResult:
    """Tests for SeedResult."""

    def test_seed_result_is_success(self):
        """SeedResult with records should be success."""
        result = SeedResult(
            pipeline_name="chembl_publication",
            records_extracted=100,
            records_silver=95,
            keys_generated=95,
        )
        assert result.is_success is True

    def test_seed_result_resumed_is_success(self):
        """Resumed SeedResult should be success."""
        result = SeedResult(
            pipeline_name="chembl_publication",
            resumed=True,
        )
        assert result.is_success is True

    def test_seed_result_empty_not_success(self):
        """SeedResult with no records and not resumed should not be success."""
        result = SeedResult(
            pipeline_name="chembl_publication",
            records_silver=0,
        )
        assert result.is_success is False


class TestMergeResult:
    """Tests for MergeResult."""

    def test_merge_result_enrichment_rate(self):
        """Enrichment rate should be calculated correctly."""
        result = MergeResult(
            records_merged=100,
            records_from_seed=100,
            records_enriched=75,
        )
        assert result.enrichment_rate == 0.75

    def test_merge_result_zero_records(self):
        """Enrichment rate should be 0 for empty merge."""
        result = MergeResult(
            records_merged=0,
        )
        assert result.enrichment_rate == 0.0

    def test_merge_result_sources_converted_to_tuple(self):
        """sources_used list should be converted to tuple."""
        result = MergeResult(
            sources_used=["seed", "crossref"],  # type: ignore
        )
        assert isinstance(result.sources_used, tuple)


class TestCompositeResult:
    """Tests for CompositeResult."""

    @pytest.fixture
    def composite_result(self):
        """Create a composite result for testing."""
        return CompositeResult(
            composite_name="composite_publication",
            composite_run_id="test-123",
            seed_result=SeedResult(
                pipeline_name="chembl_publication",
                records_silver=100,
            ),
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
                "pubmed": EnrichmentResult.failed(
                    enricher_name="pubmed",
                    error_message="API error",
                ),
            },
            merge_result=MergeResult(
                records_merged=90,
            ),
            _required_enrichers=frozenset({"crossref"}),
        )

    def test_is_success_with_successful_required(self, composite_result):
        """Composite should be success if required enrichers succeed."""
        assert composite_result.is_success is True

    def test_is_success_fails_if_required_fails(self):
        """Composite should fail if required enricher fails."""
        result = CompositeResult(
            composite_name="test",
            composite_run_id="test-123",
            seed_result=SeedResult(
                pipeline_name="seed",
                records_silver=100,
            ),
            enrichment_results={
                "crossref": EnrichmentResult.failed(
                    enricher_name="crossref",
                    error_message="Failed",
                ),
            },
            merge_result=MergeResult(records_merged=0),
            _required_enrichers=frozenset({"crossref"}),
        )
        assert result.is_success is False
        assert result.required_enrichers_succeeded is False

    def test_successful_enrichers(self, composite_result):
        """successful_enrichers should list successful ones."""
        assert "crossref" in composite_result.successful_enrichers
        assert "pubmed" not in composite_result.successful_enrichers

    def test_failed_enrichers(self, composite_result):
        """failed_enrichers should list failed ones."""
        assert "pubmed" in composite_result.failed_enrichers
        assert "crossref" not in composite_result.failed_enrichers

    def test_summary(self, composite_result):
        """summary should return dict with key metrics."""
        summary = composite_result.summary()
        assert summary["composite_name"] == "composite_publication"
        assert summary["is_success"] is True
        assert summary["enrichers_run"] == 2
        assert summary["enrichers_succeeded"] == 1
        assert summary["enrichers_failed"] == 1
