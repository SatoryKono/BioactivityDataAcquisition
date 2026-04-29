"""Unit tests for UniProt domain entities — UniprotTarget and IDMappingResult."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.entities.uniprot import IDMappingResult, UniprotTarget

BASE_KWARGS = {
    "entity_id": "uniprot:test:001",
    "content_hash": "hash123",
    "run_id": "run-001",
    "run_type": "incremental",
    "ingestion_ts": datetime(2024, 1, 1, tzinfo=UTC),
    "_index": 0,
}


@pytest.mark.unit
class TestUniprotTarget:
    """Tests for UniprotTarget domain entity."""

    def test_valid_creation_minimal(self) -> None:
        t = UniprotTarget(
            **BASE_KWARGS,
            accession="P00742",
            entry_name="FA10_HUMAN",
        )
        assert t.accession == "P00742"
        assert t.entry_name == "FA10_HUMAN"
        assert t.reviewed is False
        assert t.gene_primary is None

    def test_valid_creation_full(self) -> None:
        t = UniprotTarget(
            **BASE_KWARGS,
            accession="P00742",
            entry_name="FA10_HUMAN",
            protein_name="Coagulation factor X",
            gene_primary="F10",
            organism_scientific="Homo sapiens",
            taxonomy_id=9606,
            reviewed=True,
            annotation_score=5,
            sequence_length=488,
        )
        assert t.protein_name == "Coagulation factor X"
        assert t.taxonomy_id == 9606
        assert t.annotation_score == 5

    def test_empty_accession_raises(self) -> None:
        with pytest.raises(ValueError, match="accession is required"):
            UniprotTarget(**BASE_KWARGS, accession="", entry_name="TEST")

    def test_empty_entry_name_raises(self) -> None:
        with pytest.raises(ValueError, match="entry_name is required"):
            UniprotTarget(**BASE_KWARGS, accession="P00742", entry_name="")

    def test_invalid_annotation_score_raises(self) -> None:
        with pytest.raises(ValueError, match="Annotation score must be 1-5"):
            UniprotTarget(
                **BASE_KWARGS,
                accession="P00742",
                entry_name="FA10",
                annotation_score=6,
            )

    def test_invalid_sequence_length_raises(self) -> None:
        with pytest.raises(ValueError, match="Sequence length must be positive"):
            UniprotTarget(
                **BASE_KWARGS,
                accession="P00742",
                entry_name="FA10",
                sequence_length=0,
            )

    @pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
    def test_valid_annotation_scores(self, score: int) -> None:
        t = UniprotTarget(
            **BASE_KWARGS,
            accession="P00742",
            entry_name="FA10",
            annotation_score=score,
        )
        assert t.annotation_score == score

    def test_immutable(self) -> None:
        t = UniprotTarget(**BASE_KWARGS, accession="P00742", entry_name="FA10")
        with pytest.raises((AttributeError, TypeError)):
            t.accession = "other"  # type: ignore[misc]


@pytest.mark.unit
class TestIDMappingResult:
    """Tests for IDMappingResult entity."""

    def test_valid_creation_not_found(self) -> None:
        r = IDMappingResult(
            **BASE_KWARGS,
            target_id="CHEMBL204",
            mapping_status="not_found",
        )
        assert r.target_id == "CHEMBL204"
        assert r.mapping_status == "not_found"
        assert r.uniprot_accession is None

    def test_valid_creation_found(self) -> None:
        r = IDMappingResult(
            **BASE_KWARGS,
            target_id="CHEMBL204",
            mapping_status="found",
            uniprot_accession="P00742",
            protein_name="Factor X",
            taxonomy_id=9606,
        )
        assert r.uniprot_accession == "P00742"
        assert r.mapping_status == "found"

    def test_empty_target_id_raises(self) -> None:
        with pytest.raises(ValueError, match="target_id is required"):
            IDMappingResult(
                **BASE_KWARGS,
                target_id="",
                mapping_status="not_found",
            )

    def test_found_without_accession_raises(self) -> None:
        with pytest.raises(ValueError):
            IDMappingResult(
                **BASE_KWARGS,
                target_id="CHEMBL204",
                mapping_status="found",
                uniprot_accession=None,
            )

    def test_multiple_without_accession_raises(self) -> None:
        with pytest.raises(ValueError):
            IDMappingResult(
                **BASE_KWARGS,
                target_id="CHEMBL204",
                mapping_status="multiple",
                uniprot_accession=None,
            )

    def test_invalid_annotation_score_raises(self) -> None:
        with pytest.raises(ValueError, match="annotation_score must be 1-5"):
            IDMappingResult(
                **BASE_KWARGS,
                target_id="CHEMBL204",
                mapping_status="not_found",
                annotation_score=0,
            )

    def test_invalid_sequence_length_raises(self) -> None:
        with pytest.raises(ValueError, match="sequence_length must be positive"):
            IDMappingResult(
                **BASE_KWARGS,
                target_id="CHEMBL204",
                mapping_status="not_found",
                sequence_length=-1,
            )

    def test_invalid_sequence_mass_raises(self) -> None:
        with pytest.raises(ValueError, match="sequence_mass must be positive"):
            IDMappingResult(
                **BASE_KWARGS,
                target_id="CHEMBL204",
                mapping_status="not_found",
                sequence_mass=0,
            )

    @pytest.mark.parametrize("status", ["found", "not_found", "error", "multiple"])
    def test_valid_mapping_statuses(self, status: str) -> None:
        kwargs = {**BASE_KWARGS, "target_id": "CHEMBL204", "mapping_status": status}
        if status in ("found", "multiple"):
            kwargs["uniprot_accession"] = "P00742"
        r = IDMappingResult(**kwargs)
        assert r.mapping_status == status
