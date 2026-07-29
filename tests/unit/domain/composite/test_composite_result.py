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

pytestmark = pytest.mark.unit


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
        assert result.enrichment_rate == pytest.approx(0.95)
        assert result.not_found_rate == pytest.approx(0.05)

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
        assert result.is_success is True

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

    def test_not_run_factory(self):
        """not_run factory should create NOT_RUN result."""
        result = EnrichmentResult.not_run(
            enricher_name="openalex",
            reason="Skipped due to required_only mode",
        )
        assert result.status == EnrichmentStatus.NOT_RUN
        assert result.is_success is False
        assert "required_only" in result.error_message
        assert result.records_input == 0
        assert result.records_enriched == 0

    def test_not_run_factory_default_reason(self):
        """not_run factory should use default reason."""
        result = EnrichmentResult.not_run(enricher_name="openalex")
        assert result.status == EnrichmentStatus.NOT_RUN
        assert result.error_message is not None
        assert "required_only" in result.error_message

    def test_enrichment_rate_with_zero_input(self):
        """enrichment_rate should return 0 for zero input."""
        result = EnrichmentResult(
            enricher_name="test",
            status=EnrichmentStatus.SKIPPED,
            records_input=0,
        )
        assert result.enrichment_rate == pytest.approx(0.0)

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
        assert result.enrichment_rate == pytest.approx(0.75)

    def test_merge_result_zero_records(self):
        """Enrichment rate should be 0 for empty merge."""
        result = MergeResult(
            records_merged=0,
        )
        assert result.enrichment_rate == pytest.approx(0.0)

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

    def test_composite_result_successful_enrichers(self, composite_result):
        """successful_enrichers should list successful ones."""
        assert "crossref" in composite_result.successful_enrichers
        assert "pubmed" not in composite_result.successful_enrichers

    def test_composite_result_failed_enrichers(self, composite_result):
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

    def test_had_warnings_default_false(self):
        """had_warnings should default to False."""
        result = CompositeResult(
            composite_name="test",
            composite_run_id="test-123",
            seed_result=SeedResult(pipeline_name="seed", records_silver=100),
            enrichment_results={},
            merge_result=MergeResult(records_merged=100),
        )
        assert result.had_warnings is False

    def test_had_warnings_set_true(self):
        """had_warnings should be settable to True."""
        result = CompositeResult(
            composite_name="test",
            composite_run_id="test-123",
            seed_result=SeedResult(pipeline_name="seed", records_silver=100),
            enrichment_results={
                "optional_enricher": EnrichmentResult.failed(
                    enricher_name="optional_enricher",
                    error_message="API error",
                ),
            },
            merge_result=MergeResult(records_merged=100),
            had_warnings=True,
            _required_enrichers=frozenset(),  # No required enrichers
        )
        assert result.had_warnings is True
        assert result.is_success is True  # Still successful as no required failed

    def test_composite_result_skipped_enrichers(self):
        """skipped_enrichers should list enrichers with SKIPPED status."""
        result = CompositeResult(
            composite_name="test",
            composite_run_id="test-123",
            seed_result=SeedResult(pipeline_name="seed", records_silver=100),
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref", records_input=100, records_enriched=90
                ),
                "pubmed": EnrichmentResult.skipped(
                    enricher_name="pubmed", reason="No pmid keys"
                ),
            },
            merge_result=MergeResult(records_merged=100),
        )
        assert "pubmed" in result.skipped_enrichers
        assert "crossref" not in result.skipped_enrichers
        assert len(result.skipped_enrichers) == 1

    def test_composite_result_not_run_enrichers(self):
        """not_run_enrichers should list enrichers with NOT_RUN status."""
        result = CompositeResult(
            composite_name="test",
            composite_run_id="test-123",
            seed_result=SeedResult(pipeline_name="seed", records_silver=100),
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref", records_input=100, records_enriched=90
                ),
                "openalex": EnrichmentResult.not_run(
                    enricher_name="openalex", reason="required_only mode"
                ),
            },
            merge_result=MergeResult(records_merged=100),
        )
        assert "openalex" in result.not_run_enrichers
        assert "crossref" not in result.not_run_enrichers
        assert len(result.not_run_enrichers) == 1

    def test_composite_result_optional_failed_enrichers(self):
        """optional_failed_enrichers should list non-required failed enrichers."""
        result = CompositeResult(
            composite_name="test",
            composite_run_id="test-123",
            seed_result=SeedResult(pipeline_name="seed", records_silver=100),
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref", records_input=100, records_enriched=90
                ),
                "pubmed": EnrichmentResult.failed(
                    enricher_name="pubmed", error_message="API error"
                ),
                "openalex": EnrichmentResult.failed(
                    enricher_name="openalex", error_message="Connection error"
                ),
            },
            merge_result=MergeResult(records_merged=100),
            _required_enrichers=frozenset({"crossref"}),  # Only crossref required
        )
        # pubmed and openalex are optional and failed
        assert "pubmed" in result.optional_failed_enrichers
        assert "openalex" in result.optional_failed_enrichers
        assert "crossref" not in result.optional_failed_enrichers
        assert len(result.optional_failed_enrichers) == 2

    def test_optional_failed_excludes_required(self):
        """optional_failed_enrichers should not include required enrichers."""
        result = CompositeResult(
            composite_name="test",
            composite_run_id="test-123",
            seed_result=SeedResult(pipeline_name="seed", records_silver=100),
            enrichment_results={
                "crossref": EnrichmentResult.failed(
                    enricher_name="crossref", error_message="Failed"
                ),
            },
            merge_result=MergeResult(records_merged=0),
            _required_enrichers=frozenset({"crossref"}),
        )
        # crossref is required and failed, so not in optional_failed
        assert "crossref" not in result.optional_failed_enrichers
        assert result.is_success is False  # Pipeline should fail

    def test_summary_includes_new_fields(self):
        """summary should include had_warnings and new counts."""
        result = CompositeResult(
            composite_name="test",
            composite_run_id="test-123",
            seed_result=SeedResult(pipeline_name="seed", records_silver=100),
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref", records_input=100, records_enriched=90
                ),
                "pubmed": EnrichmentResult.skipped(
                    enricher_name="pubmed", reason="No keys"
                ),
                "openalex": EnrichmentResult.not_run(
                    enricher_name="openalex", reason="required_only"
                ),
            },
            merge_result=MergeResult(records_merged=100),
            had_warnings=True,
        )
        summary = result.summary()
        assert summary["had_warnings"] is True
        assert summary["enrichers_skipped"] == 1
        assert summary["enrichers_not_run"] == 1
