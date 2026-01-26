"""Unit tests for publication mapping registry.

Tests the centralized publication entity mapping registry (ADR-024).
"""

from __future__ import annotations

import pytest

from bioetl.domain.registry.publication import (
    ALL_PUBLICATION_ENTITY_TYPES,
    LEGACY_PUBLICATION_ALIASES,
    PUBLICATION_ENTITY_TYPES,
    PublicationMapping,
    get_publication_mapping,
    is_legacy_publication_alias,
    is_publication_entity,
    validate_publication_entity_type,
)


class TestPublicationMapping:
    """Tests for PublicationMapping dataclass."""

    def test_publication_mapping_is_frozen(self) -> None:
        """PublicationMapping should be immutable."""
        mapping = PublicationMapping(
            canonical_name="publication",
            api_resource="document",
            plural_key="documents",
            primary_key_field="document_chembl_id",
        )

        with pytest.raises(AttributeError):
            mapping.canonical_name = "other"  # type: ignore[misc]

    def test_publication_mapping_default_is_legacy_alias(self) -> None:
        """Default is_legacy_alias should be False."""
        mapping = PublicationMapping(
            canonical_name="publication",
            api_resource="document",
            plural_key="documents",
            primary_key_field="document_chembl_id",
        )

        assert mapping.is_legacy_alias is False


class TestCanonicalEntityTypes:
    """Tests for canonical publication entity types."""

    def test_canonical_types_are_frozen(self) -> None:
        """PUBLICATION_ENTITY_TYPES should be immutable."""
        assert isinstance(PUBLICATION_ENTITY_TYPES, frozenset)

    def test_canonical_types_include_publication(self) -> None:
        """Should include 'publication' canonical type."""
        assert "publication" in PUBLICATION_ENTITY_TYPES

    def test_canonical_types_include_publication_similarity(self) -> None:
        """Should include 'publication_similarity' canonical type."""
        assert "publication_similarity" in PUBLICATION_ENTITY_TYPES

    def test_canonical_types_include_publication_term(self) -> None:
        """Should include 'publication_term' canonical type."""
        assert "publication_term" in PUBLICATION_ENTITY_TYPES

    def test_canonical_types_exclude_legacy_aliases(self) -> None:
        """Canonical types should NOT include legacy aliases."""
        assert "document" not in PUBLICATION_ENTITY_TYPES
        assert "document_similarity" not in PUBLICATION_ENTITY_TYPES
        assert "document_term" not in PUBLICATION_ENTITY_TYPES


class TestLegacyAliases:
    """Tests for legacy publication aliases."""

    def test_legacy_aliases_are_frozen(self) -> None:
        """LEGACY_PUBLICATION_ALIASES should be immutable."""
        assert isinstance(LEGACY_PUBLICATION_ALIASES, frozenset)

    def test_legacy_aliases_include_document(self) -> None:
        """Should include 'document' legacy alias."""
        assert "document" in LEGACY_PUBLICATION_ALIASES

    def test_legacy_aliases_include_document_similarity(self) -> None:
        """Should include 'document_similarity' legacy alias."""
        assert "document_similarity" in LEGACY_PUBLICATION_ALIASES

    def test_legacy_aliases_include_document_term(self) -> None:
        """Should include 'document_term' legacy alias."""
        assert "document_term" in LEGACY_PUBLICATION_ALIASES

    def test_legacy_aliases_exclude_canonical(self) -> None:
        """Legacy aliases should NOT include canonical names."""
        assert "publication" not in LEGACY_PUBLICATION_ALIASES
        assert "publication_similarity" not in LEGACY_PUBLICATION_ALIASES
        assert "publication_term" not in LEGACY_PUBLICATION_ALIASES


class TestGetPublicationMapping:
    """Tests for get_publication_mapping function."""

    def test_get_canonical_publication(self) -> None:
        """Should return mapping for canonical 'publication'."""
        mapping = get_publication_mapping("publication")

        assert mapping is not None
        assert mapping.canonical_name == "publication"
        assert mapping.api_resource == "document"
        assert mapping.plural_key == "documents"
        assert mapping.primary_key_field == "document_chembl_id"
        assert mapping.is_legacy_alias is False

    def test_get_canonical_publication_similarity(self) -> None:
        """Should return mapping for canonical 'publication_similarity'."""
        mapping = get_publication_mapping("publication_similarity")

        assert mapping is not None
        assert mapping.canonical_name == "publication_similarity"
        assert mapping.api_resource == "document_similarity"
        assert mapping.plural_key == "document_similarities"
        assert mapping.primary_key_field == "sim_id"
        assert mapping.is_legacy_alias is False

    def test_get_canonical_publication_term(self) -> None:
        """Should return mapping for canonical 'publication_term'."""
        mapping = get_publication_mapping("publication_term")

        assert mapping is not None
        assert mapping.canonical_name == "publication_term"
        assert mapping.api_resource == "document"
        assert mapping.primary_key_field == "document_chembl_id"
        assert mapping.is_legacy_alias is False

    def test_get_legacy_document(self) -> None:
        """Should return mapping for legacy 'document' alias."""
        mapping = get_publication_mapping("document")

        assert mapping is not None
        assert mapping.canonical_name == "document"
        assert mapping.api_resource == "document"
        assert mapping.is_legacy_alias is True

    def test_get_unknown_entity(self) -> None:
        """Should return None for unknown entity type."""
        mapping = get_publication_mapping("activity")

        assert mapping is None

    def test_get_completely_unknown_entity(self) -> None:
        """Should return None for completely unknown entity type."""
        mapping = get_publication_mapping("nonexistent_entity")

        assert mapping is None


class TestIsPublicationEntity:
    """Tests for is_publication_entity function."""

    @pytest.mark.parametrize(
        "entity_type",
        [
            "publication",
            "publication_similarity",
            "publication_term",
            "document",
            "document_similarity",
            "document_term",
        ],
    )
    def test_is_publication_entity_true(self, entity_type: str) -> None:
        """Should return True for all publication-related entities."""
        assert is_publication_entity(entity_type) is True

    @pytest.mark.parametrize(
        "entity_type",
        [
            "activity",
            "assay",
            "molecule",
            "target",
            "compound",
            "unknown",
        ],
    )
    def test_is_publication_entity_false(self, entity_type: str) -> None:
        """Should return False for non-publication entities."""
        assert is_publication_entity(entity_type) is False


class TestIsLegacyPublicationAlias:
    """Tests for is_legacy_publication_alias function."""

    @pytest.mark.parametrize(
        "entity_type",
        [
            "document",
            "document_similarity",
            "document_term",
        ],
    )
    def test_is_legacy_alias_true(self, entity_type: str) -> None:
        """Should return True for legacy aliases."""
        assert is_legacy_publication_alias(entity_type) is True

    @pytest.mark.parametrize(
        "entity_type",
        [
            "publication",
            "publication_similarity",
            "publication_term",
            "activity",
            "unknown",
        ],
    )
    def test_is_legacy_alias_false(self, entity_type: str) -> None:
        """Should return False for canonical names and non-publication entities."""
        assert is_legacy_publication_alias(entity_type) is False


class TestValidatePublicationEntityType:
    """Tests for validate_publication_entity_type function."""

    def test_validate_canonical_publication_chembl(self) -> None:
        """Should pass validation for canonical 'publication' with chembl provider."""
        error = validate_publication_entity_type("publication", "chembl")

        assert error is None

    def test_validate_canonical_publication_similarity_chembl(self) -> None:
        """Should pass validation for canonical 'publication_similarity' with chembl."""
        error = validate_publication_entity_type("publication_similarity", "chembl")

        assert error is None

    def test_validate_legacy_document_chembl_fails(self) -> None:
        """Should fail validation for legacy 'document' with chembl provider."""
        error = validate_publication_entity_type("document", "chembl")

        assert error is not None
        assert "publication" in error
        assert "document" in error
        assert "ADR-024" in error

    def test_validate_legacy_document_similarity_chembl_fails(self) -> None:
        """Should fail validation for legacy 'document_similarity' with chembl."""
        error = validate_publication_entity_type("document_similarity", "chembl")

        assert error is not None
        assert "publication_similarity" in error
        assert "document_similarity" in error

    def test_validate_legacy_document_term_chembl_fails(self) -> None:
        """Should fail validation for legacy 'document_term' with chembl."""
        error = validate_publication_entity_type("document_term", "chembl")

        assert error is not None
        assert "publication_term" in error
        assert "document_term" in error

    def test_validate_non_chembl_provider_skips_validation(self) -> None:
        """Should skip validation for non-chembl providers."""
        # document is allowed for other providers (may have different meaning)
        error = validate_publication_entity_type("document", "pubmed")

        assert error is None

    def test_validate_non_publication_entity(self) -> None:
        """Should pass validation for non-publication entities."""
        error = validate_publication_entity_type("activity", "chembl")

        assert error is None


class TestAllPublicationEntityTypes:
    """Tests for ALL_PUBLICATION_ENTITY_TYPES set."""

    def test_includes_canonical_and_legacy(self) -> None:
        """Should include both canonical names and legacy aliases."""
        assert "publication" in ALL_PUBLICATION_ENTITY_TYPES
        assert "document" in ALL_PUBLICATION_ENTITY_TYPES
        assert "publication_similarity" in ALL_PUBLICATION_ENTITY_TYPES
        assert "document_similarity" in ALL_PUBLICATION_ENTITY_TYPES

    def test_is_union_of_canonical_and_legacy(self) -> None:
        """Should be the union of canonical and legacy sets."""
        expected = PUBLICATION_ENTITY_TYPES | LEGACY_PUBLICATION_ALIASES
        assert ALL_PUBLICATION_ENTITY_TYPES == expected
