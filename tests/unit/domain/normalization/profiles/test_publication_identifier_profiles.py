"""Publication identifier profile regression coverage."""

from __future__ import annotations

from bioetl.domain.normalization.profiles.crossref_publication import (
    CROSSREF_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.openalex_publication import (
    OPENALEX_PUBLICATION_PROFILE,
)
from bioetl.domain.normalization.profiles.semanticscholar_publication import (
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
)


def test_crossref_profile_canonicalizes_issn_collection_fields() -> None:
    issn_rule = CROSSREF_PUBLICATION_PROFILE.rule_for("issn")
    issn_list_rule = CROSSREF_PUBLICATION_PROFILE.rule_for("issn_list")
    issn_print_rule = CROSSREF_PUBLICATION_PROFILE.rule_for("issn_print")
    issn_electronic_rule = CROSSREF_PUBLICATION_PROFILE.rule_for("issn_electronic")

    assert issn_rule is not None
    assert issn_list_rule is not None
    assert issn_print_rule is not None
    assert issn_electronic_rule is not None

    assert issn_rule.apply(" ISSN:1234567X ") == "1234-567X"
    assert (
        issn_list_rule.apply(["2049-3630", "ISSN:1234567X"])
        == '["1234-567X","2049-3630"]'
    )
    assert issn_print_rule.apply("issn:1234567x") == "1234-567X"
    assert issn_electronic_rule.apply("20493630") == "2049-3630"


def test_openalex_and_semanticscholar_profiles_canonicalize_pmid_strings() -> None:
    for profile in (
        OPENALEX_PUBLICATION_PROFILE,
        SEMANTICSCHOLAR_PUBLICATION_PROFILE,
    ):
        pmid_rule = profile.rule_for("pmid")
        publication_pmid_rule = profile.rule_for("publication_pmid")
        assert pmid_rule is not None
        assert publication_pmid_rule is not None
        assert pmid_rule.apply(" PMID:0012345 ") == "12345"
        assert publication_pmid_rule.apply(12345) == "12345"
