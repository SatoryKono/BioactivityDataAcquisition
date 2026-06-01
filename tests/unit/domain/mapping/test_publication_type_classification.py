"""Tests for unified publication type classification module."""

from __future__ import annotations

import pytest

from bioetl.domain.mapping.publication_type_classification import (
    _ENTRY_BY_SPECIFICITY,
    _PROVIDER_LOOKUPS,
    build_publication_type_classification_payload,
    classify_publication_type,
    get_classification_table_size,
    is_initialized,
    normalize_publication_classification_field,
)

pytestmark = pytest.mark.usefixtures("publication_type_classification_data")


class TestClassificationTableIntegrity:
    """Verify the classification table is well-formed."""

    def test_table_has_214_entries(self) -> None:
        assert get_classification_table_size() == 214

    def test_all_entries_have_valid_class_codes(self) -> None:
        valid_codes = {"EXP", "REV", "PEER"}
        for entry in _ENTRY_BY_SPECIFICITY:
            assert entry.class_code in valid_codes, (
                f"Invalid class_code for: {entry.unified_type}"
            )

    def test_unified_types_are_unique(self) -> None:
        types = [entry.unified_type for entry in _ENTRY_BY_SPECIFICITY]
        assert len(types) == len(set(types)), "Duplicate unified_type found"


class TestOpenAlexClassification:
    """Test OpenAlex provider lookups."""

    @pytest.mark.parametrize(
        ("raw_type", "expected_unified", "expected_class"),
        [
            ("article", "Journal Article", "EXP"),
            ("preprint", "Preprint", "EXP"),
            ("dataset", "Dataset", "EXP"),
            ("review", "Review", "REV"),
            ("book", "Book", "REV"),
            ("book-chapter", "Book Chapter", "REV"),
            ("editorial", "Editorial", "REV"),
            ("letter", "Letter", "REV"),
            ("erratum", "Erratum", "REV"),
            ("retraction", "Retraction notice", "REV"),
            ("peer-review", "Peer Review", "PEER"),
            ("other", "Other", "REV"),
            ("report", "Report", "EXP"),
            ("dissertation", "Dissertation", "EXP"),
            ("software", "Software", "EXP"),
            ("paratext", "Paratext", "REV"),
            ("libguides", "Libguides", "REV"),
            ("grant", "Grant", "REV"),
            ("standard", "Standard", "REV"),
            ("reference-entry", "Reference Entry", "REV"),
            ("database", "Database", "EXP"),
            ("supplementary-materials", "Supplementary Materials", "EXP"),
            ("report-component", "Report Component", "EXP"),
            ("book-section", "Book Section", "REV"),
        ],
    )
    def test_known_types(
        self, raw_type: str, expected_unified: str, expected_class: str
    ) -> None:
        entry = classify_publication_type("openalex", raw_type=raw_type)
        assert entry is not None
        assert entry.unified_type == expected_unified
        assert entry.class_code == expected_class

    def test_alex_classification__type_returns_none__17b407ed(self) -> None:
        assert classify_publication_type("openalex", raw_type="nonexistent") is None

    def test_alex_classification__case_insensitive__98d6b404(self) -> None:
        entry = classify_publication_type("openalex", raw_type="ARTICLE")
        assert entry is not None
        assert entry.unified_type == "Journal Article"

    def test_article_star_maps_to_conference_paper(self) -> None:
        """article* in CSV adds 'article' as additional key for Conference Paper.

        But since 'article' already maps to Journal Article (row 2, primary),
        the primary mapping wins. Conference Paper is only via 'article*' which
        doesn't override.
        """
        openalex_lookup = _PROVIDER_LOOKUPS.get("openalex", {})
        entry = openalex_lookup.get("article")
        assert entry is not None
        assert entry.unified_type == "Journal Article"


class TestCrossRefClassification:
    """Test CrossRef provider lookups."""

    @pytest.mark.parametrize(
        ("raw_type", "expected_unified", "expected_class"),
        [
            ("journal-article", "Journal Article", "EXP"),
            ("proceedings-article", "Conference Paper", "EXP"),
            ("posted-content", "Preprint", "EXP"),
            ("dataset", "Dataset", "EXP"),
            ("book", "Book", "REV"),
            ("book-chapter", "Book Chapter", "REV"),
            ("monograph", "Monograph", "REV"),
            ("edited-book", "Edited Book", "REV"),
            ("peer-review", "Peer Review", "PEER"),
            ("other", "Other", "REV"),
            ("component", "Component (figure/table/suppl)", "EXP"),
            ("journal", "Journal (container)", "REV"),
            ("journal-issue", "Journal Issue", "REV"),
            ("proceedings", "Proceedings (container)", "REV"),
            ("grant", "Grant", "REV"),
            ("standard", "Standard", "REV"),
        ],
    )
    def test_ref_classification__known_types__80ee854c(
        self, raw_type: str, expected_unified: str, expected_class: str
    ) -> None:
        entry = classify_publication_type("crossref", raw_type=raw_type)
        assert entry is not None
        assert entry.unified_type == expected_unified
        assert entry.class_code == expected_class

    def test_ref_classification__type_returns_none__ce77fb0c(self) -> None:
        assert classify_publication_type("crossref", raw_type="nonexistent") is None


class TestPubMedClassification:
    """Test PubMed provider lookups."""

    @pytest.mark.parametrize(
        ("raw_type", "expected_unified"),
        [
            ("Journal Article", "Journal Article"),
            ("Review", "Review"),
            ("Systematic Review", "Systematic Review"),
            ("Meta-Analysis", "Meta-Analysis"),
            ("Clinical Trial", "Clinical Trial"),
            ("Randomized Controlled Trial", "Randomized Controlled Trial"),
            ("Case Reports", "Case Report"),
            ("Editorial", "Editorial"),
            ("Letter", "Letter"),
            ("Practice Guideline", "Practice Guideline"),
            ("Preprint", "Preprint"),
            ("Patent", "Patent"),
            ("Published Erratum", "Erratum"),
            ("Retraction of Publication", "Retraction notice"),
            ("Observational Study", "Observational Study"),
            ("Comparative Study", "Comparative Study"),
        ],
    )
    def test_pub_med_classification__known_types__203a0fa1(self, raw_type: str, expected_unified: str) -> None:
        entry = classify_publication_type("pubmed", raw_type=raw_type)
        assert entry is not None
        assert entry.unified_type == expected_unified

    def test_pub_med_classification__case_insensitive__e2c0632b(self) -> None:
        entry = classify_publication_type("pubmed", raw_type="journal article")
        assert entry is not None
        assert entry.unified_type == "Journal Article"

    def test_multi_type_most_specific(self) -> None:
        """PubMed multi-type: should return most specific (highest specificity)."""
        types = ["Journal Article", "Randomized Controlled Trial"]
        entry = classify_publication_type("pubmed", raw_types_list=types)
        assert entry is not None
        assert entry.unified_type == "Randomized Controlled Trial"
        assert entry.specificity > 2  # More specific than Journal Article (row 2)

    def test_multi_type_with_unknown(self) -> None:
        """Unknown types should be ignored when others match."""
        types = ["UnknownType", "Clinical Trial"]
        entry = classify_publication_type("pubmed", raw_types_list=types)
        assert entry is not None
        assert entry.unified_type == "Clinical Trial"

    def test_multi_type_all_unknown(self) -> None:
        types = ["UnknownType1", "UnknownType2"]
        entry = classify_publication_type("pubmed", raw_types_list=types)
        assert entry is None

    def test_pub_med_classification__empty_list__c23d68e7(self) -> None:
        entry = classify_publication_type("pubmed", raw_types_list=[])
        assert entry is None

    def test_clinical_trial_phases_specificity(self) -> None:
        """Phase-specific clinical trial types should be more specific than generic."""
        generic = classify_publication_type("pubmed", raw_type="Clinical Trial")
        phase_iii = classify_publication_type(
            "pubmed", raw_type="Clinical Trial, Phase III"
        )
        assert generic is not None
        assert phase_iii is not None
        assert phase_iii.specificity > generic.specificity


class TestSemanticScholarClassification:
    """Test Semantic Scholar provider lookups."""

    @pytest.mark.parametrize(
        ("raw_type", "expected_unified"),
        [
            ("JournalArticle", "Journal Article"),
            ("Conference", "Conference Paper"),
            ("Review", "Review"),
            ("Editorial", "Editorial"),
            ("LettersAndComments", "Letter"),
            ("Book", "Book"),
            ("BookSection", "Book Chapter"),
            ("Dataset", "Dataset"),
            ("CaseReport", "Case Report"),
            ("Study", "Clinical Study"),
            ("ClinicalTrial", "Clinical Trial"),
            ("MetaAnalysis", "Meta-Analysis"),
            ("News", "News"),
        ],
    )
    def test_scholar_classification__known_types__5d6bfdf4(self, raw_type: str, expected_unified: str) -> None:
        entry = classify_publication_type("semanticscholar", raw_type=raw_type)
        assert entry is not None
        assert entry.unified_type == expected_unified

    def test_scholar_classification__type_most_specific__b184f49b(self) -> None:
        """S2 multi-type: should return most specific."""
        types = ["JournalArticle", "ClinicalTrial"]
        entry = classify_publication_type("semanticscholar", raw_types_list=types)
        assert entry is not None
        assert entry.unified_type == "Clinical Trial"

    def test_scholar_classification__case_insensitive__924ebb64(self) -> None:
        entry = classify_publication_type("semanticscholar", raw_type="journalarticle")
        assert entry is not None
        assert entry.unified_type == "Journal Article"

    def test_provider_aliases(self) -> None:
        """Both 'semanticscholar' and 's2' should work."""
        entry1 = classify_publication_type("semanticscholar", raw_type="JournalArticle")
        entry2 = classify_publication_type("s2", raw_type="JournalArticle")
        assert entry1 == entry2


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_raw_type(self) -> None:
        assert classify_publication_type("openalex") is None

    def test_none_raw_types_list(self) -> None:
        assert classify_publication_type("pubmed") is None

    def test_unknown_provider(self) -> None:
        assert classify_publication_type("unknown_provider", raw_type="article") is None

    def test_entry_is_frozen(self) -> None:
        entry = classify_publication_type("openalex", raw_type="article")
        assert entry is not None
        with pytest.raises(AttributeError):
            entry.unified_type = "changed"  # type: ignore[misc]

    def test_all_lookups_built(self) -> None:
        """Verify all four lookup dicts are non-empty."""
        assert len(_PROVIDER_LOOKUPS.get("openalex", {})) > 0
        assert len(_PROVIDER_LOOKUPS.get("crossref", {})) > 0
        assert len(_PROVIDER_LOOKUPS.get("pubmed", {})) > 0
        assert len(_PROVIDER_LOOKUPS.get("s2", {})) > 0

    def test_pubmed_lookup_has_all_mapped_types(self) -> None:
        """PubMed has the most mappings — verify count is reasonable."""
        assert len(_PROVIDER_LOOKUPS.get("pubmed", {})) >= 150

    def test_s2_lettesandcomments_maps_to_letter(self) -> None:
        """LettersAndComments appears in both Letter and Comment rows.

        Letter (row 46) has lower specificity than Comment (row 47).
        The first mapping wins, so 'lettersandcomments' maps to Letter.
        """
        s2_lookup = _PROVIDER_LOOKUPS.get("s2", {})
        entry = s2_lookup.get("lettersandcomments")
        assert entry is not None
        assert entry.unified_type == "Letter"


class TestPublicationTypePayload:
    """Test raw-provider and derived classification payload construction."""

    def test_default_payload_uses_explicit_raw_sidecar_field(self) -> None:
        payload = build_publication_type_classification_payload(
            "openalex",
            raw_type="article",
        )

        assert payload == {
            "publication_type_raw": "article",
            "publication_type_unified": "Journal Article",
            "publication_subclass": "Original Experimental Data",
            "publication_class": "EXP",
        }

    def test_silver_payload_can_target_publication_type_raw_contract(self) -> None:
        payload = build_publication_type_classification_payload(
            "semanticscholar",
            raw_types_list=["JournalArticle", "Review"],
            raw_field_name="publication_type",
        )

        assert payload["publication_type"] == "JournalArticle|Review"
        assert payload["publication_type_unified"] == "Review"
        assert payload["publication_class"] == "REV"

    def test_unknown_raw_provider_value_is_preserved_while_derived_fields_fail_closed(
        self,
    ) -> None:
        payload = build_publication_type_classification_payload(
            "crossref",
            raw_type="future-provider-type",
            raw_field_name="publication_type",
        )

        assert payload == {
            "publication_type": "future-provider-type",
            "publication_type_unified": None,
            "publication_subclass": None,
            "publication_class": None,
        }

    def test_unknown_raw_provider_type_list_is_preserved_without_deriving_taxonomy(
        self,
    ) -> None:
        payload = build_publication_type_classification_payload(
            "semanticscholar",
            raw_types_list=["FutureType", "NovelLabel"],
            raw_field_name="publication_type",
        )

        assert payload == {
            "publication_type": "FutureType|NovelLabel",
            "publication_type_unified": None,
            "publication_subclass": None,
            "publication_class": None,
        }

    @pytest.mark.parametrize(
        ("raw_type", "expected_unified"),
        [
            ("PUBLICATION", "Journal Article"),
            ("PATENT", "Patent"),
            ("DATASET", "Dataset"),
            ("BOOK", "Book"),
        ],
    )
    def test_chembl_native_doc_types_classify_via_unified_taxonomy(
        self, raw_type: str, expected_unified: str
    ) -> None:
        payload = build_publication_type_classification_payload(
            "chembl",
            raw_type=raw_type,
            raw_field_name="publication_type",
        )

        assert payload["publication_type"] == raw_type
        assert payload["publication_type_unified"] == expected_unified

    def test_derived_field_normalizer_is_registry_backed(self) -> None:
        assert (
            normalize_publication_classification_field(
                "publication_type_unified", "journal article"
            )
            == "Journal Article"
        )
        assert (
            normalize_publication_classification_field("publication_class", "exp")
            == "EXP"
        )
        assert (
            normalize_publication_classification_field(
                "publication_subclass", "not-a-subclass"
            )
            is None
        )


class TestInitializationGuard:
    """Tests for is_initialized() guard and idempotency."""

    def test_is_initialized_returns_true(self) -> None:
        """Session fixture guarantees initialization before tests run."""
        assert is_initialized() is True

    def test_initialize_classification_is_idempotent(self) -> None:
        """Calling initialize_classification() twice must not corrupt state."""
        from bioetl.domain.mapping.publication_type_classification import (
            initialize_classification,
        )

        size_before = get_classification_table_size()
        lookups_before = dict(_PROVIDER_LOOKUPS)

        # Re-initialize with same data (loaded by session fixture)
        from bioetl.domain.mapping.publication_type_classification import _data

        assert _data is not None
        initialize_classification(_data)

        assert get_classification_table_size() == size_before
        assert set(_PROVIDER_LOOKUPS.keys()) == set(lookups_before.keys())
        assert is_initialized() is True
