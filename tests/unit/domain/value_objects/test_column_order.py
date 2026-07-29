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
"""Tests for ColumnOrder value objects."""

import pytest

from bioetl.domain.value_objects.column_order import (
    SemanticGroup,
    ColumnOrderConfig,
    DEFAULT_COLUMN_ORDER,
)


pytestmark = pytest.mark.unit


class TestSemanticGroup:
    """Tests for SemanticGroup enum."""

    def test_order_semantic_group__ordering__daf50415(self) -> None:
        """Groups are ordered correctly."""
        assert SemanticGroup.SYSTEM < SemanticGroup.IDENTIFIERS
        assert SemanticGroup.IDENTIFIERS < SemanticGroup.TITLE
        assert SemanticGroup.TITLE < SemanticGroup.ABSTRACT
        assert SemanticGroup.ABSTRACT < SemanticGroup.AUTHORS
        assert SemanticGroup.AUTHORS < SemanticGroup.OTHER


class TestColumnOrderConfig:
    """Tests for ColumnOrderConfig."""

    def test_get_group_system_column(self) -> None:
        """System columns (_*) return SYSTEM group."""
        config = ColumnOrderConfig()
        assert config.get_group("_run_id") == SemanticGroup.SYSTEM
        assert config.get_group("_ingestion_ts") == SemanticGroup.SYSTEM
        assert config.get_group("_unknown_system") == SemanticGroup.SYSTEM

    def test_get_group_identifier(self) -> None:
        """Identifier fields return IDENTIFIERS group."""
        config = ColumnOrderConfig()
        assert config.get_group("doi") == SemanticGroup.IDENTIFIERS
        assert config.get_group("pmid") == SemanticGroup.IDENTIFIERS
        assert config.get_group("publication_id") == SemanticGroup.IDENTIFIERS

    def test_column_order_config__qualified_column__09123cee(self) -> None:
        """Qualified columns extract field correctly."""
        config = ColumnOrderConfig()
        assert config.get_group("chembl.publication.title") == SemanticGroup.TITLE
        assert (
            config.get_group("crossref.publication.abstract") == SemanticGroup.ABSTRACT
        )
        assert config.get_group("pubmed.publication.authors") == SemanticGroup.AUTHORS

    def test_get_group_unknown_field(self) -> None:
        """Unknown fields return OTHER group."""
        config = ColumnOrderConfig()
        assert config.get_group("random_field") == SemanticGroup.OTHER
        assert (
            config.get_group("chembl.publication.custom_field") == SemanticGroup.OTHER
        )

    def test_column_order_config__case_insensitive__460a2a74(self) -> None:
        """Field matching is case-insensitive."""
        config = ColumnOrderConfig()
        assert config.get_group("TITLE") == SemanticGroup.TITLE
        assert config.get_group("Title") == SemanticGroup.TITLE
        assert config.get_group("chembl.publication.ABSTRACT") == SemanticGroup.ABSTRACT

    def test_get_provider_rank_qualified(self) -> None:
        """Provider rank from qualified column."""
        config = ColumnOrderConfig()
        assert config.get_provider_rank("chembl.publication.title") == 0
        assert config.get_provider_rank("crossref.publication.title") == 1
        assert config.get_provider_rank("pubmed.publication.title") == 2

    def test_get_provider_rank_unqualified(self) -> None:
        """Unqualified columns get highest priority."""
        config = ColumnOrderConfig()
        assert config.get_provider_rank("title") == -1
        assert config.get_provider_rank("doi") == -1

    def test_get_provider_rank_unknown_provider(self) -> None:
        """Unknown providers get lowest priority."""
        config = ColumnOrderConfig()
        assert config.get_provider_rank("unknown.publication.title") == 999

    def test_custom_provider_priority(self) -> None:
        """Custom provider priority is respected."""
        config = ColumnOrderConfig(provider_priority=("crossref", "chembl", "pubmed"))
        assert config.get_provider_rank("crossref.publication.title") == 0
        assert config.get_provider_rank("chembl.publication.title") == 1


class TestDefaultColumnOrder:
    """Tests for default configuration."""

    def test_default_has_all_groups(self) -> None:
        """Default config covers all major field types."""
        config = DEFAULT_COLUMN_ORDER

        # Sample fields from each group
        assert config.get_group("entity_id") == SemanticGroup.SYSTEM
        assert config.get_group("doi") == SemanticGroup.IDENTIFIERS
        assert config.get_group("title") == SemanticGroup.TITLE
        assert config.get_group("abstract") == SemanticGroup.ABSTRACT
        assert config.get_group("authors") == SemanticGroup.AUTHORS
        assert config.get_group("journal") == SemanticGroup.JOURNAL
        assert config.get_group("publication_date") == SemanticGroup.DATES
        assert config.get_group("citation_count") == SemanticGroup.METRICS
        assert config.get_group("mesh_terms") == SemanticGroup.CLASSIFICATION
        assert config.get_group("pdf_url") == SemanticGroup.URLS
