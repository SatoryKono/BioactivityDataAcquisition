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
    get_publication_entity_type_validation_error,
    get_publication_mapping,
    is_legacy_publication_alias,
    is_publication_entity,
)

pytestmark = pytest.mark.unit


class TestPublicationMapping:
    """Tests for PublicationMapping dataclass."""

    def test_publication_mapping_is_frozen(self) -> None:
        """PublicationMapping should be immutable."""
        mapping = PublicationMapping(
            canonical_name="publication",
            api_resource="document",
            plural_key="documents",
            primary_key_field="publication_id",
        )

        with pytest.raises(AttributeError):
            mapping.canonical_name = "other"  # type: ignore[misc]

    def test_publication_mapping_default_is_legacy_alias(self) -> None:
        """Default is_legacy_alias should be False."""
        mapping = PublicationMapping(
            canonical_name="publication",
            api_resource="document",
            plural_key="documents",
            primary_key_field="publication_id",
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

    def test_legacy_aliases_are_empty_after_sunset(self) -> None:
        """Legacy aliases should be removed after sunset date."""
        assert len(LEGACY_PUBLICATION_ALIASES) == 0

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
        assert mapping.primary_key_field == "publication_id"
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
        assert mapping.primary_key_field == "publication_id"
        assert mapping.is_legacy_alias is False

    def test_get_legacy_document_returns_none_after_sunset(self) -> None:
        """Should return None for legacy 'document' alias after sunset."""
        mapping = get_publication_mapping("document")
        assert mapping is None

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
        ],
    )
    def test_is_publication_entity_true(self, entity_type: str) -> None:
        """Should return True for all publication-related entities."""
        assert is_publication_entity(entity_type) is True

    @pytest.mark.parametrize(
        "entity_type",
        [
            "document",
            "document_similarity",
            "document_term",
        ],
    )
    def test_is_publication_entity_false_for_legacy_after_sunset(
        self, entity_type: str
    ) -> None:
        """Should return False for legacy entities after sunset."""
        assert is_publication_entity(entity_type) is False

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
    def test_is_legacy_alias_false_after_sunset(self, entity_type: str) -> None:
        """Should return False for legacy aliases after sunset."""
        assert is_legacy_publication_alias(entity_type) is False

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


class TestGetPublicationEntityTypeValidationError:
    """Tests for message-returning publication entity-type validation."""

    def test_validate_canonical_publication_chembl(self) -> None:
        """Should pass validation for canonical 'publication' with chembl provider."""
        error = get_publication_entity_type_validation_error("publication", "chembl")

        assert error is None

    def test_validate_canonical_publication_similarity_chembl(self) -> None:
        """Should pass validation for canonical 'publication_similarity' with chembl."""
        error = get_publication_entity_type_validation_error(
            "publication_similarity", "chembl"
        )

        assert error is None

    def test_validate_legacy_document_chembl_passes_after_sunset(self) -> None:
        """Should pass validation for legacy 'document' (as unknown) after sunset."""
        error = get_publication_entity_type_validation_error("document", "chembl")
        assert error is None

    def test_validate_legacy_document_similarity_chembl_passes_after_sunset(
        self,
    ) -> None:
        """Should pass validation for legacy 'document_similarity' after sunset."""
        error = get_publication_entity_type_validation_error(
            "document_similarity", "chembl"
        )
        assert error is None

    def test_validate_legacy_document_term_chembl_passes_after_sunset(self) -> None:
        """Should pass validation for legacy 'document_term' after sunset."""
        error = get_publication_entity_type_validation_error("document_term", "chembl")
        assert error is None

    def test_validate_non_chembl_provider_skips_validation(self) -> None:
        """Should skip validation for non-chembl providers."""
        # document is allowed for other providers (may have different meaning)
        error = get_publication_entity_type_validation_error("document", "pubmed")

        assert error is None

    def test_validate_non_publication_entity(self) -> None:
        """Should pass validation for non-publication entities."""
        error = get_publication_entity_type_validation_error("activity", "chembl")

        assert error is None


class TestAllPublicationEntityTypes:
    """Tests for ALL_PUBLICATION_ENTITY_TYPES set."""

    def test_includes_only_canonical_after_sunset(self) -> None:
        """Should include only canonical names after sunset."""
        assert "publication" in ALL_PUBLICATION_ENTITY_TYPES
        assert "document" not in ALL_PUBLICATION_ENTITY_TYPES
        assert "publication_similarity" in ALL_PUBLICATION_ENTITY_TYPES
        assert "document_similarity" not in ALL_PUBLICATION_ENTITY_TYPES

    def test_is_union_of_canonical_and_legacy(self) -> None:
        """Should be the union of canonical and legacy sets."""
        expected = PUBLICATION_ENTITY_TYPES | LEGACY_PUBLICATION_ALIASES
        assert ALL_PUBLICATION_ENTITY_TYPES == expected
