from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.column_service import (
    ColumnOrderService,
    collect_explicit_group_columns,
    extract_field_from_qualified_name,
    sort_columns_by_provider,
)
from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.value_objects.column_order import (
    ColumnOrderConfig,
    SemanticGroup,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def orderer(mock_logger: MagicMock) -> ColumnOrderService:
    """Create ColumnOrderService instance."""
    return ColumnOrderService(mock_logger)


class TestColumnOrderService:
    """Tests for ColumnOrderService."""

    def test_system_columns_first(self, orderer: ColumnOrderService) -> None:
        """System columns appear first."""
        df = pl.DataFrame(
            {
                "title": ["T1"],
                "_run_id": ["r1"],
                "doi": ["10.1/a"],
                "entity_id": ["e1"],
            }
        )
        result = orderer.order_columns(df)

        # System columns should be first
        assert result.columns[0] in ("entity_id", "_run_id")
        assert result.columns[1] in ("entity_id", "_run_id")

    def test_identifiers_before_content(self, orderer: ColumnOrderService) -> None:
        """Identifiers appear before content fields."""
        df = pl.DataFrame(
            {
                "abstract": ["A1"],
                "doi": ["10.1/a"],
                "title": ["T1"],
                "pmid": ["123"],
            }
        )
        result = orderer.order_columns(df)

        doi_idx = result.columns.index("doi")
        pmid_idx = result.columns.index("pmid")
        title_idx = result.columns.index("title")
        abstract_idx = result.columns.index("abstract")

        assert doi_idx < title_idx
        assert pmid_idx < title_idx
        assert title_idx < abstract_idx

    def test_title_before_abstract(self, orderer: ColumnOrderService) -> None:
        """Title fields appear before abstract fields."""
        df = pl.DataFrame(
            {
                "chembl.publication.abstract": ["A1"],
                "chembl.publication.title": ["T1"],
                "crossref.publication.title": ["T2"],
            }
        )
        result = orderer.order_columns(df)

        # All titles before abstracts
        title_indices = [
            i for i, c in enumerate(result.columns) if "title" in c.lower()
        ]
        abstract_indices = [
            i for i, c in enumerate(result.columns) if "abstract" in c.lower()
        ]

        assert max(title_indices) < min(abstract_indices)

    def test_provider_priority_within_group(self, orderer: ColumnOrderService) -> None:
        """Within same group, chembl comes before crossref."""
        df = pl.DataFrame(
            {
                "crossref.publication.title": ["T1"],
                "chembl.publication.title": ["T2"],
                "pubmed.publication.title": ["T3"],
            }
        )
        result = orderer.order_columns(df)

        chembl_idx = result.columns.index("chembl.publication.title")
        crossref_idx = result.columns.index("crossref.publication.title")
        pubmed_idx = result.columns.index("pubmed.publication.title")

        assert chembl_idx < crossref_idx < pubmed_idx

    def test_unqualified_columns_have_priority(
        self, orderer: ColumnOrderService
    ) -> None:
        """Unqualified columns appear before qualified in same group."""
        df = pl.DataFrame(
            {
                "crossref.publication.title": ["T1"],
                "title": ["T2"],
            }
        )
        result = orderer.order_columns(df)

        title_idx = result.columns.index("title")
        crossref_idx = result.columns.index("crossref.publication.title")

        assert title_idx < crossref_idx

    def test_column_order_service__empty_dataframe__d7317264(
        self, orderer: ColumnOrderService
    ) -> None:
        """Empty DataFrame returns empty DataFrame."""
        df = pl.DataFrame()
        result = orderer.order_columns(df)
        assert len(result.columns) == 0

    def test_get_ordered_columns(self, orderer: ColumnOrderService) -> None:
        """Get ordered column names without DataFrame."""
        columns = ["abstract", "title", "_run_id", "doi"]
        ordered = orderer.get_ordered_columns(columns)

        assert ordered.index("_run_id") < ordered.index("doi")
        assert ordered.index("doi") < ordered.index("title")
        assert ordered.index("title") < ordered.index("abstract")

    def test_group_columns(self, orderer: ColumnOrderService) -> None:
        """Group columns by semantic type."""
        columns = [
            "_run_id",
            "doi",
            "chembl.publication.title",
            "crossref.publication.abstract",
        ]
        groups = orderer.group_columns(columns)

        assert "_run_id" in groups[SemanticGroup.SYSTEM]
        assert "doi" in groups[SemanticGroup.IDENTIFIERS]
        assert "chembl.publication.title" in groups[SemanticGroup.TITLE]
        assert "crossref.publication.abstract" in groups[SemanticGroup.ABSTRACT]

    def test_data_preserved_after_reorder(self, orderer: ColumnOrderService) -> None:
        """Data values are preserved after reordering."""
        df = pl.DataFrame(
            {
                "title": ["Title 1"],
                "_run_id": ["r1"],
                "doi": ["10.1/a"],
            }
        )
        result = orderer.order_columns(df)

        assert result["title"][0] == "Title 1"
        assert result["_run_id"][0] == "r1"
        assert result["doi"][0] == "10.1/a"

    def test_custom_config(self, mock_logger: MagicMock) -> None:
        """Custom configuration is respected."""
        config = ColumnOrderConfig(
            provider_priority=("crossref", "chembl")  # Reversed
        )
        orderer = ColumnOrderService(mock_logger, config)

        df = pl.DataFrame(
            {
                "chembl.publication.title": ["T1"],
                "crossref.publication.title": ["T2"],
            }
        )
        result = orderer.order_columns(df)

        # Crossref should come first with custom config
        crossref_idx = result.columns.index("crossref.publication.title")
        chembl_idx = result.columns.index("chembl.publication.title")

        assert crossref_idx < chembl_idx

    def test_full_publication_order(self, orderer: ColumnOrderService) -> None:
        """Full publication DataFrame is ordered correctly."""
        df = pl.DataFrame(
            {
                "citation_count": [100],
                "authors": [["Author 1"]],
                "journal": ["Nature"],
                "publication_date": ["2025-01-01"],
                "abstract": ["Abstract text"],
                "title": ["Title text"],
                "mesh_terms": [["term1"]],
                "doi": ["10.1/a"],
                "pmid": ["123"],
                "_run_id": ["r1"],
                "entity_id": ["e1"],
                "content_hash": ["hash1"],
                "pdf_url": ["https://example.com/pdf"],
            }
        )
        result = orderer.order_columns(df)

        # Verify semantic order
        # Within each group, columns are sorted alphabetically by field name
        # Note: underscore has lower ASCII value than letters, so _run_id comes first
        expected_order = [
            "_run_id",  # SYSTEM (underscore sorts before letters)
            "content_hash",  # SYSTEM
            "entity_id",  # SYSTEM
            "doi",  # IDENTIFIERS
            "pmid",  # IDENTIFIERS
            "title",  # TITLE
            "abstract",  # ABSTRACT
            "authors",  # AUTHORS
            "journal",  # JOURNAL
            "publication_date",  # DATES
            "citation_count",  # METRICS
            "mesh_terms",  # CLASSIFICATION
            "pdf_url",  # URLS
        ]

        assert result.columns == expected_order

    def test_collect_explicit_group_columns_preserves_field_order(
        self,
    ) -> None:
        """Explicit group collection keeps declared field order and de-duplicates."""
        group = ColumnGroupConfig(
            name="publication_fields",
            fields=("title", "journal"),
            provider_order=("chembl", "crossref", "pubmed"),
        )
        available = {
            "chembl.publication.title",
            "crossref.publication.title",
            "title",
            "journal",
            "crossref.publication.journal",
        }

        ordered, used = collect_explicit_group_columns(
            available=available,
            group=group,
            sort_fn=sort_columns_by_provider,
            extract_field_fn=extract_field_from_qualified_name,
            resolve_aliases_fn=lambda field_name: {field_name},
        )

        assert ordered == [
            "title",
            "chembl.publication.title",
            "crossref.publication.title",
            "journal",
            "crossref.publication.journal",
        ]
        assert used == {
            "title",
            "chembl.publication.title",
            "crossref.publication.title",
            "journal",
            "crossref.publication.journal",
        }


class TestColumnOrderServiceYAMLGroups:
    """Tests for YAML-based column group ordering."""

    def test_yaml_groups_order_by_explicit_fields(self, mock_logger: MagicMock) -> None:
        """Explicit field names in YAML are ordered correctly."""
        groups = [
            ColumnGroupConfig(name="title", fields=("title",)),
            ColumnGroupConfig(name="abstract", fields=("abstract",)),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "abstract": ["A1"],
                "title": ["T1"],
                "crossref.publication.title": ["T2"],
            }
        )
        result = orderer.order_columns(df)

        # Title group first (seed, then enrichers)
        assert result.columns[0] == "title"
        assert result.columns[1] == "crossref.publication.title"
        assert result.columns[2] == "abstract"

    def test_yaml_groups_pattern_matching(self, mock_logger: MagicMock) -> None:
        """Regex pattern matching works for YAML groups."""
        groups = [
            ColumnGroupConfig(name="system", pattern=r"^_"),
            ColumnGroupConfig(name="content", fields=("title",)),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "title": ["T1"],
                "_run_id": ["r1"],
                "_ingestion_ts": ["ts1"],
            }
        )
        result = orderer.order_columns(df)

        # System fields first (pattern match)
        assert result.columns[0].startswith("_")
        assert result.columns[1].startswith("_")
        assert result.columns[2] == "title"

    def test_yaml_groups_provider_order(self, mock_logger: MagicMock) -> None:
        """Provider order within YAML group is respected."""
        groups = [
            ColumnGroupConfig(
                name="citations",
                fields=("citation_count",),
                provider_order=("crossref", "openalex", "semanticscholar"),
            ),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "semanticscholar.publication.citation_count": [10],
                "crossref.publication.citation_count": [15],
                "openalex.publication.citation_count": [12],
            }
        )
        result = orderer.order_columns(df)

        assert result.columns == [
            "crossref.publication.citation_count",
            "openalex.publication.citation_count",
            "semanticscholar.publication.citation_count",
        ]

    def test_yaml_groups_seed_first_in_group(self, mock_logger: MagicMock) -> None:
        """Seed columns (no prefix) come before enricher columns in YAML groups."""
        groups = [
            ColumnGroupConfig(name="title", fields=("title",)),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "crossref.publication.title": ["T1"],
                "title": ["T2"],
            }
        )
        result = orderer.order_columns(df)

        assert result.columns[0] == "title"  # Seed first
        assert result.columns[1] == "crossref.publication.title"

    def test_yaml_groups_ungrouped_at_end(self, mock_logger: MagicMock) -> None:
        """Columns not matching any YAML group go to the end."""
        groups = [
            ColumnGroupConfig(name="title", fields=("title",)),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "title": ["T1"],
                "unknown_field": ["X"],
                "another_unknown": ["Y"],
            }
        )
        result = orderer.order_columns(df)

        assert result.columns[0] == "title"
        # Remaining sorted alphabetically
        assert result.columns[1:] == ["another_unknown", "unknown_field"]

    def test_yaml_groups_multiple_groups_order(self, mock_logger: MagicMock) -> None:
        """Multiple YAML groups maintain their defined order."""
        groups = [
            ColumnGroupConfig(name="system", fields=("entity_id", "_run_id")),
            ColumnGroupConfig(name="identifiers", fields=("doi", "pmid")),
            ColumnGroupConfig(name="title", fields=("title",)),
            ColumnGroupConfig(name="abstract", fields=("abstract",)),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "abstract": ["A1"],
                "title": ["T1"],
                "pmid": ["123"],
                "doi": ["10.1/a"],
                "_run_id": ["r1"],
                "entity_id": ["e1"],
            }
        )
        result = orderer.order_columns(df)

        # Verify order: system -> identifiers -> title -> abstract
        entity_idx = result.columns.index("entity_id")
        run_idx = result.columns.index("_run_id")
        doi_idx = result.columns.index("doi")
        pmid_idx = result.columns.index("pmid")
        title_idx = result.columns.index("title")
        abstract_idx = result.columns.index("abstract")

        # System fields first
        assert entity_idx < doi_idx
        assert run_idx < doi_idx
        # Identifiers before title
        assert doi_idx < title_idx
        assert pmid_idx < title_idx
        # Title before abstract
        assert title_idx < abstract_idx

    def test_yaml_groups_data_preserved(self, mock_logger: MagicMock) -> None:
        """Data values are preserved after YAML group reordering."""
        groups = [
            ColumnGroupConfig(name="id", fields=("doi",)),
            ColumnGroupConfig(name="title", fields=("title",)),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "title": ["Title 1"],
                "doi": ["10.1/a"],
            }
        )
        result = orderer.order_columns(df)

        assert result["title"][0] == "Title 1"
        assert result["doi"][0] == "10.1/a"

    def test_yaml_groups_empty_dataframe(self, mock_logger: MagicMock) -> None:
        """Empty DataFrame with YAML groups returns empty DataFrame."""
        groups = [
            ColumnGroupConfig(name="title", fields=("title",)),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame()
        result = orderer.order_columns(df)
        assert len(result.columns) == 0

    def test_yaml_groups_fallback_to_default(self, mock_logger: MagicMock) -> None:
        """Without YAML groups, falls back to default ColumnOrderConfig."""
        orderer = ColumnOrderService(mock_logger)  # No column_groups

        df = pl.DataFrame(
            {
                "title": ["T1"],
                "_run_id": ["r1"],
            }
        )
        result = orderer.order_columns(df)

        # Default behavior: system before title
        assert result.columns.index("_run_id") < result.columns.index("title")

    def test_yaml_groups_preserve_field_order(self, mock_logger: MagicMock) -> None:
        """Fields within a YAML group are emitted in field-list order, not sorted."""
        groups = [
            ColumnGroupConfig(
                name="bibliography",
                fields=("abstract", "doi", "title", "volume"),
                provider_order=("chembl", "crossref"),
            ),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "chembl.publication.volume": ["1"],
                "crossref.publication.title": ["T1"],
                "chembl.publication.title": ["T2"],
                "chembl.publication.abstract": ["A1"],
                "chembl.publication.doi": ["10.1/a"],
            }
        )
        result = orderer.order_columns(df)

        # Fields should follow the field-list order: abstract, doi, title, volume
        # Within each field, providers sorted by provider_order
        assert result.columns == [
            "chembl.publication.abstract",  # abstract first
            "chembl.publication.doi",  # doi second
            "chembl.publication.title",  # title third (chembl before crossref)
            "crossref.publication.title",
            "chembl.publication.volume",  # volume last
        ]

    def test_yaml_groups_canonical_category_order(self, mock_logger: MagicMock) -> None:
        """Canonical-style groups (id, bibliography) maintain field order."""
        groups = [
            ColumnGroupConfig(
                name="id",
                fields=("entity_id", "pmid"),
                provider_order=("chembl", "openalex"),
            ),
            ColumnGroupConfig(
                name="bibliography",
                fields=("abstract", "title"),
                provider_order=("chembl", "openalex"),
            ),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "openalex.publication.abstract": ["A1"],
                "chembl.publication.title": ["T1"],
                "chembl.publication.entity_id": ["e1"],
                "openalex.publication.pmid": ["123"],
                "chembl.publication.abstract": ["A2"],
            }
        )
        result = orderer.order_columns(df)

        # id group: entity_id before pmid
        # bibliography group: abstract before title
        expected = [
            "chembl.publication.entity_id",
            "openalex.publication.pmid",
            "chembl.publication.abstract",
            "openalex.publication.abstract",
            "chembl.publication.title",
        ]
        assert result.columns == expected

    def test_yaml_groups_dq_fields_always_last(self, mock_logger: MagicMock) -> None:
        """DQ suffix fields (_dq_error, _dq_warn) are always the last two columns."""
        groups = [
            ColumnGroupConfig(
                name="system",
                fields=("entity_id", "_run_id"),
                pattern=r"^_",
            ),
            ColumnGroupConfig(name="content", fields=("title",)),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "title": ["T1"],
                "_run_id": ["r1"],
                "entity_id": ["e1"],
                "_dq_error": [False],
                "_dq_warn": [False],
                "unknown_field": ["X"],
            }
        )
        result = orderer.order_columns(df)

        # _dq_error and _dq_warn MUST be the last two columns
        assert result.columns[-2] == "_dq_error"
        assert result.columns[-1] == "_dq_warn"
        # Other fields should precede them
        assert "title" in result.columns[:-2]
        assert "entity_id" in result.columns[:-2]
        assert "_run_id" in result.columns[:-2]
        assert "unknown_field" in result.columns[:-2]

    def test_yaml_groups_dq_fields_last_even_without_remaining(
        self, mock_logger: MagicMock
    ) -> None:
        """DQ fields are last even when all other columns are in explicit groups."""
        groups = [
            ColumnGroupConfig(name="system", fields=("entity_id",)),
            ColumnGroupConfig(name="content", fields=("title",)),
        ]
        orderer = ColumnOrderService(mock_logger, column_groups=groups)

        df = pl.DataFrame(
            {
                "entity_id": ["e1"],
                "title": ["T1"],
                "_dq_error": [False],
                "_dq_warn": [False],
            }
        )
        result = orderer.order_columns(df)

        assert result.columns == ["entity_id", "title", "_dq_error", "_dq_warn"]
