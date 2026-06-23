"""Unit tests for EnrichmentCrossValidator application service.

Tests cross-validation of seed vs enricher data with exact, fuzzy,
and numeric tolerance comparisons.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.cross_validator import EnrichmentCrossValidator
from bioetl.domain.composite.config import CrossValidationConfig
from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    EnricherFieldPairing,
    FieldComparisonSpec,
)

pytestmark = pytest.mark.unit


def _make_config(
    *,
    enabled: bool = True,
    warning_threshold: int = 1,
    error_threshold: int = 2,
    quarantine_threshold: int = 2,
    pairings: tuple[EnricherFieldPairing, ...] = (),
) -> CrossValidationConfig:
    """Create a CrossValidationConfig for testing."""
    return CrossValidationConfig(
        enabled=enabled,
        warning_threshold=warning_threshold,
        error_threshold=error_threshold,
        quarantine_threshold=quarantine_threshold,
        enricher_pairings=pairings,
    )


def _make_pairing(
    enricher: str = "crossref_publication",
    fields: tuple[FieldComparisonSpec, ...] | None = None,
) -> EnricherFieldPairing:
    """Create an EnricherFieldPairing for testing."""
    if fields is None:
        fields = (
            FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
            FieldComparisonSpec(
                field_name="title", method=ComparisonMethod.FUZZY, threshold=0.8
            ),
            FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
        )
    return EnricherFieldPairing(enricher_pipeline=enricher, fields=fields)


def _make_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


class TestValidateDisabled:
    """Tests for disabled cross-validation."""

    def test_returns_unchanged_df_when_disabled(self):
        config = _make_config(enabled=False)
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame({"a": [1, 2, 3]})
        result_df, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert result_df.equals(df)
        assert stats.total_records == 3
        assert stats.passed == 0  # default


class TestValidateExactComparison:
    """Tests for exact field comparison."""

    def test_all_match(self):
        """All records match -> all PASS, no warnings or errors."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a", "10.1/b"],
                "crossref.publication.doi": ["10.1/a", "10.1/b"],
                "chembl.publication.volume": ["1", "2"],
                "crossref.publication.volume": ["1", "2"],
            }
        )

        result_df, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.total_records == 2
        assert stats.passed == 2
        assert stats.warned == 0
        assert stats.errored == 0
        assert "_cv_warn" in result_df.columns
        assert "_cv_error" in result_df.columns
        assert "_cv_quarantine" in result_df.columns

    def test_one_mismatch_gives_warning(self):
        """One field mismatch -> WARNING verdict."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": ["10.1/a"],
                "chembl.publication.volume": ["1"],
                "crossref.publication.volume": ["DIFFERENT"],  # 1 mismatch
            }
        )

        _, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.warned == 1
        assert stats.errored == 0

    def test_two_mismatches_gives_error(self):
        """Two field mismatches -> ENRICHER_ERROR, enricher columns nullified."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="issue", method=ComparisonMethod.EXACT),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": ["10.1/WRONG"],  # mismatch 1
                "chembl.publication.volume": ["1"],
                "crossref.publication.volume": ["WRONG"],  # mismatch 2
                "chembl.publication.issue": ["5"],
                "crossref.publication.issue": ["5"],
            }
        )

        result_df, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.errored == 1
        assert stats.warned == 0
        # Enricher columns should be nullified
        assert result_df["crossref.publication.doi"][0] is None
        assert result_df["crossref.publication.volume"][0] is None
        assert result_df["crossref.publication.issue"][0] is None


class TestValidateNullHandling:
    """Tests for null/empty value handling."""

    def test_null_seed_field_skipped(self):
        """Null seed value -> comparison skipped, not counted as mismatch."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": [None],
                "crossref.publication.doi": ["10.1/a"],
                "chembl.publication.volume": [None],
                "crossref.publication.volume": ["1"],
            }
        )

        _, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.passed == 1  # No mismatches since both fields skipped
        assert stats.warned == 0
        assert stats.errored == 0

    def test_null_enricher_field_skipped(self):
        """Null enricher value -> comparison skipped."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": [None],
                "chembl.publication.volume": ["1"],
                "crossref.publication.volume": [None],
            }
        )

        _, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.passed == 1
        assert stats.warned == 0

    def test_empty_string_treated_as_null(self):
        """Empty string seed value -> comparison skipped."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": [""],
                "crossref.publication.doi": ["10.1/a"],
                "chembl.publication.volume": [""],
                "crossref.publication.volume": ["1"],
            }
        )

        _, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.passed == 1
        assert stats.warned == 0


class TestValidateFuzzyComparison:
    """Tests for fuzzy (Jaccard) comparison."""

    def test_similar_titles_pass(self):
        """Titles with Jaccard >= 0.8 should match."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(
                    field_name="title", method=ComparisonMethod.FUZZY, threshold=0.8
                ),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        # 9 out of 11 words match -> Jaccard = 9/11 = 0.818 >= 0.8
        df = pl.DataFrame(
            {
                "chembl.publication.title": [
                    "Discovery of Novel EGFR Inhibitors in Human Cancer Cell Lines"
                ],
                "crossref.publication.title": [
                    "Discovery of Novel EGFR Inhibitors in Human Cancer Cell Models"
                ],
            }
        )

        _, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.passed == 1

    def test_different_titles_mismatch(self):
        """Titles with Jaccard < 0.8 should mismatch."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(
                    field_name="title", method=ComparisonMethod.FUZZY, threshold=0.8
                ),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.title": ["Alpha Beta"],
                "crossref.publication.title": ["Gamma Delta Epsilon Zeta"],
            }
        )

        _, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.warned == 1  # 1 mismatch = WARNING


class TestValidateNumericComparison:
    """Tests for numeric tolerance comparison."""

    def test_within_tolerance_passes(self):
        """Values within 10% tolerance should match."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(
                    field_name="citations_received",
                    method=ComparisonMethod.NUMERIC_TOLERANCE,
                    threshold=0.10,
                ),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.citations_received": [100],
                "crossref.publication.citations_received": [108],  # 8% diff
            }
        )

        _, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.passed == 1

    def test_outside_tolerance_mismatches(self):
        """Values beyond 10% tolerance should mismatch."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(
                    field_name="citations_received",
                    method=ComparisonMethod.NUMERIC_TOLERANCE,
                    threshold=0.10,
                ),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.citations_received": [100],
                "crossref.publication.citations_received": [150],  # 50% diff
            }
        )

        _, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.warned == 1


class TestQuarantine:
    """Tests for quarantine logic with multiple enrichers."""

    def test_two_enricher_errors_triggers_quarantine(self):
        """2+ enrichers with ENRICHER_ERROR -> quarantine seed record."""
        pairing_cr = _make_pairing(
            enricher="crossref_publication",
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            ),
        )
        pairing_oa = _make_pairing(
            enricher="openalex_publication",
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            ),
        )
        config = _make_config(
            pairings=(pairing_cr, pairing_oa),
            quarantine_threshold=2,
        )
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": ["WRONG1"],  # mismatch
                "crossref.publication.volume": ["WRONG2"],  # mismatch -> ENRICHER_ERROR
                "chembl.publication.volume": ["1"],
                "openalex.publication.doi": ["WRONG3"],  # mismatch
                "openalex.publication.volume": ["WRONG4"],  # mismatch -> ENRICHER_ERROR
            }
        )

        result_df, stats = validator.validate(
            df,
            ["crossref_publication", "openalex_publication"],
            "chembl_publication",
        )

        assert stats.quarantined == 1
        assert result_df["_cv_quarantine"][0] is True

    def test_one_enricher_error_no_quarantine(self):
        """Only 1 enricher with ENRICHER_ERROR -> no quarantine."""
        pairing_cr = _make_pairing(
            enricher="crossref_publication",
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            ),
        )
        pairing_oa = _make_pairing(
            enricher="openalex_publication",
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
            ),
        )
        config = _make_config(
            pairings=(pairing_cr, pairing_oa),
            quarantine_threshold=2,
        )
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": ["WRONG1"],
                "crossref.publication.volume": ["WRONG2"],  # 2 mismatches -> error
                "chembl.publication.volume": ["1"],
                "openalex.publication.doi": ["10.1/a"],  # matches -> PASS
            }
        )

        result_df, stats = validator.validate(
            df,
            ["crossref_publication", "openalex_publication"],
            "chembl_publication",
        )

        assert stats.quarantined == 0
        assert result_df["_cv_quarantine"][0] is False


class TestNullifyEnricherColumns:
    """Tests for enricher column nullification on ENRICHER_ERROR."""

    def test_only_enricher_columns_nullified(self):
        """Only the errored enricher's columns should be nullified."""
        pairing = _make_pairing(
            enricher="crossref_publication",
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            ),
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "chembl.publication.volume": ["1"],
                "crossref.publication.doi": ["WRONG"],  # mismatch 1
                "crossref.publication.volume": ["WRONG"],  # mismatch 2 -> ERROR
                "crossref.publication.title": ["Some Title"],  # should be nullified
            }
        )

        result_df, _ = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        # Seed columns untouched
        assert result_df["chembl.publication.doi"][0] == "10.1/a"
        assert result_df["chembl.publication.volume"][0] == "1"
        # All crossref columns nullified
        assert result_df["crossref.publication.doi"][0] is None
        assert result_df["crossref.publication.volume"][0] is None
        assert result_df["crossref.publication.title"][0] is None


class TestParsePipeline:
    """Tests for pipeline name parsing."""

    def test_valid_pipeline(self):
        result = EnrichmentCrossValidator._parse_pipeline("chembl_publication")
        assert result == ("chembl", "publication")

    def test_invalid_pipeline_no_underscore(self):
        with pytest.raises(ValueError, match="must be in format"):
            EnrichmentCrossValidator._parse_pipeline("chemblpublication")

    def test_pipeline_with_multiple_underscores(self):
        result = EnrichmentCrossValidator._parse_pipeline(
            "semantic_scholar_publication"
        )
        assert result == ("semantic", "scholar_publication")


class TestMissingColumns:
    """Tests for behavior when expected columns are missing."""

    def test_missing_column_skipped(self):
        """Missing column should be skipped, not cause error."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(
                    field_name="nonexistent", method=ComparisonMethod.EXACT
                ),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": ["10.1/a"],
            }
        )

        _, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.passed == 1


class TestSkipComparisonMethod:
    """Tests for SKIP comparison method."""

    def test_skip_method_not_compared(self):
        """Fields with SKIP method should not be compared."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(
                    field_name="abstract", method=ComparisonMethod.SKIP
                ),
            )
        )
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": ["10.1/a"],
                "chembl.publication.abstract": ["Abstract A"],
                "crossref.publication.abstract": [
                    "Totally different"
                ],  # would mismatch
            }
        )

        _, stats = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert stats.passed == 1  # abstract not counted


class TestEnricherWithoutPairing:
    """Tests for enrichers without configured pairings."""

    def test_enricher_without_pairing_skipped(self):
        """Enricher with no configured pairing should be silently skipped."""
        pairing = _make_pairing(enricher="crossref_publication")
        config = _make_config(pairings=(pairing,))
        logger = _make_logger()
        validator = EnrichmentCrossValidator(config, logger)

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": ["10.1/a"],
                "pubmed.publication.doi": ["10.1/WRONG"],  # no pairing for pubmed
            }
        )

        _, stats = validator.validate(
            df,
            ["crossref_publication", "pubmed_publication"],
            "chembl_publication",
        )

        # Only crossref validated (1 enricher stats)
        assert len(stats.enricher_stats) == 1
        assert stats.enricher_stats[0].enricher == "crossref_publication"


class TestCvDetailsColumn:
    """Tests for _cv_details per-record mismatch detail column."""

    def test_no_mismatches_gives_null_details(self):
        """All records match -> _cv_details is null for all rows."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
            )
        )
        config = _make_config(pairings=(pairing,))
        validator = EnrichmentCrossValidator(config, _make_logger())

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a", "10.1/b"],
                "crossref.publication.doi": ["10.1/a", "10.1/b"],
            }
        )

        result_df, _ = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert "_cv_details" in result_df.columns
        assert result_df["_cv_details"][0] is None
        assert result_df["_cv_details"][1] is None

    def test_single_field_mismatch_in_details(self):
        """One mismatch -> _cv_details contains enricher and field name."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            )
        )
        config = _make_config(pairings=(pairing,))
        validator = EnrichmentCrossValidator(config, _make_logger())

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": ["10.1/a"],
                "chembl.publication.volume": ["1"],
                "crossref.publication.volume": ["WRONG"],
            }
        )

        result_df, _ = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        details = json.loads(result_df["_cv_details"][0])
        assert len(details) == 1
        assert details[0]["enricher"] == "crossref_publication"
        assert details[0]["field_mismatches"] == ["volume"]

    def test_multiple_field_mismatches_in_details(self):
        """Multiple mismatches -> all fields listed in details."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
                FieldComparisonSpec(field_name="issue", method=ComparisonMethod.EXACT),
            )
        )
        config = _make_config(pairings=(pairing,))
        validator = EnrichmentCrossValidator(config, _make_logger())

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": ["WRONG"],
                "chembl.publication.volume": ["1"],
                "crossref.publication.volume": ["WRONG"],
                "chembl.publication.issue": ["5"],
                "crossref.publication.issue": ["5"],  # matches
            }
        )

        result_df, _ = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        details = json.loads(result_df["_cv_details"][0])
        assert details[0]["enricher"] == "crossref_publication"
        assert sorted(details[0]["field_mismatches"]) == ["doi", "volume"]

    def test_multiple_enrichers_in_details(self):
        """Mismatches from multiple enrichers -> multiple entries in array."""
        pairing_cr = _make_pairing(
            enricher="crossref_publication",
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
            ),
        )
        pairing_oa = _make_pairing(
            enricher="openalex_publication",
            fields=(
                FieldComparisonSpec(field_name="volume", method=ComparisonMethod.EXACT),
            ),
        )
        config = _make_config(pairings=(pairing_cr, pairing_oa))
        validator = EnrichmentCrossValidator(config, _make_logger())

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a"],
                "crossref.publication.doi": ["WRONG"],
                "chembl.publication.volume": ["1"],
                "openalex.publication.volume": ["WRONG"],
            }
        )

        result_df, _ = validator.validate(
            df,
            ["crossref_publication", "openalex_publication"],
            "chembl_publication",
        )

        details = json.loads(result_df["_cv_details"][0])
        assert len(details) == 2
        enrichers = {d["enricher"] for d in details}
        assert enrichers == {"crossref_publication", "openalex_publication"}

    def test_mixed_rows_some_null_some_with_details(self):
        """Some rows match, some don't -> mixed null/detail values."""
        pairing = _make_pairing(
            fields=(
                FieldComparisonSpec(field_name="doi", method=ComparisonMethod.EXACT),
            )
        )
        config = _make_config(pairings=(pairing,))
        validator = EnrichmentCrossValidator(config, _make_logger())

        df = pl.DataFrame(
            {
                "chembl.publication.doi": ["10.1/a", "10.1/b", "10.1/c"],
                "crossref.publication.doi": ["10.1/a", "WRONG", "10.1/c"],
            }
        )

        result_df, _ = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert result_df["_cv_details"][0] is None  # match
        assert result_df["_cv_details"][1] is not None  # mismatch
        assert result_df["_cv_details"][2] is None  # match

        details = json.loads(result_df["_cv_details"][1])
        assert details[0]["field_mismatches"] == ["doi"]

    def test_disabled_cv_has_no_details_column(self):
        """When CV is disabled, _cv_details column should not be added."""
        config = _make_config(enabled=False)
        validator = EnrichmentCrossValidator(config, _make_logger())

        df = pl.DataFrame({"a": [1]})
        result_df, _ = validator.validate(
            df, ["crossref_publication"], "chembl_publication"
        )

        assert "_cv_details" not in result_df.columns
