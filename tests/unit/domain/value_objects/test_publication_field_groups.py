"""Tests for PublicationFieldGroup value objects."""

import pytest

from bioetl.domain.value_objects._publication_field_group_config import (
    DEFAULT_FIELD_GROUP_CONFIG,
    FieldGroupConfig,
)
from bioetl.domain.value_objects._publication_field_group_types import (
    FIELD_TO_GROUP_MAPPING,
    PublicationFieldGroup,
)

pytestmark = pytest.mark.unit


class TestPublicationFieldGroup:
    """Tests for PublicationFieldGroup enum."""

    def test_all_groups_defined(self) -> None:
        """All 9 semantic groups are defined."""
        assert len(PublicationFieldGroup) == 9

        expected_groups = {
            "id_and_status",
            "bibliography",
            "author_and_affiliations",
            "terms_and_keywords_and_topics",
            "citations_and_reference",
            "date_and_places",
            "publication_types",
            "system_metadata",
            "trash",
        }
        actual_groups = {g.value for g in PublicationFieldGroup}
        assert actual_groups == expected_groups

    def test_display_name(self) -> None:
        """Display names are human-readable."""
        assert PublicationFieldGroup.ID_AND_STATUS.display_name == "ID & Status"
        assert PublicationFieldGroup.BIBLIOGRAPHY.display_name == "Bibliography"
        assert (
            PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS.display_name
            == "Author & Affiliations"
        )
        assert (
            PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS.display_name
            == "Terms & Keywords & Topics"
        )
        assert (
            PublicationFieldGroup.CITATIONS_AND_REFERENCE.display_name
            == "Citations & Reference"
        )
        assert PublicationFieldGroup.DATE_AND_PLACES.display_name == "Date & Places"
        assert (
            PublicationFieldGroup.PUBLICATION_TYPES.display_name == "Publication Types"
        )
        assert PublicationFieldGroup.SYSTEM_METADATA.display_name == "System Metadata"
        assert PublicationFieldGroup.TRASH.display_name == "Trash (Excluded)"

    def test_include_in_gold(self) -> None:
        """TRASH and SYSTEM_METADATA groups are excluded from Gold layer."""
        excluded = {
            PublicationFieldGroup.TRASH,
            PublicationFieldGroup.SYSTEM_METADATA,
        }
        for group in PublicationFieldGroup:
            if group in excluded:
                assert not group.include_in_gold
            else:
                assert group.include_in_gold

    def test_gold_groups(self) -> None:
        """gold_groups() returns all groups except TRASH and SYSTEM_METADATA."""
        gold_groups = PublicationFieldGroup.gold_groups()
        assert len(gold_groups) == 7
        assert PublicationFieldGroup.TRASH not in gold_groups
        assert PublicationFieldGroup.SYSTEM_METADATA not in gold_groups

        expected = {
            PublicationFieldGroup.ID_AND_STATUS,
            PublicationFieldGroup.BIBLIOGRAPHY,
            PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS,
            PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS,
            PublicationFieldGroup.CITATIONS_AND_REFERENCE,
            PublicationFieldGroup.DATE_AND_PLACES,
            PublicationFieldGroup.PUBLICATION_TYPES,
        }
        assert set(gold_groups) == expected

    def test_excluded_groups(self) -> None:
        """excluded_groups() returns SYSTEM_METADATA and TRASH."""
        excluded = PublicationFieldGroup.excluded_groups()
        assert len(excluded) == 2
        assert PublicationFieldGroup.SYSTEM_METADATA in excluded
        assert PublicationFieldGroup.TRASH in excluded

    def test_from_string_valid(self) -> None:
        """from_string() parses valid group names."""
        assert (
            PublicationFieldGroup.from_string("id_and_status")
            == PublicationFieldGroup.ID_AND_STATUS
        )
        assert (
            PublicationFieldGroup.from_string("bibliography")
            == PublicationFieldGroup.BIBLIOGRAPHY
        )
        assert PublicationFieldGroup.from_string("TRASH") == PublicationFieldGroup.TRASH
        assert (
            PublicationFieldGroup.from_string("system_metadata")
            == PublicationFieldGroup.SYSTEM_METADATA
        )
        # Case-insensitive
        assert (
            PublicationFieldGroup.from_string("ID_AND_STATUS")
            == PublicationFieldGroup.ID_AND_STATUS
        )

    def test_from_string_invalid(self) -> None:
        """from_string() raises ValueError for invalid group names."""
        with pytest.raises(ValueError, match="Invalid field group"):
            PublicationFieldGroup.from_string("invalid_group")

        with pytest.raises(ValueError, match="Invalid field group"):
            PublicationFieldGroup.from_string("")


class TestFieldToGroupMapping:
    """Tests for FIELD_TO_GROUP_MAPPING."""

    def test_mapping_not_empty(self) -> None:
        """Mapping contains fields."""
        assert len(FIELD_TO_GROUP_MAPPING) > 0

    def test_all_groups_have_fields(self) -> None:
        """All non-trash groups have at least one field."""
        groups_with_fields = set(FIELD_TO_GROUP_MAPPING.values())

        for group in PublicationFieldGroup:
            # Skip checking if TRASH has fields (it should, but not required)
            if group != PublicationFieldGroup.TRASH:
                assert group in groups_with_fields, f"Group {group} has no fields"

    def test_id_and_status_fields(self) -> None:
        """ID & Status group contains expected identifier fields."""
        expected_fields = {
            "doi",
            "pmid",
            "pmc_id",
            "publication_id",
            "entity_id",
            "openalex_id",
            "paper_id",
            "corpus_id",
            "is_oa",
            "is_retracted",
            "dblp_id",
        }
        actual_fields = {
            f
            for f, g in FIELD_TO_GROUP_MAPPING.items()
            if g == PublicationFieldGroup.ID_AND_STATUS
        }
        assert expected_fields.issubset(actual_fields)

    def test_bibliography_fields(self) -> None:
        """Bibliography group contains expected fields."""
        expected_fields = {
            "title",
            "abstract",
            "journal",
            "volume",
            "issue",
            "page_first",
            "page_last",
            "issn",
            "publisher",
        }
        actual_fields = {
            f
            for f, g in FIELD_TO_GROUP_MAPPING.items()
            if g == PublicationFieldGroup.BIBLIOGRAPHY
        }
        assert expected_fields.issubset(actual_fields)

    def test_author_fields(self) -> None:
        """Author & Affiliations group contains expected fields."""
        expected_fields = {
            "authors",
            "affiliation_list",
            "author_count",
            "author_openalex_ids",
            "author_h_indices",
            "ror_ids",
        }
        actual_fields = {
            f
            for f, g in FIELD_TO_GROUP_MAPPING.items()
            if g == PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS
        }
        assert expected_fields.issubset(actual_fields)

    def test_terms_and_keywords_fields(self) -> None:
        """Terms & Keywords group contains expected fields."""
        expected_fields = {
            "subject_keywords",
            "subject_mesh",
            "subject_topics",
            "subject_fields",
            "primary_topic",
            "chemicals",
            "chemical_count",
            "gene_symbols",
            "databanks",
        }
        actual_fields = {
            f
            for f, g in FIELD_TO_GROUP_MAPPING.items()
            if g == PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS
        }
        assert expected_fields.issubset(actual_fields)

    def test_citation_fields(self) -> None:
        """Citations & Reference group contains expected fields."""
        expected_fields = {
            "citations_received",
            "citations_made",
            "grants",
            "grant_count",
            "influential_citation_count",
            "fwci",
            "references",
            "citation_contexts",
        }
        actual_fields = {
            f
            for f, g in FIELD_TO_GROUP_MAPPING.items()
            if g == PublicationFieldGroup.CITATIONS_AND_REFERENCE
        }
        assert expected_fields.issubset(actual_fields)

    def test_date_and_places_fields(self) -> None:
        """Date & Places group contains expected fields."""
        expected_fields = {
            "publication_year",
            "publication_date",
            "country",
            "creation_date",
            "pub_day",
        }
        actual_fields = {
            f
            for f, g in FIELD_TO_GROUP_MAPPING.items()
            if g == PublicationFieldGroup.DATE_AND_PLACES
        }
        assert expected_fields.issubset(actual_fields)

    def test_publication_types_fields(self) -> None:
        """Publication Types group contains expected fields."""
        expected_fields = {
            "publication_types",
        }
        actual_fields = {
            f
            for f, g in FIELD_TO_GROUP_MAPPING.items()
            if g == PublicationFieldGroup.PUBLICATION_TYPES
        }
        assert expected_fields.issubset(actual_fields)

    def test_trash_fields(self) -> None:
        """Trash group contains expected excluded fields."""
        expected_fields = {
            "language",
            "src_id",
        }
        actual_fields = {
            f
            for f, g in FIELD_TO_GROUP_MAPPING.items()
            if g == PublicationFieldGroup.TRASH
        }
        assert expected_fields.issubset(actual_fields)

    def test_system_metadata_fields(self) -> None:
        """System metadata group contains content_hash."""
        actual_fields = {
            f
            for f, g in FIELD_TO_GROUP_MAPPING.items()
            if g == PublicationFieldGroup.SYSTEM_METADATA
        }
        assert "content_hash" in actual_fields


class TestFieldGroupConfig:
    """Tests for FieldGroupConfig."""

    def test_get_group_unqualified(self) -> None:
        """get_group() works with unqualified field names."""
        config = FieldGroupConfig()
        assert config.get_group("title") == PublicationFieldGroup.BIBLIOGRAPHY
        assert config.get_group("doi") == PublicationFieldGroup.ID_AND_STATUS
        assert (
            config.get_group("authors") == PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS
        )

    def test_get_group_qualified(self) -> None:
        """get_group() extracts field from qualified names."""
        config = FieldGroupConfig()
        assert (
            config.get_group("chembl.publication.title")
            == PublicationFieldGroup.BIBLIOGRAPHY
        )
        assert (
            config.get_group("crossref.publication.doi")
            == PublicationFieldGroup.ID_AND_STATUS
        )
        assert (
            config.get_group("pubmed.publication.subject_mesh")
            == PublicationFieldGroup.TERMS_AND_KEYWORDS_AND_TOPICS
        )

    def test_get_group_case_insensitive(self) -> None:
        """get_group() is case-insensitive."""
        config = FieldGroupConfig()
        assert config.get_group("TITLE") == PublicationFieldGroup.BIBLIOGRAPHY
        assert config.get_group("Title") == PublicationFieldGroup.BIBLIOGRAPHY
        assert (
            config.get_group("chembl.publication.ABSTRACT")
            == PublicationFieldGroup.BIBLIOGRAPHY
        )

    def test_get_group_unknown_field(self) -> None:
        """get_group() returns default_group for unknown fields."""
        config = FieldGroupConfig()
        assert config.get_group("unknown_field") == PublicationFieldGroup.TRASH
        assert (
            config.get_group("chembl.publication.custom_field")
            == PublicationFieldGroup.TRASH
        )

    def test_get_group_custom_default(self) -> None:
        """get_group() uses custom default_group."""
        config = FieldGroupConfig(default_group=PublicationFieldGroup.ID_AND_STATUS)
        assert config.get_group("unknown_field") == PublicationFieldGroup.ID_AND_STATUS

    def test_is_gold_field(self) -> None:
        """is_gold_field() identifies Gold layer fields correctly."""
        config = FieldGroupConfig()

        # Gold fields
        assert config.is_gold_field("title") is True
        assert config.is_gold_field("doi") is True
        assert config.is_gold_field("authors") is True
        assert config.is_gold_field("chembl.publication.title") is True

        # Trash fields
        assert config.is_gold_field("language") is False

        # System metadata fields (also excluded from Gold)
        assert config.is_gold_field("content_hash") is False
        assert config.is_gold_field("chembl.publication.content_hash") is False

    def test_get_gold_columns(self) -> None:
        """get_gold_columns() filters to Gold layer fields."""
        config = FieldGroupConfig()
        columns = [
            "title",
            "content_hash",
            "doi",
            "language",
            "authors",
            "grants",
        ]
        gold_columns = config.get_gold_columns(columns)

        assert "title" in gold_columns
        assert "doi" in gold_columns
        assert "authors" in gold_columns
        assert "grants" in gold_columns
        assert "content_hash" not in gold_columns
        assert "language" not in gold_columns
        assert len(gold_columns) == 4

    def test_get_trash_columns(self) -> None:
        """get_trash_columns() returns excluded columns."""
        config = FieldGroupConfig()
        columns = [
            "title",
            "content_hash",
            "doi",
            "language",
        ]
        trash_columns = config.get_trash_columns(columns)

        assert "content_hash" in trash_columns
        assert "language" in trash_columns
        assert "title" not in trash_columns
        assert "doi" not in trash_columns
        assert len(trash_columns) == 2

    def test_get_columns_by_group(self) -> None:
        """get_columns_by_group() filters by specific group."""
        config = FieldGroupConfig()
        columns = [
            "title",
            "abstract",
            "doi",
            "authors",
            "journal",
        ]
        biblio_columns = config.get_columns_by_group(
            columns, PublicationFieldGroup.BIBLIOGRAPHY
        )

        assert "title" in biblio_columns
        assert "abstract" in biblio_columns
        assert "journal" in biblio_columns
        assert "doi" not in biblio_columns  # ID_AND_STATUS
        assert "authors" not in biblio_columns  # AUTHOR_AND_AFFILIATIONS

    def test_group_columns(self) -> None:
        """group_columns() groups columns by semantic group."""
        config = FieldGroupConfig()
        columns = [
            "title",
            "doi",
            "authors",
            "content_hash",
            "publication_year",
        ]
        grouped = config.group_columns(columns)

        assert "title" in grouped[PublicationFieldGroup.BIBLIOGRAPHY]
        assert "doi" in grouped[PublicationFieldGroup.ID_AND_STATUS]
        assert "authors" in grouped[PublicationFieldGroup.AUTHOR_AND_AFFILIATIONS]
        assert "content_hash" in grouped[PublicationFieldGroup.SYSTEM_METADATA]
        assert "publication_year" in grouped[PublicationFieldGroup.DATE_AND_PLACES]

        # Empty groups should exist
        assert PublicationFieldGroup.CITATIONS_AND_REFERENCE in grouped
        assert grouped[PublicationFieldGroup.CITATIONS_AND_REFERENCE] == []

    def test_get_provider_rank_qualified(self) -> None:
        """get_provider_rank() extracts provider rank from qualified names."""
        config = FieldGroupConfig()

        assert config.get_provider_rank("chembl.publication.title") == 0
        assert config.get_provider_rank("crossref.publication.title") == 1
        assert config.get_provider_rank("openalex.publication.title") == 2
        assert config.get_provider_rank("pubmed.publication.title") == 3
        assert config.get_provider_rank("semanticscholar.publication.title") == 4

    def test_get_provider_rank_unqualified(self) -> None:
        """get_provider_rank() returns -1 for unqualified columns (seed)."""
        config = FieldGroupConfig()
        assert config.get_provider_rank("title") == -1
        assert config.get_provider_rank("doi") == -1

    def test_get_provider_rank_unknown_provider(self) -> None:
        """get_provider_rank() returns 999 for unknown providers."""
        config = FieldGroupConfig()
        assert config.get_provider_rank("unknown.publication.title") == 999

    def test_get_provider_rank_custom_priority(self) -> None:
        """get_provider_rank() respects custom provider_priority."""
        config = FieldGroupConfig(provider_priority=("crossref", "chembl", "pubmed"))
        assert config.get_provider_rank("crossref.publication.title") == 0
        assert config.get_provider_rank("chembl.publication.title") == 1
        assert config.get_provider_rank("pubmed.publication.title") == 2

    def test_sort_columns(self) -> None:
        """sort_columns() sorts by group, provider, and field name."""
        config = FieldGroupConfig()
        columns = [
            "pubmed.publication.title",
            "chembl.publication.doi",
            "crossref.publication.title",
            "chembl.publication.title",
            "content_hash",  # trash
            "authors",  # unqualified
        ]
        sorted_cols = config.sort_columns(columns)

        # ID_AND_STATUS (doi) comes before BIBLIOGRAPHY (title)
        doi_idx = sorted_cols.index("chembl.publication.doi")
        title_idx = sorted_cols.index("chembl.publication.title")
        assert doi_idx < title_idx

        # Within same group, chembl comes before crossref
        chembl_title_idx = sorted_cols.index("chembl.publication.title")
        crossref_title_idx = sorted_cols.index("crossref.publication.title")
        assert chembl_title_idx < crossref_title_idx

        # System metadata and trash come after business groups
        hash_idx = sorted_cols.index("content_hash")
        assert hash_idx > crossref_title_idx

    def test_sort_columns_unqualified_first(self) -> None:
        """sort_columns() puts unqualified (seed) columns before qualified."""
        config = FieldGroupConfig()
        columns = [
            "chembl.publication.title",
            "title",  # unqualified
        ]
        sorted_cols = config.sort_columns(columns)

        # Unqualified should come first (provider_rank = -1)
        assert sorted_cols[0] == "title"
        assert sorted_cols[1] == "chembl.publication.title"

    def test_frozen(self) -> None:
        """FieldGroupConfig is immutable."""
        config = FieldGroupConfig()
        with pytest.raises(Exception):  # FrozenInstanceError
            config.provider_priority = ("new", "order")  # type: ignore[misc]


class TestDefaultFieldGroupConfig:
    """Tests for DEFAULT_FIELD_GROUP_CONFIG."""

    def test_default_exists(self) -> None:
        """Default config instance exists."""
        assert DEFAULT_FIELD_GROUP_CONFIG is not None
        assert isinstance(DEFAULT_FIELD_GROUP_CONFIG, FieldGroupConfig)

    def test_default_provider_priority(self) -> None:
        """Default config has correct provider priority."""
        expected = ("chembl", "crossref", "openalex", "pubmed", "semanticscholar")
        assert DEFAULT_FIELD_GROUP_CONFIG.provider_priority == expected

    def test_default_field_groups(self) -> None:
        """Default config uses FIELD_TO_GROUP_MAPPING."""
        assert DEFAULT_FIELD_GROUP_CONFIG.field_groups == FIELD_TO_GROUP_MAPPING

    def test_default_field_group_config_uses_trash_group(
        self,
    ) -> None:
        """Default config uses TRASH as default group."""
        assert DEFAULT_FIELD_GROUP_CONFIG.default_group == PublicationFieldGroup.TRASH


class TestFieldMappingCompleteness:
    """Tests for completeness of field mapping based on requirements."""

    def test_chembl_fields_mapped(self) -> None:
        """ChEMBL publication fields are mapped."""
        chembl_fields = {
            "chembl_release",
            "publication_type",
            "publication_id",
            "doi",
            "entity_id",
            "abstract",
            "page_first",
            "issue",
            "journal",
            "journal_full_title",
            "page_last",
            "title",
            "volume",
            "authors",
            "creation_date",
            "publication_year",
            "content_hash",
            "src_id",
            "pmid",
        }
        for field in chembl_fields:
            assert field in FIELD_TO_GROUP_MAPPING, f"ChEMBL field {field} not mapped"

    def test_crossref_fields_mapped(self) -> None:
        """CrossRef publication fields are mapped."""
        crossref_fields = {
            "alternative_id",
            "doi",
            "entity_id",
            "page_first",
            "issn",
            "issn_electronic",
            "issn_print",
            "issue",
            "journal",
            "page_last",
            "publisher",
            "journal_name_short",
            "title",
            "volume",
            "authors",
            "citations_received",
            "citations_made",
            "publication_date",
            "published",
            "published_online",
            "published_print",
            "publication_year",
            "publication_type",
            "content_hash",
            "language",
            "license_url",
            "subject_keywords",
            "content_domain_crossmark_restriction",
            "content_domain_domains",
        }
        for field in crossref_fields:
            assert field in FIELD_TO_GROUP_MAPPING, f"CrossRef field {field} not mapped"

    def test_openalex_fields_mapped(self) -> None:
        """OpenAlex publication fields are mapped."""
        openalex_fields = {
            "doi",
            "entity_id",
            "is_oa",
            "is_retracted",
            "mag_id",
            "oa_status",
            "openalex_id",
            "pmid",
            "abstract",
            "page_first",
            "issn",
            "issue",
            "journal",
            "page_last",
            "publisher",
            "title",
            "volume",
            "affiliation_list",
            "author_openalex_ids",
            "authors",
            "institution_ids",
            "subject_keywords",
            "mesh",
            "primary_topic",
            "subject_topics",
            "citations_received",
            "citations_made",
            "institution_country_codes",
            "publication_date",
            "publication_year",
            "publication_type",
            "content_hash",
            "fwci",
            "grants",
            "language",
            "ror_ids",
        }
        for field in openalex_fields:
            assert field in FIELD_TO_GROUP_MAPPING, f"OpenAlex field {field} not mapped"

    def test_pubmed_fields_mapped(self) -> None:
        """PubMed publication fields are mapped."""
        pubmed_fields = {
            "doi",
            "entity_id",
            "nlm_unique_id",
            "pmc_id",
            "publication_status",
            "abstract",
            "page_first",
            "issn",
            "issue",
            "journal",
            "journal_iso_abbrev",
            "journal_issn_type",
            "journal_name_short",
            "page_last",
            "page_range",
            "title",
            "volume",
            "affiliation_list",
            "affiliation_structured",
            "author_count",
            "authors",
            "authors_with_affiliations",
            "keyword_count",
            "subject_keywords",
            "mesh_heading_count",
            "subject_mesh",
            "citation_subset",
            "chemical_count",
            "citations_made",
            "country",
            "date_completed",
            "date_revised",
            "pub_date",
            "pub_month",
            "publication_date",
            "publication_year",
            "publication_types",
            "abstract_structured",
            "content_hash",
            "grant_count",
            "language",
            "medline_pgn",
            "pub_day",
        }
        for field in pubmed_fields:
            assert field in FIELD_TO_GROUP_MAPPING, f"PubMed field {field} not mapped"

    def test_semanticscholar_fields_mapped(self) -> None:
        """SemanticScholar publication fields are mapped."""
        s2_fields = {
            "corpus_id",
            "doi",
            "entity_id",
            "abstract",
            "subject_fields",
            "is_oa",
            "oa_status",
            "open_access_url",
            "paper_id",
            "pmid",
            "page_first",
            "issue",
            "journal",
            "page_last",
            "page_range",
            "title",
            "venue",
            "volume",
            "affiliation_list",
            "author_openalex_ids",
            "author_s2_ids",
            "tldr",
            "citations_received",
            "citations_made",
            "publication_date",
            "publication_year",
            "publication_types",
            "author_h_indices",
            "citation_contexts",
            "content_hash",
            "dblp_id",
            "influential_citation_count",
        }
        for field in s2_fields:
            assert field in FIELD_TO_GROUP_MAPPING, (
                f"SemanticScholar field {field} not mapped"
            )
