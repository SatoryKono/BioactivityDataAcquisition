# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# Entity fixture overrides use intentional wide test inputs (PD2-9).
"""Unit tests for ChEMBL Assay domain entity."""

from __future__ import annotations

from typing import Any, cast


from datetime import UTC, datetime

import pytest

from bioetl.domain.entities.chembl_activity import Assay

BASE_KWARGS = cast(Any, {
    "entity_id": "assay:test:001",
    "content_hash": "hash123",
    "run_id": "run-001",
    "run_type": "incremental",
    "ingestion_ts": datetime(2024, 1, 1, tzinfo=UTC),
    "_index": 0,
})


@pytest.mark.unit
class TestAssay:
    """Tests for Assay domain entity."""

    def test_activity_entity_assay__creation_minimal__c2e4ab6c(self) -> None:
        a = Assay(**BASE_KWARGS, assay_id="CHEMBL1000")
        assert a.assay_id == "CHEMBL1000"
        assert a.target_id is None
        assert a.confidence_score is None

    def test_valid_creation_full(self) -> None:
        a = Assay(
            **BASE_KWARGS,
            assay_id="CHEMBL1000",
            target_id="CHEMBL204",
            assay_type="B",
            assay_organism="Homo sapiens",
            confidence_score=9,
            assay_description="In vitro binding assay",
            bao_format="BAO_0000357",
        )
        assert a.assay_type == "B"
        assert a.confidence_score == 9
        assert a.assay_description == "In vitro binding assay"

    def test_empty_assay_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Assay ChEMBL ID is required"):
            Assay(**BASE_KWARGS, assay_id="")

    def test_confidence_score_too_low_raises(self) -> None:
        with pytest.raises(ValueError, match="Confidence score must be 0-9"):
            Assay(**BASE_KWARGS, assay_id="CHEMBL1", confidence_score=-1)

    def test_confidence_score_too_high_raises(self) -> None:
        with pytest.raises(ValueError, match="Confidence score must be 0-9"):
            Assay(**BASE_KWARGS, assay_id="CHEMBL1", confidence_score=10)

    @pytest.mark.parametrize("score", list(range(10)))
    def test_valid_confidence_scores(self, score: int) -> None:
        a = Assay(**BASE_KWARGS, assay_id="CHEMBL1", confidence_score=score)
        assert a.confidence_score == score

    def test_confidence_score_none_valid(self) -> None:
        a = Assay(**BASE_KWARGS, assay_id="CHEMBL1", confidence_score=None)
        assert a.confidence_score is None

    def test_variant_fields(self) -> None:
        a = Assay(
            **BASE_KWARGS,
            assay_id="CHEMBL1",
            variant_accession="P00742",
            variant_mutation="V600E",
        )
        assert a.variant_accession == "P00742"
        assert a.variant_mutation == "V600E"

    def test_activity_entity_assay__immutable__4f37321e(self) -> None:
        a = Assay(**BASE_KWARGS, assay_id="CHEMBL1")
        with pytest.raises((AttributeError, TypeError)):
            a.assay_id = "other"  # type: ignore[misc]
