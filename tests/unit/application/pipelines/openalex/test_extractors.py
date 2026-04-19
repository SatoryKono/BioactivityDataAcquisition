"""Unit tests for OpenAlex field extractors.

Tests the pure functions in extractors.py module.
"""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.openalex.extractors import (
    extract_affiliations,
    extract_author_ids,
    extract_author_orcids,
    extract_authors,
    extract_biblio_info,
    extract_doi,
    extract_external_ids,
    extract_grants,
    extract_institution_country_codes,
    extract_institution_ids,
    extract_journal_info,
    extract_keywords,
    extract_mesh_terms,
    extract_open_access_info,
    extract_openalex_id,
    extract_primary_topic,
    extract_topics,
    reconstruct_abstract,
)

LEGACY_HTTP_DOI = "http" + "://doi.org/10.1016/j.cell.2024.01.005"
LEGACY_HTTP_ORCID = "http" + "://orcid.org/0000-0001-2345-6789"


class TestExtractDoi:
    """Tests for extract_doi function."""

    def test_extract_doi_from_full_url(self) -> None:
        """Should extract DOI from https://doi.org/ URL."""
        result = extract_doi("https://doi.org/10.1038/s41586-024-07487-w")
        assert result == "10.1038/s41586-024-07487-w"

    def test_extract_doi_from_http_url(self) -> None:
        """Should extract DOI from a legacy HTTP DOI URL."""
        result = extract_doi(LEGACY_HTTP_DOI)
        assert result == "10.1016/j.cell.2024.01.005"

    def test_extract_doi_from_doi_prefix(self) -> None:
        """Should extract DOI from doi: prefix."""
        result = extract_doi("doi:10.1126/science.abc1234")
        assert result == "10.1126/science.abc1234"

    def test_extract_doi_bare_doi(self) -> None:
        """Should return bare DOI unchanged."""
        result = extract_doi("10.1001/jama.2024.0001")
        assert result == "10.1001/jama.2024.0001"

    def test_extract_doi_none(self) -> None:
        """Should return None for None input."""
        result = extract_doi(None)
        assert result is None

    def test_extract_doi_empty_string(self) -> None:
        """Should return None for empty input."""
        result = extract_doi("")
        assert result is None


class TestExtractOpenalexId:
    """Tests for extract_openalex_id function."""

    def test_extract_id_from_full_url(self) -> None:
        """Should extract ID from full OpenAlex URL."""
        result = extract_openalex_id("https://openalex.org/W2148763428")
        assert result == "W2148763428"

    def test_extract_id_bare_id(self) -> None:
        """Should return bare ID unchanged."""
        result = extract_openalex_id("W2148763428")
        assert result == "W2148763428"

    def test_extract_id_none(self) -> None:
        """Should return None for None input."""
        result = extract_openalex_id(None)
        assert result is None


class TestExtractAuthors:
    """Tests for extract_authors function."""

    def test_extract_authors_with_display_names(self) -> None:
        """Should extract author display names from authorships."""
        authorships = [
            {"author": {"display_name": "John Doe", "id": "A123"}},
            {"author": {"display_name": "Jane Smith", "id": "A456"}},
        ]
        result = extract_authors(authorships)
        assert result == ["John Doe", "Jane Smith"]

    def test_extract_authors_empty_list(self) -> None:
        """Should return empty list for empty authorships."""
        result = extract_authors([])
        assert result == []

    def test_extract_authors_missing_display_name(self) -> None:
        """Should skip authorships without display_name."""
        authorships = [
            {"author": {"id": "A123"}},  # No display_name
            {"author": {"display_name": "Jane Smith"}},
        ]
        result = extract_authors(authorships)
        assert result == ["Jane Smith"]

    def test_extract_authors_with_whitespace(self) -> None:
        """Should strip whitespace from author names."""
        authorships = [
            {"author": {"display_name": "  John Doe  "}},
        ]
        result = extract_authors(authorships)
        assert result == ["John Doe"]

    def test_extract_authors_invalid_structure(self) -> None:
        """Should handle invalid authorship structure gracefully."""
        authorships = [
            {"author": None},  # Invalid author
            {"not_author": {}},  # Missing author key
            {"author": "string"},  # Invalid type
        ]
        result = extract_authors(authorships)
        assert result == []


class TestExtractAuthorIds:
    """Tests for extract_author_ids function."""

    def test_extract_author_ids_from_urls(self) -> None:
        """Should extract author IDs from full OpenAlex URLs."""
        authorships = [
            {"author": {"id": "https://openalex.org/A1234567890"}},
            {"author": {"id": "https://openalex.org/A9876543210"}},
        ]
        result = extract_author_ids(authorships)
        assert result == ["A1234567890", "A9876543210"]

    def test_extract_author_ids_preserves_order(self) -> None:
        """Should preserve order and return same length as input."""
        authorships = [
            {"author": {"id": "https://openalex.org/A1234567890"}},
            {"author": {"id": None}},
            {"author": {"id": "https://openalex.org/A9876543210"}},
        ]
        result = extract_author_ids(authorships)
        assert len(result) == 3
        assert result == ["A1234567890", "", "A9876543210"]

    def test_extract_author_ids_none_value(self) -> None:
        """Should return empty string for None ID."""
        authorships = [
            {"author": {"display_name": "John Doe", "id": None}},
        ]
        result = extract_author_ids(authorships)
        assert result == [""]

    def test_extract_author_ids_missing_id_field(self) -> None:
        """Should return empty string when id field is missing."""
        authorships = [
            {"author": {"display_name": "John Doe"}},
        ]
        result = extract_author_ids(authorships)
        assert result == [""]

    def test_extract_author_ids_bare_id(self) -> None:
        """Should handle bare ID without URL prefix."""
        authorships = [
            {"author": {"id": "A1234567890"}},
        ]
        result = extract_author_ids(authorships)
        assert result == ["A1234567890"]

    def test_extract_author_ids_empty_list(self) -> None:
        """Should return empty list for empty authorships."""
        result = extract_author_ids([])
        assert result == []

    def test_extract_author_ids_invalid_author_structure(self) -> None:
        """Should return empty string for invalid author structure."""
        authorships = [
            {"author": None},
            {"author": "string"},
            {"not_author": {}},
        ]
        result = extract_author_ids(authorships)
        assert result == ["", "", ""]

    def test_extract_author_ids_empty_string(self) -> None:
        """Should return empty string for empty URL."""
        authorships = [
            {"author": {"id": ""}},
        ]
        result = extract_author_ids(authorships)
        assert result == [""]


class TestExtractAuthorOrcids:
    """Tests for extract_author_orcids function."""

    def test_extract_orcids_from_urls(self) -> None:
        """Should extract ORCID IDs from full URLs."""
        authorships = [
            {"author": {"orcid": "https://orcid.org/0000-0001-2345-6789"}},
            {"author": {"orcid": "https://orcid.org/0000-0002-3456-789X"}},
        ]
        result = extract_author_orcids(authorships)
        assert result == ["0000-0001-2345-6789", "0000-0002-3456-789X"]

    def test_extract_orcids_preserves_order(self) -> None:
        """Should preserve order and return same length as input."""
        authorships = [
            {"author": {"orcid": "https://orcid.org/0000-0001-2345-6789"}},
            {"author": {"orcid": None}},
            {"author": {"orcid": "https://orcid.org/0000-0003-4567-8901"}},
        ]
        result = extract_author_orcids(authorships)
        assert len(result) == 3
        assert result == ["0000-0001-2345-6789", "", "0000-0003-4567-8901"]

    def test_extract_orcids_none_value(self) -> None:
        """Should return empty string for None ORCID."""
        authorships = [
            {"author": {"display_name": "John Doe", "orcid": None}},
        ]
        result = extract_author_orcids(authorships)
        assert result == [""]

    def test_extract_orcids_missing_orcid_field(self) -> None:
        """Should return empty string when orcid field is missing."""
        authorships = [
            {"author": {"display_name": "John Doe"}},  # No orcid field
        ]
        result = extract_author_orcids(authorships)
        assert result == [""]

    def test_extract_orcids_invalid_format(self) -> None:
        """Should return empty string for invalid ORCID format."""
        authorships = [
            {"author": {"orcid": "https://orcid.org/invalid-orcid"}},
            {"author": {"orcid": "https://orcid.org/0000-0001"}},  # Too short
            {"author": {"orcid": "not-a-url"}},
        ]
        result = extract_author_orcids(authorships)
        assert result == ["", "", ""]

    def test_extract_orcids_http_url(self) -> None:
        """Should handle legacy HTTP URLs (not just HTTPS)."""
        authorships = [
            {"author": {"orcid": LEGACY_HTTP_ORCID}},
        ]
        result = extract_author_orcids(authorships)
        assert result == ["0000-0001-2345-6789"]

    def test_extract_orcids_bare_orcid(self) -> None:
        """Should handle bare ORCID without URL prefix."""
        authorships = [
            {"author": {"orcid": "0000-0001-2345-6789"}},
        ]
        result = extract_author_orcids(authorships)
        assert result == ["0000-0001-2345-6789"]

    def test_extract_orcids_empty_list(self) -> None:
        """Should return empty list for empty authorships."""
        result = extract_author_orcids([])
        assert result == []

    def test_extract_orcids_invalid_author_structure(self) -> None:
        """Should return empty string for invalid author structure."""
        authorships = [
            {"author": None},
            {"author": "string"},
            {"not_author": {}},
        ]
        result = extract_author_orcids(authorships)
        assert result == ["", "", ""]

    def test_extract_orcids_with_checksum_x(self) -> None:
        """Should accept ORCID with X checksum digit."""
        authorships = [
            {"author": {"orcid": "https://orcid.org/0000-0002-1825-009X"}},
        ]
        result = extract_author_orcids(authorships)
        assert result == ["0000-0002-1825-009X"]

    def test_extract_orcids_empty_string_url(self) -> None:
        """Should return empty string for empty URL."""
        authorships = [
            {"author": {"orcid": ""}},
        ]
        result = extract_author_orcids(authorships)
        assert result == [""]


class TestExtractAffiliations:
    """Tests for extract_affiliations function."""

    def test_extract_affiliations_basic(self) -> None:
        """Should extract unique affiliations."""
        authorships = [
            {
                "author": {"display_name": "John Doe"},
                "institutions": [{"display_name": "Harvard University"}],
            },
            {
                "author": {"display_name": "Jane Smith"},
                "institutions": [{"display_name": "MIT"}],
            },
        ]
        result = extract_affiliations(authorships)
        assert result == ["Harvard University", "MIT"]

    def test_extract_affiliations_multiple_per_author(self) -> None:
        """Should extract all affiliations for an author."""
        authorships = [
            {
                "author": {"display_name": "John Doe"},
                "institutions": [
                    {"display_name": "Harvard University"},
                    {"display_name": "Broad Institute"},
                ],
            }
        ]
        result = extract_affiliations(authorships)
        # Sorted
        assert result == ["Broad Institute", "Harvard University"]

    def test_extract_affiliations_deduplication(self) -> None:
        """Should deduplicate affiliations across authors."""
        authorships = [
            {
                "author": {"display_name": "John Doe"},
                "institutions": [{"display_name": "Harvard University"}],
            },
            {
                "author": {"display_name": "Jane Smith"},
                "institutions": [{"display_name": "Harvard University"}],
            },
        ]
        result = extract_affiliations(authorships)
        assert result == ["Harvard University"]

    def test_extract_affiliations_empty(self) -> None:
        """Should return empty list if no authorships."""
        result = extract_affiliations([])
        assert result == []

    def test_extract_affiliations_no_institutions(self) -> None:
        """Should skip authors without institutions."""
        authorships = [
            {"author": {"display_name": "John Doe"}, "institutions": []},
            {"author": {"display_name": "Jane Smith"}},
        ]
        result = extract_affiliations(authorships)
        assert result == []


class TestExtractInstitutionIds:
    """Tests for extract_institution_ids function."""

    def test_extract_institution_ids_basic(self) -> None:
        """Should extract unique institution IDs from authorships."""
        authorships = [
            {
                "author": {"display_name": "John Doe"},
                "institutions": [
                    {
                        "id": "https://openalex.org/I1234567890",
                        "display_name": "Harvard",
                    },
                    {"id": "https://openalex.org/I9876543210", "display_name": "MIT"},
                ],
            },
        ]
        result = extract_institution_ids(authorships)
        assert result == ["I1234567890", "I9876543210"]

    def test_extract_institution_ids_deduplication(self) -> None:
        """Should deduplicate institution IDs across authors."""
        authorships = [
            {
                "author": {"display_name": "John Doe"},
                "institutions": [
                    {
                        "id": "https://openalex.org/I1234567890",
                        "display_name": "Harvard",
                    },
                ],
            },
            {
                "author": {"display_name": "Jane Smith"},
                "institutions": [
                    {
                        "id": "https://openalex.org/I1234567890",
                        "display_name": "Harvard",
                    },
                ],
            },
        ]
        result = extract_institution_ids(authorships)
        assert result == ["I1234567890"]

    def test_extract_institution_ids_bare_id(self) -> None:
        """Should handle bare institution ID (no URL)."""
        authorships = [
            {
                "institutions": [{"id": "I1234567890", "display_name": "Harvard"}],
            },
        ]
        result = extract_institution_ids(authorships)
        assert result == ["I1234567890"]

    def test_extract_institution_ids_empty(self) -> None:
        """Should return empty list for empty authorships."""
        result = extract_institution_ids([])
        assert result == []

    def test_extract_institution_ids_no_institutions(self) -> None:
        """Should handle authorships without institutions."""
        authorships = [
            {"author": {"display_name": "John Doe"}},
        ]
        result = extract_institution_ids(authorships)
        assert result == []

    def test_extract_institution_ids_missing_id(self) -> None:
        """Should skip institutions without id field."""
        authorships = [
            {
                "institutions": [
                    {"display_name": "Harvard"},  # No id
                    {"id": "https://openalex.org/I1234567890", "display_name": "MIT"},
                ],
            },
        ]
        result = extract_institution_ids(authorships)
        assert result == ["I1234567890"]

    def test_extract_institution_ids_invalid_structure(self) -> None:
        """Should handle invalid institutions structure gracefully."""
        authorships = [
            {"institutions": "not_a_list"},
            {
                "institutions": [
                    {"id": "https://openalex.org/I123", "display_name": "Valid"}
                ]
            },
        ]
        result = extract_institution_ids(authorships)
        assert result == ["I123"]


class TestExtractInstitutionCountryCodes:
    """Tests for extract_institution_country_codes function."""

    def test_extract_country_codes_basic(self) -> None:
        """Should extract unique country codes from authorships."""
        authorships = [
            {
                "institutions": [
                    {"display_name": "Harvard", "country_code": "US"},
                    {"display_name": "Oxford", "country_code": "GB"},
                ],
            },
        ]
        result = extract_institution_country_codes(authorships)
        assert result == ["GB", "US"]  # Sorted

    def test_extract_country_codes_uppercase(self) -> None:
        """Should normalize country codes to uppercase."""
        authorships = [
            {
                "institutions": [
                    {"display_name": "Harvard", "country_code": "us"},
                    {"display_name": "Oxford", "country_code": "gb"},
                ],
            },
        ]
        result = extract_institution_country_codes(authorships)
        assert result == ["GB", "US"]

    def test_extract_country_codes_deduplication(self) -> None:
        """Should deduplicate country codes."""
        authorships = [
            {
                "institutions": [
                    {"display_name": "Harvard", "country_code": "US"},
                    {"display_name": "MIT", "country_code": "US"},
                ],
            },
        ]
        result = extract_institution_country_codes(authorships)
        assert result == ["US"]

    def test_extract_country_codes_empty(self) -> None:
        """Should return empty list for empty authorships."""
        result = extract_institution_country_codes([])
        assert result == []

    def test_extract_country_codes_missing(self) -> None:
        """Should skip institutions without country_code."""
        authorships = [
            {
                "institutions": [
                    {"display_name": "Harvard"},  # No country_code
                    {"display_name": "Oxford", "country_code": "GB"},
                ],
            },
        ]
        result = extract_institution_country_codes(authorships)
        assert result == ["GB"]

    def test_extract_country_codes_invalid_structure(self) -> None:
        """Should handle invalid institutions structure gracefully."""
        authorships = [
            {"institutions": "not_a_list"},
            {"institutions": [{"display_name": "Valid", "country_code": "DE"}]},
        ]
        result = extract_institution_country_codes(authorships)
        assert result == ["DE"]


class TestExtractJournalInfo:
    """Tests for extract_journal_info function."""

    def test_extract_journal_info_complete(self) -> None:
        """Should extract all journal fields."""
        primary_location = {
            "source": {
                "display_name": "Nature",
                "issn_l": "0028-0836",
                "host_organization_name": "Springer Nature",
            }
        }
        result = extract_journal_info(primary_location)
        assert result == {
            "journal": "Nature",
            "issn": "0028-0836",
            "publisher": "Springer Nature",
        }

    def test_extract_journal_info_partial(self) -> None:
        """Should handle missing fields gracefully."""
        primary_location = {
            "source": {
                "display_name": "Nature",
            }
        }
        result = extract_journal_info(primary_location)
        assert result["journal"] == "Nature"
        assert result["issn"] is None
        assert result["publisher"] is None

    def test_extract_journal_info_none(self) -> None:
        """Should return None values for None input."""
        result = extract_journal_info(None)
        assert result == {"journal": None, "issn": None, "publisher": None}

    def test_extract_journal_info_empty_source(self) -> None:
        """Should handle empty source gracefully."""
        result = extract_journal_info({"source": None})
        assert result == {"journal": None, "issn": None, "publisher": None}


class TestReconstructAbstract:
    """Tests for reconstruct_abstract function."""

    def test_reconstruct_abstract_basic(self) -> None:
        """Should reconstruct abstract from inverted index."""
        inverted_index = {
            "This": [0],
            "is": [1],
            "a": [2],
            "test": [3],
        }
        result = reconstruct_abstract(inverted_index)
        assert result == "This is a test"

    def test_reconstruct_abstract_with_repeated_words(self) -> None:
        """Should handle words appearing multiple times."""
        inverted_index = {
            "The": [0],
            "test": [1, 4],
            "is": [2, 5],
            "a": [3],
            "good": [6],
        }
        result = reconstruct_abstract(inverted_index)
        assert result == "The test is a test is good"

    def test_reconstruct_abstract_none(self) -> None:
        """Should return None for None input."""
        result = reconstruct_abstract(None)
        assert result is None

    def test_reconstruct_abstract_empty(self) -> None:
        """Should return None for empty dict."""
        result = reconstruct_abstract({})
        assert result is None

    def test_reconstruct_abstract_invalid_positions(self) -> None:
        """Should skip invalid position values."""
        inverted_index = {
            "Valid": [0, 1],
            "invalid": ["not_int"],  # Invalid position
        }
        result = reconstruct_abstract(inverted_index)
        assert result == "Valid Valid"


class TestExtractOpenAccessInfo:
    """Tests for extract_open_access_info function."""

    def test_extract_oa_info_gold(self) -> None:
        """Should extract OA info for gold status."""
        oa = {"is_oa": True, "oa_status": "gold"}
        result = extract_open_access_info(oa)
        assert result == {"is_oa": True, "oa_status": "gold"}

    def test_extract_oa_info_closed(self) -> None:
        """Should extract OA info for closed status."""
        oa = {"is_oa": False, "oa_status": "closed"}
        result = extract_open_access_info(oa)
        assert result == {"is_oa": False, "oa_status": "closed"}

    def test_extract_oa_info_none(self) -> None:
        """Should return None values for None input."""
        result = extract_open_access_info(None)
        assert result == {"is_oa": None, "oa_status": None}

    def test_extract_oa_info_empty(self) -> None:
        """Should return None values for empty dict."""
        result = extract_open_access_info({})
        assert result == {"is_oa": None, "oa_status": None}


class TestExtractExternalIds:
    """Tests for extract_external_ids function."""

    def test_extract_external_ids_complete(self) -> None:
        """Should extract all external IDs from URLs."""
        ids = {
            "pmid": "https://pubmed.ncbi.nlm.nih.gov/32015508",
            "pmmolecule_id": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7095418",
            "mag": "3006090887",
        }
        result = extract_external_ids(ids)
        assert result == {
            "pmid": "32015508",
            "pmmolecule_id": "PMC7095418",
            "mag_id": "3006090887",
        }

    def test_extract_external_ids_pmid_only(self) -> None:
        """Should extract PMID from URL."""
        ids = {"pmid": "https://pubmed.ncbi.nlm.nih.gov/12345678"}
        result = extract_external_ids(ids)
        assert result["pmid"] == "12345678"
        assert result["pmmolecule_id"] is None
        assert result["mag_id"] is None

    def test_extract_external_ids_bare_pmid(self) -> None:
        """Should handle bare PMID (no URL)."""
        ids = {"pmid": "12345678"}
        result = extract_external_ids(ids)
        assert result["pmid"] == "12345678"

    def test_extract_external_ids_pmmolecule_id_trailing_slash(self) -> None:
        """Should handle trailing slash in PMCID URL."""
        ids = {"pmmolecule_id": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7095418/"}
        result = extract_external_ids(ids)
        assert result["pmmolecule_id"] == "PMC7095418"

    def test_extract_external_ids_mag_as_int(self) -> None:
        """Should convert MAG ID to string."""
        ids = {"mag": 3006090887}
        result = extract_external_ids(ids)
        assert result["mag_id"] == "3006090887"

    def test_extract_external_ids_none(self) -> None:
        """Should return None values for None input."""
        result = extract_external_ids(None)
        assert result == {"pmid": None, "pmmolecule_id": None, "mag_id": None}

    def test_extract_external_ids_empty(self) -> None:
        """Should return None values for empty dict."""
        result = extract_external_ids({})
        assert result == {"pmid": None, "pmmolecule_id": None, "mag_id": None}

    def test_extract_external_ids_pmid_leading_zeros(self) -> None:
        """Should strip leading zeros from PMID via PubMedId normalization."""
        ids = {"pmid": "0012345"}
        result = extract_external_ids(ids)
        assert result["pmid"] == "12345"

    def test_extract_external_ids_pmid_leading_zeros_url(self) -> None:
        """Should strip leading zeros from PMID extracted from URL."""
        ids = {"pmid": "https://pubmed.ncbi.nlm.nih.gov/0012345"}
        result = extract_external_ids(ids)
        assert result["pmid"] == "12345"

    def test_extract_external_ids_pmid_exceeds_upper_bound(self) -> None:
        """Should return None for PMID exceeding 10^10 upper bound."""
        ids = {"pmid": "10000000000"}
        result = extract_external_ids(ids)
        assert result["pmid"] is None

    def test_extract_external_ids_pmid_zero(self) -> None:
        """Should return None for zero PMID."""
        ids = {"pmid": "0"}
        result = extract_external_ids(ids)
        assert result["pmid"] is None


class TestExtractMeshTerms:
    """Tests for extract_mesh_terms function."""

    def test_extract_mesh_terms_basic(self) -> None:
        """Should extract MeSH descriptor names."""
        mesh = [
            {"descriptor_ui": "D000818", "descriptor_name": "Animals"},
            {"descriptor_ui": "D006801", "descriptor_name": "Humans"},
        ]
        result = extract_mesh_terms(mesh)
        assert result == ["Animals", "Humans"]

    def test_extract_mesh_terms_deduplication(self) -> None:
        """Should deduplicate repeated descriptors."""
        mesh = [
            {"descriptor_ui": "D000818", "descriptor_name": "Animals"},
            {"descriptor_ui": "D000818", "descriptor_name": "Animals"},  # Duplicate
            {"descriptor_ui": "D006801", "descriptor_name": "Humans"},
        ]
        result = extract_mesh_terms(mesh)
        assert result == ["Animals", "Humans"]

    def test_extract_mesh_terms_preserves_order(self) -> None:
        """Should preserve order of first occurrence."""
        mesh = [
            {"descriptor_name": "First"},
            {"descriptor_name": "Second"},
            {"descriptor_name": "First"},  # Duplicate
            {"descriptor_name": "Third"},
        ]
        result = extract_mesh_terms(mesh)
        assert result == ["First", "Second", "Third"]

    def test_extract_mesh_terms_missing_name(self) -> None:
        """Should skip terms without descriptor_name."""
        mesh = [
            {"descriptor_ui": "D000818"},  # No name
            {"descriptor_name": "Humans"},
        ]
        result = extract_mesh_terms(mesh)
        assert result == ["Humans"]

    def test_extract_mesh_terms_none(self) -> None:
        """Should return empty list for None input."""
        result = extract_mesh_terms(None)
        assert result == []

    def test_extract_mesh_terms_empty(self) -> None:
        """Should return empty list for empty list."""
        result = extract_mesh_terms([])
        assert result == []

    def test_extract_mesh_terms_invalid_structure(self) -> None:
        """Should handle invalid mesh structure gracefully."""
        mesh = [
            "not_a_dict",  # Invalid type
            {"descriptor_name": "Valid"},
        ]
        result = extract_mesh_terms(mesh)  # type: ignore[arg-type]
        assert result == ["Valid"]


class TestExtractKeywords:
    """Tests for extract_keywords function."""

    def test_extract_keywords_basic(self) -> None:
        """Should extract keyword display names."""
        keywords = [
            {
                "id": "https://openalex.org/keywords/coronavirus",
                "display_name": "Coronavirus",
            },
            {
                "id": "https://openalex.org/keywords/pandemic",
                "display_name": "Pandemic",
            },
        ]
        result = extract_keywords(keywords)
        assert result == ["Coronavirus", "Pandemic"]

    def test_extract_keywords_strips_whitespace(self) -> None:
        """Should strip whitespace from keywords."""
        keywords = [
            {"display_name": "  Coronavirus  "},
            {"display_name": "Pandemic"},
        ]
        result = extract_keywords(keywords)
        assert result == ["Coronavirus", "Pandemic"]

    def test_extract_keywords_missing_display_name(self) -> None:
        """Should skip keywords without display_name."""
        keywords = [
            {"id": "https://openalex.org/keywords/coronavirus"},  # No display_name
            {"display_name": "Pandemic"},
        ]
        result = extract_keywords(keywords)
        assert result == ["Pandemic"]

    def test_extract_keywords_none(self) -> None:
        """Should return empty list for None input."""
        result = extract_keywords(None)
        assert result == []

    def test_extract_keywords_empty(self) -> None:
        """Should return empty list for empty list."""
        result = extract_keywords([])
        assert result == []

    def test_extract_keywords_invalid_structure(self) -> None:
        """Should handle invalid keyword structure gracefully."""
        keywords = [
            "not_a_dict",  # Invalid type
            {"display_name": "Valid"},
        ]
        result = extract_keywords(keywords)  # type: ignore[arg-type]
        assert result == ["Valid"]


class TestExtractBiblioInfo:
    """Tests for extract_biblio_info function."""

    def test_extract_biblio_info_complete(self) -> None:
        """Should extract all biblio fields."""
        biblio = {
            "volume": "42",
            "issue": "3",
            "first_page": "123",
            "last_page": "145",
        }
        result = extract_biblio_info(biblio)
        assert result == {
            "volume": "42",
            "issue": "3",
            "page_first": "123",
            "page_last": "145",
        }

    def test_extract_biblio_info_partial(self) -> None:
        """Should handle missing fields gracefully."""
        biblio = {
            "volume": "42",
            "first_page": "123",
        }
        result = extract_biblio_info(biblio)
        assert result["volume"] == "42"
        assert result["issue"] is None
        assert result["page_first"] == "123"
        assert result["page_last"] is None

    def test_extract_biblio_info_none(self) -> None:
        """Should return None values for None input."""
        result = extract_biblio_info(None)
        assert result == {
            "volume": None,
            "issue": None,
            "page_first": None,
            "page_last": None,
        }

    def test_extract_biblio_info_empty(self) -> None:
        """Should return None values for empty dict."""
        result = extract_biblio_info({})
        assert result == {
            "volume": None,
            "issue": None,
            "page_first": None,
            "page_last": None,
        }

    def test_extract_biblio_info_invalid_type(self) -> None:
        """Should return None values for invalid type."""
        result = extract_biblio_info("not_a_dict")  # type: ignore[arg-type]
        assert result == {
            "volume": None,
            "issue": None,
            "page_first": None,
            "page_last": None,
        }


class TestExtractTopics:
    """Tests for extract_topics function."""

    def test_extract_topics_basic(self) -> None:
        """Should extract topics with hierarchical classification."""
        topics = [
            {
                "id": "https://openalex.org/T12345",
                "display_name": "Organic Synthesis",
                "score": 0.95,
                "subfield": {"display_name": "Organic Chemistry"},
                "field": {"display_name": "Chemistry"},
                "domain": {"display_name": "Physical Sciences"},
            }
        ]
        result = extract_topics(topics)
        assert len(result) == 1
        assert result[0]["id"] == "T12345"
        assert result[0]["display_name"] == "Organic Synthesis"
        assert result[0]["score"] == pytest.approx(0.95)
        assert result[0]["subfield"] == "Organic Chemistry"
        assert result[0]["field"] == "Chemistry"
        assert result[0]["domain"] == "Physical Sciences"

    def test_extract_topics_multiple(self) -> None:
        """Should extract multiple topics."""
        topics = [
            {
                "id": "https://openalex.org/T12345",
                "display_name": "Topic A",
                "score": 0.95,
                "subfield": {"display_name": "Subfield A"},
                "field": {"display_name": "Field A"},
                "domain": {"display_name": "Domain A"},
            },
            {
                "id": "https://openalex.org/T67890",
                "display_name": "Topic B",
                "score": 0.75,
                "subfield": {"display_name": "Subfield B"},
                "field": {"display_name": "Field B"},
                "domain": {"display_name": "Domain B"},
            },
        ]
        result = extract_topics(topics)
        assert len(result) == 2
        assert result[0]["display_name"] == "Topic A"
        assert result[1]["display_name"] == "Topic B"

    def test_extract_topics_with_limit(self) -> None:
        """Should respect max_count limit."""
        topics = [
            {
                "id": f"https://openalex.org/T{i}",
                "display_name": f"Topic{i}",
                "score": 0.9 - i * 0.05,
                "subfield": {"display_name": f"Subfield{i}"},
                "field": {"display_name": f"Field{i}"},
                "domain": {"display_name": f"Domain{i}"},
            }
            for i in range(20)
        ]
        result = extract_topics(topics, max_count=5)
        assert len(result) == 5
        assert result[0]["display_name"] == "Topic0"

    def test_extract_topics_empty(self) -> None:
        """Should return empty list for empty topics."""
        result = extract_topics([])
        assert result == []

    def test_extract_topics_none(self) -> None:
        """Should return empty list for None input."""
        result = extract_topics(None)
        assert result == []

    def test_extract_topics_missing_display_name(self) -> None:
        """Should skip topics without display_name."""
        topics = [
            {"id": "https://openalex.org/T12345", "score": 0.95},
            {
                "id": "https://openalex.org/T67890",
                "display_name": "Valid Topic",
                "score": 0.75,
            },
        ]
        result = extract_topics(topics)
        assert len(result) == 1
        assert result[0]["display_name"] == "Valid Topic"

    def test_extract_topics_missing_hierarchy(self) -> None:
        """Should handle missing hierarchy fields gracefully."""
        topics = [
            {
                "id": "https://openalex.org/T12345",
                "display_name": "Topic A",
                "score": 0.95,
                # Missing subfield, field, domain
            }
        ]
        result = extract_topics(topics)
        assert len(result) == 1
        assert result[0]["subfield"] is None
        assert result[0]["field"] is None
        assert result[0]["domain"] is None

    def test_extract_topics_bare_id(self) -> None:
        """Should handle bare topic ID (no URL)."""
        topics = [
            {
                "id": "T12345",
                "display_name": "Topic A",
                "score": 0.95,
            }
        ]
        result = extract_topics(topics)
        assert result[0]["id"] == "T12345"

    def test_extract_topics_strips_whitespace(self) -> None:
        """Should strip whitespace from topic names."""
        topics = [
            {
                "id": "T12345",
                "display_name": "  Topic A  ",
                "score": 0.95,
            }
        ]
        result = extract_topics(topics)
        assert result[0]["display_name"] == "Topic A"

    def test_extract_topics_missing_score(self) -> None:
        """Should default score to 0.0 if missing."""
        topics = [
            {
                "id": "T12345",
                "display_name": "Topic A",
                # Missing score
            }
        ]
        result = extract_topics(topics)
        assert result[0]["score"] == pytest.approx(0.0)


class TestExtractPrimaryTopic:
    """Tests for extract_primary_topic function."""

    def test_extract_primary_topic_basic(self) -> None:
        """Should extract primary topic with hierarchical classification."""
        primary_topic = {
            "id": "https://openalex.org/T12345",
            "display_name": "Organic Synthesis",
            "score": 0.95,
            "subfield": {"display_name": "Organic Chemistry"},
            "field": {"display_name": "Chemistry"},
            "domain": {"display_name": "Physical Sciences"},
        }
        result = extract_primary_topic(primary_topic)
        assert result is not None
        assert result["id"] == "T12345"
        assert result["display_name"] == "Organic Synthesis"
        assert result["score"] == pytest.approx(0.95)
        assert result["subfield"] == "Organic Chemistry"
        assert result["field"] == "Chemistry"
        assert result["domain"] == "Physical Sciences"

    def test_extract_primary_topic_none(self) -> None:
        """Should return None for None input."""
        result = extract_primary_topic(None)
        assert result is None

    def test_extract_primary_topic_empty(self) -> None:
        """Should return None for empty dict."""
        result = extract_primary_topic({})
        assert result is None

    def test_extract_primary_topic_missing_display_name(self) -> None:
        """Should return None if display_name is missing."""
        primary_topic = {
            "id": "https://openalex.org/T12345",
            "score": 0.95,
        }
        result = extract_primary_topic(primary_topic)
        assert result is None

    def test_extract_primary_topic_missing_hierarchy(self) -> None:
        """Should handle missing hierarchy fields gracefully."""
        primary_topic = {
            "id": "https://openalex.org/T12345",
            "display_name": "Topic A",
            "score": 0.95,
        }
        result = extract_primary_topic(primary_topic)
        assert result is not None
        assert result["subfield"] is None
        assert result["field"] is None
        assert result["domain"] is None

    def test_extract_primary_topic_strips_whitespace(self) -> None:
        """Should strip whitespace from topic name."""
        primary_topic = {
            "id": "T12345",
            "display_name": "  Topic A  ",
            "score": 0.95,
        }
        result = extract_primary_topic(primary_topic)
        assert result is not None
        assert result["display_name"] == "Topic A"


class TestExtractGrants:
    """Tests for extract_grants function."""

    def test_extract_grants_basic(self) -> None:
        """Should extract grant information."""
        grants = [
            {
                "funder": "https://openalex.org/F1234567",
                "funder_display_name": "National Institutes of Health",
                "award_id": "R01-GM123456",
            }
        ]
        result = extract_grants(grants)
        assert len(result) == 1
        assert result[0]["funder"] == "F1234567"
        assert result[0]["funder_display_name"] == "National Institutes of Health"
        assert result[0]["award_id"] == "R01-GM123456"

    def test_extract_grants_multiple(self) -> None:
        """Should extract multiple grants."""
        grants = [
            {
                "funder": "https://openalex.org/F1234567",
                "funder_display_name": "NIH",
                "award_id": "R01-123",
            },
            {
                "funder": "https://openalex.org/F7654321",
                "funder_display_name": "NSF",
                "award_id": "NSF-456",
            },
        ]
        result = extract_grants(grants)
        assert len(result) == 2
        assert result[0]["funder_display_name"] == "NIH"
        assert result[1]["funder_display_name"] == "NSF"

    def test_extract_grants_no_award_id(self) -> None:
        """Should handle missing award_id."""
        grants = [
            {
                "funder": "https://openalex.org/F1234567",
                "funder_display_name": "NIH",
                # Missing award_id
            }
        ]
        result = extract_grants(grants)
        assert len(result) == 1
        assert result[0]["award_id"] is None

    def test_extract_grants_empty(self) -> None:
        """Should return empty list for empty grants."""
        result = extract_grants([])
        assert result == []

    def test_extract_grants_none(self) -> None:
        """Should return empty list for None input."""
        result = extract_grants(None)
        assert result == []

    def test_extract_grants_missing_funder_name(self) -> None:
        """Should skip grants without funder_display_name."""
        grants = [
            {"funder": "https://openalex.org/F1234567"},  # No funder_display_name
            {"funder": "https://openalex.org/F7654321", "funder_display_name": "NSF"},
        ]
        result = extract_grants(grants)
        assert len(result) == 1
        assert result[0]["funder_display_name"] == "NSF"

    def test_extract_grants_bare_funder_id(self) -> None:
        """Should handle bare funder ID (no URL)."""
        grants = [
            {
                "funder": "F1234567",
                "funder_display_name": "NIH",
            }
        ]
        result = extract_grants(grants)
        assert result[0]["funder"] == "F1234567"

    def test_extract_grants_strips_whitespace(self) -> None:
        """Should strip whitespace from funder name and award_id."""
        grants = [
            {
                "funder": "F1234567",
                "funder_display_name": "  NIH  ",
                "award_id": "  R01-123  ",
            }
        ]
        result = extract_grants(grants)
        assert result[0]["funder_display_name"] == "NIH"
        assert result[0]["award_id"] == "R01-123"

    def test_extract_grants_invalid_structure(self) -> None:
        """Should handle invalid grant structure gracefully."""
        grants = [
            "not_a_dict",  # Invalid type
            {"funder": "F1", "funder_display_name": "Valid"},
        ]
        result = extract_grants(grants)  # type: ignore[arg-type]
        assert len(result) == 1
        assert result[0]["funder_display_name"] == "Valid"
