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
# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
# Entity fixture overrides use intentional wide test inputs (PD2-9).
"""Unit tests for publication domain entities — CrossRef, OpenAlex, SemanticScholar, PubMed, ChEMBL."""

from __future__ import annotations

from typing import Any, cast


from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from bioetl.domain.entities.publication_base import PublicationEntityBase

BASE_KWARGS = cast(
    Any,
    {
        "entity_id": "pub:test:001",
        "content_hash": "hash123abc",
        "run_id": "run-001",
        "run_type": "incremental",
        "ingestion_ts": datetime(2024, 1, 15, tzinfo=UTC),
        "_index": 0,
    },
)


@dataclass(frozen=True, kw_only=True)
class HookValidatedPublication(PublicationEntityBase):
    """Test-only publication entity that uses the shared invariant hook."""

    provider_key: str | None = None

    def _validate_invariants(self) -> None:
        super()._validate_invariants()
        if not self.provider_key:
            raise ValueError("provider_key is required")


@pytest.mark.unit
class TestCrossRefPublicationEntity:
    """CrossRefPublicationEntity validation and immutability."""

    def test_ref_publication_entity__creation_minimal__95f45062(self) -> None:
        from bioetl.domain.entities.crossref import CrossRefPublicationEntity

        entity = CrossRefPublicationEntity(
            **BASE_KWARGS,
            doi="10.1038/nature12373",
        )
        assert entity.doi == "10.1038/nature12373"
        assert entity._source == "crossref"
        assert entity.issn == []
        assert entity.subject_keywords == []

    def test_ref_publication_entity__valid_creation_full__a6b570e0(self) -> None:
        from bioetl.domain.entities.crossref import CrossRefPublicationEntity

        entity = CrossRefPublicationEntity(
            **BASE_KWARGS,
            doi="10.1038/nature12373",
            title="Test Article",
            abstract="An abstract",
            journal="Nature",
            publisher="Springer Nature",
            volume="500",
            issue="7462",
            publication_year=2013,
            citations_received=100,
            is_oa=True,
            oa_status="gold",
            issn=["0028-0836"],
            subject_keywords=["chemistry"],
        )
        assert entity.title == "Test Article"
        assert entity.volume == "500"
        assert entity.issn == ["0028-0836"]

    def test_empty_doi_raises(self) -> None:
        from bioetl.domain.entities.crossref import CrossRefPublicationEntity

        with pytest.raises(ValueError, match="DOI is required"):
            CrossRefPublicationEntity(**BASE_KWARGS, doi="")

    def test_ref_publication_entity__immutable__3f73c957(self) -> None:
        from bioetl.domain.entities.crossref import CrossRefPublicationEntity

        entity = CrossRefPublicationEntity(**BASE_KWARGS, doi="10.1234/test")
        with pytest.raises((AttributeError, TypeError)):
            entity.doi = "other"  # type: ignore[misc]


@pytest.mark.unit
class TestOpenAlexPublicationEntity:
    """OpenAlexPublicationEntity validation and immutability."""

    def test_publication_entity__creation_minimal__45a35b4b(self) -> None:
        from bioetl.domain.entities.openalex import OpenAlexPublicationEntity

        entity = OpenAlexPublicationEntity(
            **BASE_KWARGS,
            openalex_id="W2741809807",
        )
        assert entity.openalex_id == "W2741809807"
        assert entity._source == "openalex"
        assert entity.institution_ids == []
        assert entity.grants == []

    def test_valid_creation_with_topics(self) -> None:
        from bioetl.domain.entities.openalex import OpenAlexPublicationEntity

        entity = OpenAlexPublicationEntity(
            **BASE_KWARGS,
            openalex_id="W123",
            subject_topics=[{"id": "T1", "display_name": "Chemistry", "score": 0.95}],
            primary_topic={"id": "T1", "display_name": "Chemistry", "score": 0.95},
            fwci=1.5,
            is_retracted=False,
        )
        assert len(entity.subject_topics) == 1
        assert entity.fwci == pytest.approx(1.5)
        assert entity.is_retracted is False

    def test_empty_openalex_id_raises(self) -> None:
        from bioetl.domain.entities.openalex import OpenAlexPublicationEntity

        with pytest.raises(ValueError, match="OpenAlex Publication ID is required"):
            OpenAlexPublicationEntity(**BASE_KWARGS, openalex_id="")

    def test_publication_entity__immutable__709dd0b6(self) -> None:
        from bioetl.domain.entities.openalex import OpenAlexPublicationEntity

        entity = OpenAlexPublicationEntity(**BASE_KWARGS, openalex_id="W1")
        with pytest.raises((AttributeError, TypeError)):
            entity.openalex_id = "W2"  # type: ignore[misc]


@pytest.mark.unit
class TestSemanticScholarPublicationEntity:
    """SemanticScholarPublicationEntity validation and immutability."""

    def test_publication_entity__creation_minimal__1b97c28d(self) -> None:
        from bioetl.domain.entities.semanticscholar import (
            SemanticScholarPublicationEntity,
        )

        entity = SemanticScholarPublicationEntity(
            **BASE_KWARGS,
            paper_id="a" * 40,
        )
        assert entity.paper_id == "a" * 40
        assert entity._source == "semanticscholar"

    def test_publication_entity__valid_creation_full__778cffa9(self) -> None:
        from bioetl.domain.entities.semanticscholar import (
            SemanticScholarPublicationEntity,
        )

        entity = SemanticScholarPublicationEntity(
            **BASE_KWARGS,
            paper_id="b" * 40,
            doi="10.1234/test",
            arxiv_id="2301.00001",
            corpus_id=12345,
            tldr="Summary text",
            influential_citation_count=5,
        )
        assert entity.corpus_id == 12345
        assert entity.tldr == "Summary text"

    def test_empty_paper_id_raises(self) -> None:
        from bioetl.domain.entities.semanticscholar import (
            SemanticScholarPublicationEntity,
        )

        with pytest.raises(ValueError, match="Paper ID is required"):
            SemanticScholarPublicationEntity(**BASE_KWARGS, paper_id="")


@pytest.mark.unit
class TestPubMedPublicationEntity:
    """PubMedPublicationEntity validation and immutability."""

    def test_med_publication_entity__creation_minimal__33278e4c(self) -> None:
        from bioetl.domain.entities.pubmed import PubMedPublicationEntity

        entity = PubMedPublicationEntity(
            **BASE_KWARGS,
            pmid="12345678",
        )
        assert entity.pmid == "12345678"
        assert entity._source == "pubmed"
        assert entity.publication_types == []
        assert entity.subject_keywords == []
        assert entity.subject_mesh == []

    def test_valid_creation_with_metadata(self) -> None:
        from bioetl.domain.entities.pubmed import PubMedPublicationEntity

        entity = PubMedPublicationEntity(
            **BASE_KWARGS,
            pmid="99999999",
            title="Test PubMed Article",
            journal="J Biol Chem",
            volume="296",
            issue="12",
            publication_year=2021,
            pub_month=6,
            pub_day=15,
            publication_types=["Journal Article"],
            subject_mesh=["Kinases"],
            author_count=5,
        )
        assert entity.volume == "296"
        assert entity.pub_month == 6
        assert entity.author_count == 5

    def test_empty_pmid_raises(self) -> None:
        from bioetl.domain.entities.pubmed import PubMedPublicationEntity

        with pytest.raises(ValueError, match="PMID is required"):
            PubMedPublicationEntity(**BASE_KWARGS, pmid="")


@pytest.mark.unit
class TestChemblPublication:
    """ChemblPublication validation and immutability."""

    def test_chembl_publication__creation_minimal__c28a7e2e(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublication

        entity = ChemblPublication(
            **BASE_KWARGS,
            publication_id="CHEMBL1125145",
        )
        assert entity.publication_id == "CHEMBL1125145"

    def test_chembl_publication__valid_creation_full__a68fa5d4(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublication

        entity = ChemblPublication(
            **BASE_KWARGS,
            publication_id="CHEMBL1125145",
            title="A ChEMBL Document",
            volume="10",
            issue="3",
            src_id=1,
            chembl_release="CHEMBL_34",
            creation_date="2024-01-01",
        )
        assert entity.volume == "10"
        assert entity.chembl_release == "CHEMBL_34"

    def test_chembl_publication__id_raises__3e658eef(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublication

        with pytest.raises(ValueError, match="publication_id is required"):
            ChemblPublication(**BASE_KWARGS, publication_id="")


@pytest.mark.unit
class TestPublicationInvariantHook:
    """PublicationEntityBase should participate in the centralized invariant chain."""

    def test_publication_subclass_invariants_run_without_custom_post_init(self) -> None:
        entity = HookValidatedPublication(**BASE_KWARGS, provider_key="pub-1")
        assert entity.provider_key == "pub-1"

    def test_publication_subclass_invariants_raise_without_custom_post_init(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="provider_key is required"):
            HookValidatedPublication(**BASE_KWARGS, provider_key="")
