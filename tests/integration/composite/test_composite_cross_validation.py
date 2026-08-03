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
"""Integration-style composite cross-validation without live HTTP."""

from __future__ import annotations

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

pytestmark = pytest.mark.integration


def test_composite_cross_validation_flags_field_mismatch() -> None:
    """Seed vs enricher field mismatch must produce warning/error CV counters."""
    config = CrossValidationConfig(
        enabled=True,
        warning_threshold=1,
        error_threshold=2,
        quarantine_threshold=2,
        enricher_pairings=(
            EnricherFieldPairing(
                enricher_pipeline="crossref_publication",
                fields=(
                    FieldComparisonSpec(
                        field_name="doi",
                        method=ComparisonMethod.EXACT,
                    ),
                ),
            ),
        ),
    )
    validator = EnrichmentCrossValidator(config=config, logger=MagicMock())
    merged = pl.DataFrame(
        {
            "chembl.publication.doi": ["10.1000/a"],
            "crossref.publication.doi": ["10.1000/b"],
        }
    )

    result_df, stats = validator.validate(
        merged,
        ["crossref_publication"],
        "chembl_publication",
    )

    assert stats.total_records == 1
    assert stats.warned + stats.errored >= 1
    assert "_cv_warn" in result_df.columns
    assert "_cv_error" in result_df.columns
